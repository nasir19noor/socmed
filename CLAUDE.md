# socmed — notes for Claude

Automated Threads content for one personal account, run by an **OpenClaw**
agent (Claude as the model) that talks to the owner over **WhatsApp**. The
agent researches trends, drafts posts in the owner's voice with a rendered
image, sends them to WhatsApp for approval, and posts only what the owner
approves. Everything user-facing — content, WhatsApp messages, README,
SKILL.md, script messages and comments — is in **Bahasa Indonesia**; keep it
that way. This file is in English, for whoever (or whatever) works on the code.

Read `README.md` (installation, WhatsApp commands) and
`skills/konten-threads/SKILL.md` (what the agent is told to do) before
changing behaviour. **Keep this file, README.md and SKILL.md current in the
same change as any code edit** — a stale file is worse than none.

## Layout

```
skills/konten-threads/          the OpenClaw skill — copied to ~/.openclaw/workspace/skills/
  SKILL.md                      the agent's instructions: 4 modes, schedule, safety rules
  referensi/sumber-tren.md      where to research trends
  referensi/gaya-bahasa.md      the account's voice, hook and thread patterns
  referensi/contoh-postingan.md the owner's real posts (style reference; edited by contoh.py)
  referensi/desain-bebas.md     rules for free-form HTML/SVG visuals
  templates/visual.html         standard 1080×1350 card template
  scripts/jalankan              bash entry point: runs <script>.py with the venv's Python
  scripts/antrian.py            per-day queue of proposals and approvals (JSON)
  scripts/post_threads.py       posts the approved option to the Threads API
  scripts/render_visual.py      template card → PNG (Playwright, Chrome fallback)
  scripts/render_html.py        agent-written HTML/SVG → PNG, with safety checks
  scripts/contoh.py             add / list / remove style examples
pasang.sh                       installs/updates the skill on the host, filling in the owner's number
cron-setup.sh                   registers the 6 OpenClaw cron jobs (WIB)
AGENTS-tambahan.md              "threads" trigger rule; pasang.sh puts it in ~/.openclaw/workspace/AGENTS.md
env.example                     variables for ~/.openclaw/.env
contoh-visual/                  sample renders (reference only, not used at runtime)
```

**Deploy**: `.github/workflows/deploy.yml` on push to `main` (paths
`skills/**`, `pasang.sh`, `AGENTS-tambahan.md`) or by hand. It runs on a
**self-hosted runner on the OpenClaw host** (labels `[self-hosted,
contabo-2-openclaw]`, registered as the `openclaw` user — the same pattern
as the Contabo runners in lantip and nasir.id): syntax-check the scripts,
**empty `~/.openclaw/workspace/skills/` entirely** (so files deleted from
the repo do not linger — and any skill installed there by hand goes too),
`bash pasang.sh`, `chmod +x` the scripts, `openclaw gateway restart`. The
emptying step sets `konten-threads/referensi/contoh-postingan.md` aside in
`$RUNNER_TEMP` and puts it back first: the owner's saved style examples
exist only on the host and must survive every deploy. Cron jobs
are not touched; `cron-setup.sh` stays a one-time manual step.

Nothing here is a service or a build: `pasang.sh` copies the skill folder
onto the OpenClaw host (Linux, user `openclaw`) and the agent runs the
scripts there. It keeps the host's `referensi/contoh-postingan.md` (the
owner adds examples to it from WhatsApp, so the repo copy is only the
seed), and replaces its own marked block in `AGENTS.md`, so it is safe to
re-run after every update.

## How it works

**Four modes** (SKILL.md):
1. **Proposals** — cron at 06.30 / 12.15 / 19.15 WIB: research, 3 options per
   slot (`pagi` = 4–7-post thread, `siang`/`malam` = one post), render a
   visual each, `antrian simpan`, send each option to WhatsApp.
2. **Owner replies** — `OK n`, `revisi n: …`, `ganti topik`, `skip`,
   `status`, `contoh: …`, free requests ("buatkan konten …", "analisa …").
3. **Posting** — cron at 08.00 / 13.00 / 20.00 WIB:
   `jalankan post_threads --slot <slot>`; posts only an approved option.
4. **Manual trigger** — a message starting with `threads` from the owner: a
   one-message wizard (topic, format, image, when), 2 options in slot
   `manualN`, posted immediately or by a one-shot cron (`--at`, UTC).

