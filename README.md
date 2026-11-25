# Konten Threads Otomatis — OpenClaw + Claude

Alur:

```
Kedua akun posting OTOMATIS, tanpa usulan:
@lantip.ai.id (bisnis) — tema teknologi (AI, cloud, DevOps) & bisnis
  posting 08.00 (utas panjang) 10.00 12.00 14.00 16.00 18.00 20.00 WIB
@nasir19noor (utama) — tema teknologi, parenting, kuliner
  posting 09.00 (utas panjang) 12.00 19.00 WIB

30 menit sebelum slot  cron "buat"    → riset sesuai tema akun → 1 konten + visual → langsung disetujui (tanpa WA)
jam slot               cron "posting" → diposting ke akun slotnya → tautan ke WA
Sebelum tayang Anda bisa "skip 14" / "revisi u12 1: ..." / "ganti topik 16" (dari nomor pemilik)
Minggu 21.00 WIB       cron "laporan" → laporan mingguan per akun (engagement, reply, follower, saran) → WA
                                      → disimpan sebagai acuan konten berikutnya
Kapan saja: kirim "threads" dari nomor pemilik → bot bertanya topik, format, gambar, waktu → usulan → OK → posting
          atau chat bebas: "buatkan konten tema X" / "analisa tren buku minggu ini"
```

**Bot** = nomor WhatsApp OpenClaw. **Pemilik** = satu-satunya nomor yang boleh menyetujui dan memicu konten.
Nomor pemilik tidak ditulis di repo: isi `THREADS_PEMILIK` di `~/.openclaw/.env`, lalu `pasang.sh` memasukkannya ke skill.

## Isi paket

```
skills/konten-threads/
  SKILL.md                  instruksi agen (riset, gaya, alur persetujuan)
  referensi/sumber-tren.md  daftar sumber riset
  referensi/gaya-bahasa.md  suara akun & pola hook/utas
  referensi/contoh-postingan.md  postingan asli Anda sebagai acuan gaya
  scripts/contoh.py         tambah/daftar/hapus contoh gaya
  templates/visual.html     template visual 1080×1350, 7 tata letak
  scripts/render_visual.py  template standar → PNG
  scripts/render_html.py    desain bebas buatan Claude (HTML/SVG) → PNG
  referensi/desain-bebas.md aturan & arah desain bebas
  scripts/ragam.py          ingatan gaya visual agar gambar tidak seragam
  scripts/antrian.py        antrian konten per slot, jadwal & tema tiap akun
  scripts/post_threads.py   posting ke Threads API (utas berantai + gambar)
  scripts/laporan.py        laporan mingguan dari Threads Insights → SQLite + JSON/MD + pesan WA
pasang.sh                   memasang skill + mengisi nomor pemilik dari ~/.openclaw/.env
cron-setup.sh               mendaftarkan 21 cron job (bisnis 7+7, utama 3+3, 1 laporan); `reset` = hapus job Threads lalu daftarkan ulang
.github/workflows/deploy.yml  deploy otomatis ke server OpenClaw (self-hosted runner)
.github/workflows/hapus-gambar.yml  hapus semua gambar di server setiap hari 23.00 WIB
AGENTS-tambahan.md          aturan pemicu kata "threads" (tempel ke AGENTS.md)
env.example                 variabel yang perlu diisi
```

## Langkah pemasangan

### 1. Isi nomor pemilik, lalu pasang skill
Tambahkan ke `~/.openclaw/.env` (lihat `env.example`):
```bash
THREADS_PEMILIK=+62812xxxxxxx
```
Lalu dari folder repo ini:
```bash
bash pasang.sh
openclaw skills list | grep konten-threads
```
`pasang.sh` menyalin skill ke `~/.openclaw/workspace/skills/konten-threads`, mengisi nomor pemilik ke
`SKILL.md`, dan menambahkan aturan pemicu "threads" ke `AGENTS.md` (sekali saja). Contoh gaya yang sudah
tersimpan di server (`contoh-postingan.md`) **tidak ditimpa**. Jalankan ulang setiap kali repo diperbarui.

### 2. Pasang perender gambar di virtual environment
Semua skrip dijalankan lewat `scripts/jalankan`, yang otomatis memakai Python dari venv
`/home/openclaw/projects/threads/venv` (yaitu `/home/openclaw/projects/threads/venv/bin/python`).
Jika venv Anda pindah, set `KONTEN_VENV=/lokasi/baru` di `~/.openclaw/.env`.

