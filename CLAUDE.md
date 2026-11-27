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
  referensi/desain-bebas.md     free-form HTML/SVG visuals: art-direction menu, fonts, rules
  templates/visual.html         1080×1350 template with 7 layouts (body class tata-*)
  scripts/jalankan              bash entry point: runs <script>.py with the venv's Python
  scripts/antrian.py            per-day queue of proposals and approvals (JSON)
  scripts/post_threads.py       posts the approved option to the Threads API
  scripts/render_visual.py      template card → PNG (Playwright, Chrome fallback)
  scripts/render_html.py        agent-written HTML/SVG → PNG, with safety checks
  scripts/foto.py               find/download free-license real photos (Commons, Openverse)
  scripts/ragam.py              visual style memory (ragam.json) so images don't look alike
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

**Image cleanup**: `.github/workflows/hapus-gambar.yml`, a GitHub schedule
(`0 16 * * *` UTC = 23:00 WIB, plus manual dispatch) on the same runner,
deletes everything in `~/.openclaw/workspace/konten-threads/gambar/`
(PNGs and `.akun` sidecars), after listing them (mtime, size, name) in the
log and the run summary. It is deliberately not an OpenClaw cron job.
23:00 WIB sits between the last post (20:00) and the first "Threads buat"
(07:00); images are not needed after posting (they are uploaded to imgbb).
A manual proposal for a later date whose image was rendered earlier loses
it and must be re-rendered.

Nothing here is a service or a build: `pasang.sh` copies the skill folder
onto the OpenClaw host (Linux, user `openclaw`) and the agent runs the
scripts there. It keeps the host's `referensi/contoh-postingan.md` (the
owner adds examples to it from WhatsApp, so the repo copy is only the
seed), and replaces its own marked block in `AGENTS.md`, so it is safe to
re-run after every update.

## How it works