**Queue** (`antrian.py`): one JSON file per WIB date in
`$KONTEN_DATA_DIR` (default `~/.openclaw/workspace/konten-threads/antrian/`).
Each slot: `status` ∈ `menunggu → disetujui → terposting` (or `dilewati`),
`disetujui` = 1-based option number, `opsi` = list of
`{topik, kategori, tag, posts[], gambar, sumber[], format?}`. A revision of
the approved option drops the approval. `simpan` validates every post
against the **500-character Threads limit** (counted as Threads counts —
see `panjang_threads`).

**Posting** (`post_threads.py`, stdlib only): the image is uploaded to
**imgbb** (Threads must fetch it from a public URL), each post becomes a
container (`IMAGE` for the first post when there is an image, `TEXT`
otherwise, `reply_to_id` chaining a thread, the topic tag on the first post
only; each post replies to the one before, 4 s apart), waits for
`FINISHED`, publishes, then records `terposting` with the first post's
permalink and every media id. Exit codes matter to the cron prompts: **0** posted, **2** not
approved / already posted / skipped, **1** error. `--dry-run` simulates,
`--cek` checks the token and prints the user id, `--refresh-token` extends
the 60-day long-lived token.

**Rendering**: `render_visual.py` fills `templates/visual.html` (palette per
`kategori`, `*accent*` in titles, `--poin` list, `--gaya kutipan`);
`render_html.py` renders an agent-written HTML file and **rejects external
resources** except Google Fonts, and warns when content overflows
1080×1350. Both try Playwright first, then a system Chrome/Chromium.

## Conventions and gotchas

- **Nothing is ever posted without the owner's explicit "OK".** The posting
  script enforces it (status must be `disetujui`); do not add a path around
  it.
- **Only the owner's number may approve, revise, skip or trigger content.**
  Other allowlisted numbers can chat with the bot but must be refused for
  content commands.
- **No phone numbers in the repo.** The owner's number is `THREADS_PEMILIK`
  in `~/.openclaw/.env`; SKILL.md and AGENTS-tambahan.md say `{{PEMILIK}}`,
  which `pasang.sh` fills in on the host, and `cron-setup.sh` reads the
  variable itself. Write `{{PEMILIK}}` (or "pemilik") in anything new — never
  a real number. The same goes for tokens: the git remote is a plain HTTPS
  URL, credentials stay in the credential manager.
- **Run scripts through `scripts/jalankan`**, never `python3 x.py`
  directly: it picks the venv (`KONTEN_VENV`, default
  `/home/openclaw/projects/threads/venv`) where Playwright lives. Only the
  renderers need packages (Playwright); everything else is the Python
  standard library — keep it that way.
- **Secrets live only in `~/.openclaw/.env`** on the host
  (`THREADS_PEMILIK`, `THREADS_USER_ID`, `THREADS_ACCESS_TOKEN`,
  `IMGBB_API_KEY`, optional `KONTEN_VENV`, `THREADS_HANDLE`). `post_threads.py` reads that file
  itself. Never commit a real token; `env.example` holds empty names only.
- **Times are WIB (Asia/Jakarta).** Recurring cron jobs use `--tz`;
  one-shot `--at` jobs take UTC (WIB − 7 h). Queue dates are WIB dates.
- **Facts need sources**: every option carries `sumber` URLs; the agent
  must not invent facts, numbers or quotes. No SARA, partisan politics,
  hoaxes, other people's personal data, or real people's photos in visuals.
- **Voice**: the agent reads `contoh-postingan.md` (the owner's own posts)
  before `gaya-bahasa.md` and imitates style, never content. First person
  "saya", no emoji or hashtags in posts.
- `contoh.py` rewrites `contoh-postingan.md` in place, splitting on `---`
  lines; keep that separator format if you edit the file by hand.

## Testing

There is no test suite. Safe checks that touch nothing live:

```bash
cd skills/konten-threads/scripts
KONTEN_DATA_DIR=/tmp/antrian ./jalankan antrian slot-baru
KONTEN_DATA_DIR=/tmp/antrian ./jalankan antrian simpan --slot siang < opsi.json
KONTEN_DATA_DIR=/tmp/antrian ./jalankan antrian setujui --slot siang --opsi 1
KONTEN_DATA_DIR=/tmp/antrian ./jalankan post_threads --slot siang --dry-run
./jalankan render_visual --kategori lokal --judul "Uji *visual*" --isi "Tes" --out /tmp/uji.png
```

`post_threads` without `--dry-run`, and anything with `openclaw message
send` or `openclaw cron add`, acts on the real account and the owner's
WhatsApp — do not run those to test.