```bash
source /home/openclaw/projects/threads/venv/bin/activate
pip install playwright
python -m playwright install chromium
sudo $(which python) -m playwright install-deps chromium  # sekali saja, pustaka sistem untuk Chromium di Linux
deactivate
```
(Jika sudah ada Google Chrome/Chromium di server, skrip otomatis memakainya sebagai cadangan.)
Skrip lain hanya memakai pustaka bawaan Python, jadi tidak perlu paket tambahan.

Uji:
```bash
~/.openclaw/workspace/skills/konten-threads/scripts/jalankan render_visual \
  --kategori lokal --judul "Mendoan *naik kelas*" --isi "Uji visual" --out ~/uji.png
```

### 3. Siapkan akses Threads API
1. Buka developers.facebook.com → **Create App** → pilih use case **Access the Threads API**.
2. Tambahkan izin `threads_basic`, `threads_content_publish`, dan `threads_manage_insights` (untuk laporan mingguan).
3. Di **App roles → Roles**, tambahkan akun Threads Anda sebagai *Threads Tester*, lalu terima undangannya di aplikasi Threads (Settings → Account → Website permissions).
4. Pakai **User Token Generator** di dashboard aplikasi untuk membuat token, lalu tukar ke **long-lived token** (berlaku 60 hari dan bisa diperpanjang).
5. Isi `~/.openclaw/.env` sesuai `env.example`, lalu cek:
   ```bash
   ~/.openclaw/workspace/skills/konten-threads/scripts/jalankan post_threads --cek
   ```
   Perintah ini juga menampilkan `THREADS_USER_ID` yang benar.
6. Daftar gratis di api.imgbb.com untuk `IMGBB_API_KEY` (tempat gambar di-hosting agar bisa diambil Threads).

### 4. Pastikan agen boleh menjalankan perintah
Skill ini menjalankan `scripts/jalankan` (Python dari venv) dan `openclaw message send`. Pastikan tool **exec** aktif untuk agen utama (lihat `openclaw approvals` / pengaturan tools). Model utama sebaiknya Claude, mis.:
```bash
openclaw config set agents.defaults.model.primary "anthropic/claude-sonnet-4-6"
```
(gunakan model Claude terbaru yang tersedia di akun Anda).

### 5. WhatsApp — sudah sesuai
Pastikan `allowFrom` OpenClaw memuat nomor pemilik (`THREADS_PEMILIK`). Skill hanya menerima perintah konten dari nomor itu; nomor lain di allowlist tetap bisa chat biasa.

### 5b. Trigger manual "threads"
Sudah dipasang oleh `pasang.sh` (langkah 1): isi `AGENTS-tambahan.md`, dengan nomor pemilik terisi, ditambahkan ke
akhir `~/.openclaw/workspace/AGENTS.md` sehingga agen selalu memakai skill ini setiap kali menerima kata "threads".

### 6. Daftarkan cron
```bash
bash cron-setup.sh
openclaw gateway restart
```

### 7. Uji coba
```bash
openclaw cron list
openclaw cron run <id "Threads buat jam12">     # konten jam12 dibuat & disetujui, tanpa pesan WA
~/.openclaw/workspace/skills/konten-threads/scripts/jalankan antrian status
```
Uji posting tanpa benar-benar memposting:
```bash
~/.openclaw/workspace/skills/konten-threads/scripts/jalankan post_threads --slot jam12 --dry-run
```

## Perintah via WhatsApp (dari nomor pemilik)

### Trigger manual
Kirim **`threads`** ke nomor bot. Bot akan bertanya dalam satu pesan:
1. Topik: tren hari ini, teknologi, bisnis, parenting, kuliner, lokal Purwokerto, atau tema sendiri
2. Format: pendek atau panjang (utas)
3. Gambar: kartu judul, daftar poin, kutipan besar, foto sendiri, tanpa gambar, atau **desain bebas** (Claude mendesain HTML/SVG khusus)
4. Waktu posting: langsung setelah OK, atau jam tertentu