**Six modes** (SKILL.md):
1. **Proposals** — only for owner requests ("buatkan konten …") and manual
   slots: research on the account's theme, 2 options, visuals, `antrian
   simpan`, each option to WhatsApp, wait for `OK`. Scheduled slots of both
   accounts have **no proposals** — see mode 6. `bisnis` (@lantip.ai.id,
   technology; business only as the business side of tech) posts `jam08` …
   `jam20` every 2 h, **one rubric per slot**; `utama` (@nasir19noor,
   personal & general knowledge) posts 5 daily slots `u09` `u1230` `u15`
   `u17` `u1930` plus one weekly slot per day (`usen` Mon 10:30, `usel`
   Tue 10:30, `urab` Wed 10:30, `ukam` Thu 10:20, `ujum` Fri 09:40, `usab`
   Sat 09:23, `umin` Sun 09:47 — odd minutes are the owner's choice).
   Weekly slots carry a cron day in `antrian.HARI` (0 = Sunday);
   `slot_aktif()` hides them from `status` on other days and `simpan`
   refuses them off-day. Schedules, themes and rubrics live in
   `antrian.JADWAL` / `HARI` / `TEMA` / `RUBRIK` (`antrian jadwal` prints
   them). `RUBRIK[slot]` holds `nama`, `format` (panjang = 4–7-post
   thread, pendek = one post; `SLOT_PANJANG` is derived from it), `visual`
   (`bebas` / `foto` / `foto-tokoh` / `ilustrasi` / `tanpa`), `wajib`,
   `ingat` (days of topic memory) and optional `boleh_pendek` (a long slot
   may be saved as one post when there is little material — the owner's
   rule for utama; a 1-post option with no `format` is inferred pendek). bisnis: jam08 Deep Dive (long), jam10 Kisah Fiktif
   (long), jam12 Fun Fact (photo bg), jam14 Kutipan Tokoh (figure photo bg),
   jam16 Kisah Nyata (long, photo), jam18 Tips & Trik (photo if relevant),
   jam20 Berita (no image, news URL). `antrian simpan` enforces `wajib`:
   `fiktif` = post 1 contains "fiktif" (the disclosure), `tautan` = post 1
   has a URL, `sumber` = a source URL, `polling` = 2–4 options ≤ 25 chars
   (`polling` on any other rubric is rejected); visual `tanpa` rejects `gambar`, and
   a scheduled slot's format must match. `antrian rubrik --slot S` prints
   the rubric plus that slot's topics for `ingat` days and today's other
   slots — Mode 6 reads it first.
2. **Owner replies** — `OK n`, `revisi n: …`, `ganti topik`, `skip`,
   `status`, `contoh: …`, free requests ("buatkan konten …", "analisa …").
3. **Posting** — one cron per slot (bisnis every 2 h 08.00–20.00, utama
   per `JADWAL`/`HARI`): `jalankan post_threads --slot <slot>`; posts
   only an approved option (auto slots are approved on save). Before it
   goes live the owner can `skip 14`, `revisi 14 1: …`, `ganti topik 14`
   (utama uses the slot name: `u1230`, `ujum`, …; a bare `12` is always
   bisnis). A text-only first post gets `poll_attachment` from the
   option's `polling` (option_a…d, JSON string), otherwise
   `link_attachment` from its first URL.
4. **Manual trigger** — a message starting with `threads` from the owner: a
   one-message wizard (topic, format, image, when), 2 options in slot
   `manualN`, posted immediately or by a one-shot cron (`--at`, UTC).
5. **Weekly report** — cron Sunday 21.00 WIB, or `threads laporan [@akun]`:
   `jalankan laporan buat` prints one block per account; the agent adds 3
   suggestions, sends one WhatsApp message per account, and stores the
   suggestions with `laporan saran`.
6. **Auto-post** (accounts in `antrian.OTOMATIS` — both) — cron "Threads
   buat <slot>" 60 min before a long-thread slot and 30 min before a short
   one (`antrian.jam_buat`): read `antrian rubrik`, research,
   write **one** option, render a visual, `antrian simpan` — which, for an
   auto slot, requires exactly one option and stores it already
   `disetujui` (`otomatis: true`; `ganti` keeps it approved). No WhatsApp
   proposal; "Threads posting <slot>" posts it and sends the link. Stricter
   content rules apply (SKILL.md Mode 6), since nobody reviews before it
   goes live.

**Cron** (`cron-setup.sh`): 39 jobs (19 slots × "buat" + "posting", plus
the weekly report). Slots, times, days and formats come from `python3
skills/konten-threads/scripts/antrian.py cron-tabel` (one line per slot:
akun slot menit_buat jam_buat menit_posting jam_posting hari format;
hari `*` or 0–6), read **before** any reset deletes jobs; the script
aborts unless every line has 8 fields, and the job count is derived. Changing a
slot's format moves its "buat" time, so it needs a cron reset. `bash cron-setup.sh reset` removes every job whose
name starts with `Threads ` (`openclaw cron list --all --json` →
`openclaw cron remove <id>`; the JSON shape is undocumented, so the parser
accepts a bare array or an object holding one, skips any banner text, and
aborts on anything else rather than risk duplicates) and registers the set
again; OpenClaw's own jobs are left alone. The deploy workflow runs it only
on a manual dispatch with `reset_cron` ticked; a push never touches cron.
Without `reset` the script only adds, so re-running it duplicates jobs.

**Reports** (`laporan.py`, stdlib only — `sqlite3`): Threads Insights
(`/{user}/threads` since/until, `/{media}/insights` views/likes/replies/
reposts/quotes/shares, `/{user}/threads_insights` followers_count). Needs
the token permission `threads_manage_insights`. Data lives in
`$KONTEN_DATA_DIR/../laporan/` (outside `skills/`, so deploys never wipe
it): `laporan.db` with tables `postingan`, `metrik` (one row per post per
fetch, latest wins), `follower` (snapshots), `laporan` (summary JSON +
`saran`); plus `<akun>/<YYYY-Www>.json|.md` and a generated
`pelajaran.md`. Week = Monday 00.00 WIB to now; last week is re-fetched
for final numbers. The "Waktu" pattern buckets posts by nearest hour
(`waktu_bagian`); scheduled slots are on the hour, so slots compare directly. Follower growth
= now minus the latest snapshot at least 6 days old, so the first report is only a baseline. Category /
format / visual / slot come from the queue (`media_ids[0]` of posted
slots); visual type is inferred (`desain/<stem>.html` = free design,
`gambar/` = template). A thread's numbers are its first post's. Mode 1
reads `laporan ringkas --akun` before choosing topics. JSON + SQLite for
now; PostgreSQL is planned later, so keep the SQL portable (nothing
SQLite-only beyond `INSERT OR REPLACE` / `ON CONFLICT`).

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

**Rendering**: `render_visual.py` fills `templates/visual.html`: 7 layouts
(kartu, poster, split, catatan, gelap, bingkai, majalah), 7 font pairings and
3 palette variants per `kategori`; `*accent*` in titles, `--poin` list,
`--angka` big stat, `--gaya kutipan`. Layout, font and palette default to
`auto` = least recently used, recorded in `ragam.json` (next to the queue
folder) by `ragam.py`. `render_html.py` renders an agent-written HTML file,
**rejects external resources** except Google Fonts (and local files other
than photos fetched by `foto.py`, whose `kredit` text must appear in the
design — see *Real photos*), warns when content
overflows 1080×1350, and records the art direction (`--arah`) so the next
free design picks another (`jalankan ragam --saran`). Both try Playwright
first, then a system Chrome/Chromium/Edge (Linux, macOS, Windows paths).
Goal: no two consecutive visuals look alike — don't hard-code a single look.

**Watermark** = the posting account's handle. `render_visual` and
`render_html` require `--slot` (account from `antrian.AKUN_SLOT`) or
`--akun <name|@handle>`; the handle comes from `antrian.handle_akun`
(`THREADS_HANDLE[_AKUN]`, falling back to `HANDLE_BAWAAN`). `render_html`
rejects a design missing that handle or containing another account's. Both
write `<png>.akun` with the handle, and `antrian simpan` refuses an image
whose `.akun` names a different account (images without one, e.g. the
owner's photos, pass).

**Real photos** (SKILL 1.14.0): for a concrete subject (a dish, a public
figure, a place) the agent tries a real photo first. `foto.py cari <kata>`
searches Wikimedia Commons and Openverse; `foto.py ambil <commons:File:…|
openverse:<id>>` re-reads the license **from the source API** (never from
the agent), accepts only CC0 / public domain / CC BY / CC BY-SA (NC and ND
rejected: images get text and the bisnis account is commercial-ish), checks
the bytes are JPG/PNG/WebP (≤ 20 MB), and saves to `<gambar>/foto/` with
`<file>.sumber.json` (`kredit`, `halaman`, …). Folder from
`KONTEN_GAMBAR_DIR`, default `~/.openclaw/workspace/konten-threads/gambar`,
so the daily `hapus-gambar` workflow clears photos too. The photo is used
only in a free design (`render_html`), which checks every `file:`/absolute
reference sits in that folder with a sidecar and that the `kredit` text is
visible (tags stripped, case- and whitespace-insensitive). People: public
figures only, neutral context, no children; no photos from news sites,
Instagram, Google Images or restaurant sites.

**Accounts**: several Threads accounts, one approver (the owner), one voice.
`utama` uses `THREADS_USER_ID` / `THREADS_ACCESS_TOKEN` / `THREADS_HANDLE`;
another account `x` uses the same names suffixed `_X`
(`post_threads.nama_env`; `antrian.muat_env` is the one `.env` loader,
`post_threads` reuses it). Each scheduled slot belongs to one account
(`antrian.AKUN_SLOT`, built from `JADWAL`; the old `THREADS_AKUN_JADWAL`
is ignored). `antrian simpan` fills it in for scheduled slots and refuses any other;
manual slots default to `utama`, or `--akun` (`threads @bisnis …`). Each slot
stores its `akun`, and `post_threads --slot` posts to that account, so a
one-shot cron needs no account argument. `--daftar-akun` lists accounts
from the env (names and handles only); `--cek` / `--refresh-token` take
`--akun`. Proposals must name the target handle.

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
  hoaxes, or other people's personal data. Real people in visuals: only
  public figures via `foto.py` (free license, credit shown), never private
  people or children.
- **No fictional anecdotes** (both accounts, since SKILL 1.13.0): never
  invent first-person events ("tadi sore saya beli mendoan…", "anak saya
  tadi…"). Opinions are fine; personal stories only if the owner told them.
- **Voice**: the agent reads `contoh-postingan.md` (the owner's own posts)
  before `gaya-bahasa.md` and imitates style, never content. First person
  "saya", no emoji or hashtags in posts.
- `contoh.py` rewrites `contoh-postingan.md` in place, splitting on `---`
  lines; keep that separator format if you edit the file by hand.

## Testing

`laporan.py` calls the live API; to test it offline, replace
`post_threads.http` with a fake returning Graph-shaped JSON (see
`laporan.insight_postingan` / `daftar_postingan`) and point
`KONTEN_DATA_DIR` and `HOME` at a temp folder.

There is no test suite. Safe checks that touch nothing live:

```bash
cd skills/konten-threads/scripts
KONTEN_DATA_DIR=/tmp/antrian ./jalankan antrian slot-baru
KONTEN_DATA_DIR=/tmp/antrian ./jalankan antrian simpan --slot jam12 < opsi.json
KONTEN_DATA_DIR=/tmp/antrian ./jalankan antrian setujui --slot jam12 --opsi 1
KONTEN_DATA_DIR=/tmp/antrian ./jalankan post_threads --slot jam12 --dry-run
./jalankan render_visual --kategori lokal --judul "Uji *visual*" --isi "Tes" --out /tmp/uji.png
```

`post_threads` without `--dry-run`, and anything with `openclaw message
send` or `openclaw cron add`, acts on the real account and the owner's
WhatsApp — do not run those to test.