Cukup jawab singkat, misalnya `1c 2a 3c 4a`. Bisa juga langsung lengkap dalam satu pesan, misalnya
`threads parenting panjang daftar poin jam 15.30`. Kirim `threads cepat` untuk memakai pilihan default.
Bot lalu mengirim 2 opsi. Balas `OK 1` untuk menyetujui, dan konten akan diposting langsung atau sesuai jam yang dipilih.

### Perintah lain

| Ketik | Hasil |
|---|---|
| `skip 10` / `skip u19` | slot itu dilewati hari ini (sebelum jam posting) |
| `revisi 14 1: lebih santai` / `revisi u12 1: …` | konten otomatis slot itu ditulis ulang sebelum tayang |
| `ganti topik 16` | konten slot 16.00 dibuat ulang dengan topik lain |
| `OK 1` / `OK 2` | hanya untuk usulan manual (`threads …` atau "buatkan konten") |
| `status` | ringkasan hari ini, semua slot kedua akun (`[bisnis]` / `[utama]`) |
| `contoh: <teks postingan Anda>` | disimpan sebagai acuan gaya bahasa |
| `daftar contoh` / `hapus contoh 3` | kelola contoh gaya |
| `buatkan konten tema parenting gen alpha` | usulan manual bertema (2 opsi, perlu `OK`) |
| `analisa tren teknologi minggu ini` | ringkasan + ide konten |
| `threads laporan` / `threads laporan @bisnis` | laporan mingguan sekarang (semua akun / satu akun) |

## Tema & jadwal per akun (sejak skill 1.12.0: keduanya otomatis)

| Akun | Tema | Posting | Konten dibuat |
|---|---|---|---|
| @lantip.ai.id (`bisnis`) | teknologi (AI, cloud, DevOps) dan bisnis | 7×: 08.00 (utas panjang), 10.00, 12.00, 14.00, 16.00, 18.00, 20.00 | 30 menit sebelumnya (07.30 … 19.30) |
| @nasir19noor (`utama`) | teknologi, parenting, kuliner | 3×: 09.00 (utas panjang), 12.00, 19.00 | 08.30, 11.30, 18.30 |

**Tanpa usulan.** Untuk tiap slot ada dua cron job: **"Threads buat <slot>"** 30 menit sebelum jam posting membuat
satu konten sesuai tema akun (riset, tulisan, gambar) dan menyimpannya sebagai sudah disetujui, tanpa pesan WA;
**"Threads posting <slot>"** di jam slotnya memposting dan mengirim tautannya ke WA, jadi Anda bisa memeriksa dan
menghapusnya di aplikasi Threads bila perlu. Sebelum tayang Anda masih bisa `skip 14`, `revisi 14 1: …`,
`ganti topik 14`, atau `status` (`u12` dst. untuk @nasir19noor). Karena tidak diperiksa dulu, konten otomatis
menghindari topik sensitif (duka, politik, SARA, kesehatan berisiko, isu hukum, saran investasi) dan memilih topik
evergreen bila kabar terbaru belum pasti. Konten juga **tidak mengarang pengalaman pribadi** (mis. "sore ini saya
beli mendoan…", "anak saya tadi…"); sudutnya fakta, tips, opini, atau pertanyaan ke pembaca. Cerita pribadi hanya
dipakai bila Anda sendiri yang menceritakannya.

Jadwal dan tema ada di `antrian.py` (`JADWAL`, `TEMA`, `OTOMATIS`, `jam_buat`; cek dengan `jalankan antrian jadwal`)
dan harus sama dengan `cron-setup.sh`. Slot akun utama bernama `u09`, `u12`, `u19` (jam 12.00 dipakai kedua akun).
`THREADS_AKUN_JADWAL` di `.env` tidak dipakai lagi (boleh dihapus).

### Hapus semua cron job Threads dan daftarkan ulang

Dipakai saat pindah versi, atau bila daftar job di server tidak lagi cocok dengan repo (mis. job buatan tangan).
Job yang namanya diawali **"Threads "** dihapus semua, lalu 21 job didaftarkan ulang: bisnis 7 buat + 7 posting,
utama 3 buat + 3 posting, laporan mingguan 1. Job bawaan OpenClaw (Heartbeat, memory) tidak disentuh.

- **Dari GitHub:** **Actions → Deploy konten-threads → Run workflow**, centang **reset_cron**, lalu Run. Skill
  dipasang dulu, kemudian cron di-reset; ringkasannya tampil di halaman run.
- **Dari server:** `bash cron-setup.sh reset` (di folder repo).

Cek hasilnya dengan `openclaw cron list`. `bash cron-setup.sh` tanpa `reset` hanya menambah job, jadi jangan dijalankan
di server yang sudah punya job Threads (job akan dobel).

## Laporan mingguan

Setiap **Minggu 21.00 WIB** bot mengirim **satu pesan WA per akun** (@nasir19noor = `utama`,
@lantip.ai.id = `bisnis`): jumlah utas, views, interaksi dan rasionya, **penambahan follower**, utas dengan
interaksi / reply / views terbanyak dan yang paling sepi, pola per kategori, waktu, format, dan jenis visual,
angka final minggu lalu, tautan 3 utas teratas, lalu 3 saran minggu depan dari Claude. Pola waktu dibandingkan
per jam posting (dibulatkan ke jam terdekat), jadi terlihat slot mana yang paling ramai.

- **Rentang:** Senin 00.00 WIB s.d. saat laporan dibuat; postingan yang dibuat manual di aplikasi Threads ikut dihitung.
  Interaksi = like + reply + repost + quote + share; metrik sebuah utas diambil dari postingan pertamanya.
- **Follower:** API hanya memberi jumlah saat ini, jadi laporan pertama mencatat titik awal; penambahan tampil mulai
  laporan berikutnya. Catat titik awal lebih cepat: `jalankan laporan snapshot`.
- **Disimpan** di `~/.openclaw/workspace/konten-threads/laporan/`: `laporan.db` (SQLite: postingan, metrik per
  pengambilan, follower, laporan + saran), `<akun>/<YYYY-Www>.json` dan `.md`, serta `pelajaran.md`
  (4 laporan terakhir + tren 8 minggu per akun). Agen membacanya (`jalankan laporan ringkas --akun …`) sebelum
  membuat konten.
- **Syarat:** token setiap akun punya izin `threads_manage_insights`. Token lama belum punya: tambahkan izinnya di
  aplikasi Meta, buat token baru untuk tiap akun, isi `~/.openclaw/.env`, lalu `openclaw gateway restart`.
- **Job laporan belum ada di server?** Jalankan reset cron (lihat *Hapus semua cron job Threads dan daftarkan
  ulang*); job laporan ikut didaftarkan.

## Deploy otomatis (GitHub Actions)

Setiap push ke `main` yang mengubah `skills/`, `pasang.sh` atau `AGENTS-tambahan.md` menjalankan
`.github/workflows/deploy.yml` di server OpenClaw: memeriksa skrip, **mengosongkan
`~/.openclaw/workspace/skills/`** (contoh gaya yang tersimpan dari WhatsApp tetap dipertahankan), memasang skill
(`pasang.sh`, yaitu salin `skills/konten-threads` ke `~/.openclaw/workspace/skills/`), `chmod +x` skrip, lalu
`openclaw gateway restart`.

> ⚠️ Karena folder `skills/` dikosongkan setiap deploy, skill lain yang dipasang manual di server ikut terhapus.
> Simpan skill lain di repo ini juga, atau pasang di luar folder `skills/` itu. Bisa juga dijalankan manual dari tab **Actions → Deploy konten-threads → Run workflow**.

Workflow ini berjalan **di server itu sendiri**, lewat self-hosted runner. Pasang sekali, sebagai user `openclaw`:
1. GitHub → repo ini → **Settings → Actions → Runners → New self-hosted runner** (Linux), ikuti perintahnya
   di folder mis. `~/actions-runner`. Saat `config.sh` menanyakan label, tambahkan **`contabo-2-openclaw`**.
2. Jalankan sebagai layanan: `sudo ./svc.sh install openclaw && sudo ./svc.sh start`.
3. Pastikan `openclaw` ada di PATH runner: jika `command -v openclaw` menunjuk ke folder di luar PATH
   standar, tambahkan folder itu ke `~/actions-runner/.path`, lalu `sudo ./svc.sh stop && sudo ./svc.sh start`.

`THREADS_PEMILIK` tetap harus ada di `~/.openclaw/.env` — workflow berhenti dengan pesan jelas jika belum.
Push tidak menyentuh cron. Untuk menghapus semua job Threads dan mendaftarkannya ulang, jalankan workflow secara manual
dengan **reset_cron** dicentang (lihat *Hapus semua cron job Threads dan daftarkan ulang*).

### Hapus gambar harian

`.github/workflows/hapus-gambar.yml` berjalan setiap hari pukul **23.00 WIB** (cron GitHub `0 16 * * *`, UTC) di
runner yang sama dan menghapus semua isi `~/.openclaw/workspace/konten-threads/gambar/` (PNG dan file `.akun`).
Jam itu sesudah posting terakhir (20.00) dan sebelum konten pertama dibuat (07.30), jadi gambar slot terjadwal tidak
ikut terhapus sebelum tayang; gambar yang sudah diposting sudah tersimpan di imgbb/Threads. Jumlah file yang dihapus
tampil di ringkasan run. Bisa juga dijalankan manual: **Actions → Hapus gambar konten-threads → Run workflow**.
Catatan: usulan manual untuk tanggal berikutnya yang gambarnya dibuat hari ini ikut terhapus dan perlu dirender ulang.
Jadwal GitHub bisa terlambat beberapa menit, dan hanya berjalan dari branch default (`main`).

## Beberapa akun Threads

Akun **`utama`** = @nasir19noor, akun **`bisnis`** = @lantip.ai.id; keduanya punya jadwal dan tema sendiri (lihat
*Tema & jadwal per akun*). Di luar jadwal, akun mana pun bisa diposting sesuai permintaan (`threads @bisnis …`), dengan
gaya bahasa dan contoh yang sama; persetujuan tetap dari nomor pemilik. Cek dengan `jalankan post_threads --daftar-akun`:
tiap akun ditandai jam terjadwalnya, dan ada peringatan bila akun berjadwal belum punya token.

**Menambah akun** (mis. `bisnis`):
1. Di aplikasi Meta yang sama, tambahkan akun Threads itu sebagai *Threads Tester* (langkah 3 di atas), terima
   undangannya dari akun tersebut, lalu buat long-lived token untuknya.
2. Tambahkan ke `~/.openclaw/.env` (lihat `env.example`):
   ```bash
   THREADS_USER_ID_BISNIS=...
   THREADS_ACCESS_TOKEN_BISNIS=...
   THREADS_HANDLE_BISNIS=@akunbisnis
   ```
3. Cek: `jalankan post_threads --cek --akun bisnis`, lalu `jalankan post_threads --daftar-akun`.
4. `openclaw gateway restart`.

**Memakai**: sebut akunnya di pesan pemicu, mis. `threads @bisnis teknologi pendek` atau `threads akun bisnis …`.
Tanpa sebutan akun, konten untuk `utama`. Setiap usulan menyebut handle tujuannya, jadi periksa sebelum `OK`.

**Watermark gambar** selalu handle akun yang memposting: @lantip.ai.id untuk slot `jam…`, @nasir19noor untuk slot
`u…` (atau akun yang disebut untuk slot manual). Handle diambil dari `THREADS_HANDLE` / `THREADS_HANDLE_BISNIS` di
`.env`; jika kosong, dipakai kedua handle di atas. Gambar dengan watermark akun lain ditolak saat disimpan ke antrian.

## Perawatan
- **Token Threads** berlaku 60 hari, per akun. Perpanjang tiap bulan dengan `jalankan post_threads --refresh-token`
  (akun lain: `--refresh-token --akun bisnis`), atau tambahkan cron bulanan untuk itu.
- Riwayat & antrian: `~/.openclaw/workspace/konten-threads/antrian/` (satu file JSON per hari).
- Laporan: `~/.openclaw/workspace/konten-threads/laporan/` (tidak tersentuh deploy; cadangkan bersama workspace).
- Ubah gaya tulisan di `referensi/gaya-bahasa.md`, sumber di `referensi/sumber-tren.md`, warna/desain di `templates/visual.html`
  (tata letak) dan `scripts/render_visual.py` (palet & font), arah seni desain bebas di `referensi/desain-bebas.md`.
- Visual otomatis bervariasi: `render_visual` memilih tata letak (kartu, poster, split, catatan, gelap, bingkai, majalah),
  pasangan font, dan varian palet yang paling lama tidak dipakai; desain bebas memakai arah seni yang berbeda tiap kali.
  Lihat riwayatnya: `jalankan ragam`; saran arah berikutnya: `jalankan ragam --saran`.
- Konten **tidak pernah** diposting tanpa balasan "OK" dari Anda.
