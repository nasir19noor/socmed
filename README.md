# Konten Threads Otomatis — OpenClaw + Claude

Alur:

```
Kedua akun posting OTOMATIS, tanpa usulan:
@lantip.ai.id (bisnis) — tema teknologi (bisnis hanya sebagai sisi bisnis teknologi), satu rubrik per slot
  08.00 Deep Dive · 10.00 Kisah Fiktif · 12.00 Fun Fact · 14.00 Kutipan Tokoh
  16.00 Kisah Nyata · 18.00 Tips & Trik · 20.00 Berita
@nasir19noor (utama) — personal & pengetahuan, 5 rubrik harian + 1 rubrik mingguan
  09.00 Berita & Dampak · 12.30 Kisah Tokoh · 15.00 Kutipan Lucu · 17.00 Fun Fact · 19.30 Penjelasan Teknologi
  Sen 10.30 Pepatah Jawa · Sel 10.30 Tips & Trik · Rab 10.30 Kuliner · Kam 10.20 Polling
  Jum 09.40 Petuah Islami · Sab 09.23 Fun Fact Wisata · Min 09.47 Psikologi & Parenting

60/30 mnt sebelum slot cron "buat"    → baca rubrik → riset → 1 konten + visual → langsung disetujui (tanpa WA)
jam slot               cron "posting" → diposting ke akun slotnya → tautan ke WA
Sebelum tayang Anda bisa "skip 14" / "revisi u1230 1: ..." / "ganti topik 16" (dari nomor pemilik)
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
  scripts/foto.py           cari & unduh foto asli berlisensi bebas (Wikimedia Commons, Openverse)
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

**Foto asli:** bila topiknya subjek nyata (kuliner tertentu, tokoh publik, tempat), Claude berusaha memakai foto
aslinya, dicari lewat `jalankan foto cari "<subjek>"` lalu `jalankan foto ambil <id>`. Sumbernya hanya Wikimedia
Commons dan Openverse dengan lisensi bebas (CC0, domain publik, CC BY, CC BY-SA), dan lisensinya diperiksa skrip.
Foto dipakai dalam desain bebas dengan baris kredit kecil di gambar (mis. *Foto: Hersy ardianty a / Wikimedia
Commons, CC BY-SA 4.0*). Desain tanpa kredit ditolak `render_html`. Tokoh: hanya tokoh publik dalam konteks netral,
tanpa anak-anak. Foto dari situs berita, Instagram, atau Google Images tidak dipakai karena berhak cipta. Jika tidak
ada foto yang cocok, visual dibuat tanpa foto seperti biasa.

Cukup jawab singkat, misalnya `1c 2a 3c 4a`. Bisa juga langsung lengkap dalam satu pesan, misalnya
`threads parenting panjang daftar poin jam 15.30`. Kirim `threads cepat` untuk memakai pilihan default.
Bot lalu mengirim 2 opsi. Balas `OK 1` untuk menyetujui, dan konten akan diposting langsung atau sesuai jam yang dipilih.

### Perintah lain

| Ketik | Hasil |
|---|---|
| `skip 10` / `skip u1930` | slot itu dilewati hari ini (sebelum jam posting) |
| `revisi 14 1: lebih santai` / `revisi u1230 1: …` | konten otomatis slot itu ditulis ulang sebelum tayang |
| `ganti topik 16` | konten slot 16.00 dibuat ulang dengan topik lain |
| `OK 1` / `OK 2` | hanya untuk usulan manual (`threads …` atau "buatkan konten") |
| `status` | ringkasan hari ini, semua slot kedua akun (`[bisnis]` / `[utama]`) |
| `contoh: <teks postingan Anda>` | disimpan sebagai acuan gaya bahasa |
| `daftar contoh` / `hapus contoh 3` | kelola contoh gaya |
| `buatkan konten tema parenting gen alpha` | usulan manual bertema (2 opsi, perlu `OK`) |
| `analisa tren teknologi minggu ini` | ringkasan + ide konten |
| `threads laporan` / `threads laporan @bisnis` | laporan mingguan sekarang (semua akun / satu akun) |

## Tema & jadwal per akun (keduanya otomatis; rubrik @lantip.ai.id sejak skill 1.15.0)

| Akun | Tema | Posting | Konten dibuat |
|---|---|---|---|
| @lantip.ai.id (`bisnis`) | teknologi (AI, cloud, DevOps, keamanan, software); bisnis hanya sebagai sisi bisnis teknologi | 7×, satu rubrik per slot (tabel di bawah) | 60 menit sebelum utas panjang, 30 menit sebelum pendek |
| @nasir19noor (`utama`) | personal & pengetahuan (rubrik di bawah) | 6×: 5 slot harian + 1 slot mingguan | 60 menit sebelum utas panjang, 30 menit sebelum pendek |

### Jadwal gabungan kedua akun (WIB, urut jam)

Setiap hari: 7 posting @lantip.ai.id + 6 posting @nasir19noor (5 harian + 1 sesuai harinya) = **13 posting**.
Format: **utas** = utas panjang 4–7 postingan (@nasir19noor: boleh jadi pendek bila bahannya sedikit), **pendek** =
1 postingan. Jam di kurung = jam konten dibuat (cron "Threads buat").

| Jam posting | Hari | @lantip.ai.id (`bisnis`) | @nasir19noor (`utama`) |
|---|---|---|---|
| 08.00 | setiap hari | `jam08` Deep Dive · utas (07.00) | |
| 09.00 | setiap hari | | `u09` Berita & Dampak · utas · tanpa gambar, URL (08.00) |
| 09.23 | Sabtu | | `usab` Fun Fact Wisata · pendek (08.53) |
| 09.40 | Jumat | | `ujum` Petuah Islami · pendek (09.10) |
| 09.47 | Minggu | | `umin` Psikologi & Parenting · utas (08.47) |
| 10.00 | setiap hari | `jam10` Kisah Fiktif · utas (09.00) | |
| 10.20 | Kamis | | `ukam` Polling · pendek · tanpa gambar (09.50) |
| 10.30 | Senin | | `usen` Pepatah Jawa · pendek (10.00) |
| 10.30 | Selasa | | `usel` Tips & Trik · utas (09.30) |
| 10.30 | Rabu | | `urab` Kuliner · utas (09.30) |
| 12.00 | setiap hari | `jam12` Fun Fact · pendek (11.30) | |
| 12.30 | setiap hari | | `u1230` Kisah Tokoh · utas (11.30) |
| 14.00 | setiap hari | `jam14` Kutipan Tokoh · pendek (13.30) | |
| 15.00 | setiap hari | | `u15` Kutipan Lucu · pendek (14.30) |
| 16.00 | setiap hari | `jam16` Kisah Nyata · utas (15.00) | |
| 17.00 | setiap hari | | `u17` Fun Fact · pendek (16.30) |
| 18.00 | setiap hari | `jam18` Tips & Trik · pendek (17.30) | |
| 19.30 | setiap hari | | `u1930` Penjelasan Teknologi · utas (18.30) |
| 20.00 | setiap hari | `jam20` Berita · pendek · tanpa gambar, URL (19.30) | |
| 21.00 | Minggu | laporan mingguan (WA) | laporan mingguan (WA) |
| 23.00 | setiap hari | hapus gambar di server (GitHub Actions) | hapus gambar di server (GitHub Actions) |

Sumber kebenaran jadwal adalah `antrian.py` (`JADWAL`, `HARI`, `RUBRIK`); cek versi terkini di server dengan
`jalankan antrian jadwal`. Jika jadwal di kode berubah, perbarui tabel ini juga.

Rubrik @lantip.ai.id (`antrian.RUBRIK`; lihat dengan `jalankan antrian jadwal`):

| Jam | Slot | Rubrik | Format | Gambar |
|---|---|---|---|---|
| 08.00 | `jam08` | Deep Dive: penjelasan mendalam satu teknologi | utas panjang | template/desain bebas |
| 10.00 | `jam10` | Kisah Fiktif dengan pelajaran nyata, **diakui fiktif** di postingan pertama | utas panjang | template/desain bebas |
| 12.00 | `jam12` | Fun Fact teknologi (terverifikasi, bersumber) | pendek | foto asli sebagai background |
| 14.00 | `jam14` | Kutipan Tokoh teknologi (bersumber) | pendek | foto tokoh sebagai background |
| 16.00 | `jam16` | Kisah Nyata/sejarah teknologi | utas panjang | foto asli |
| 18.00 | `jam18` | Tips & Trik | pendek | foto asli bila relevan, selain itu template |
| 20.00 | `jam20` | Berita teknologi ≤ 24 jam + URL berita | pendek | tanpa gambar (kartu pratinjau tautan) |

`antrian simpan` menolak konten yang melanggar syarat rubrik: Kisah Fiktif tanpa kata "fiktif" di postingan 1,
Berita tanpa URL atau dengan gambar, Fun Fact/Kutipan/Kisah Nyata/Deep Dive tanpa `sumber`, atau format yang salah.
Agar topik tidak berulang, `jalankan antrian rubrik --slot <slot>` menampilkan topik slot itu dalam rentang
tertentu (Fun Fact 90 hari, Kisah Nyata 180 hari, Kutipan Tokoh 30 hari, dst.). Foto background dibuat dengan
`render_visual --foto <path dari jalankan foto ambil>`: foto penuh, gradasi gelap, kredit foto otomatis.
Postingan teks yang memuat URL (rubrik Berita) dikirim dengan `link_attachment`, sehingga Threads menampilkan kartu
pratinjau tautan. **Mengubah format atau jam slot perlu reset cron** (jam pembuatan ikut bergeser).

Rubrik @nasir19noor (sejak skill 1.16.0). *Panjang\** = utas panjang, tetapi bila bahannya memang sedikit, Claude
membuat 1 postingan pendek. Menit ganjil disengaja.

| Hari | Jam | Slot | Rubrik | Format | Gambar |
|---|---|---|---|---|---|
| setiap hari | 09.00 | `u09` | Berita & Dampak: berita tech terbaru, dampaknya, dampak bagi Indonesia, cara menghadapinya | panjang\* | tanpa gambar, URL berita |
| setiap hari | 12.30 | `u1230` | Kisah Tokoh dengan POV personal (refleksi, bukan pengalaman karangan) | panjang\* | foto tokoh + overlay |
| setiap hari | 15.00 | `u15` | Kutipan Lucu (yang tidak terverifikasi ditulis "sering dikaitkan dengan …") | pendek | foto tokoh + overlay |
| setiap hari | 17.00 | `u17` | Fun Fact umum | pendek | foto + overlay |
| setiap hari | 19.30 | `u1930` | Penjelasan Teknologi untuk awam | panjang\* | foto + overlay, atau diagram |
| Senin | 10.30 | `usen` | Pepatah Jawa | pendek | ilustrasi pepatah (desain HTML/SVG) |
| Selasa | 10.30 | `usel` | Tips & Trik teknologi | panjang\* | foto + overlay |
| Rabu | 10.30 | `urab` | Kuliner (sejarah/fungsi bumbu, dsb.) | panjang\* | foto + overlay |
| Kamis | 10.20 | `ukam` | Polling teknologi (2–4 pilihan) | pendek | tanpa gambar |
| Jumat | 09.40 | `ujum` | Petuah Islami dari sufi/tokoh Islam (bukan ayat/hadis, sumber kitab jelas) | pendek | kaligrafi/foto tempat + overlay, bukan tokoh |
| Sabtu | 09.23 | `usab` | Fun Fact Wisata/Geografi | pendek | foto tempat + overlay |
| Minggu | 09.47 | `umin` | Psikologi, Parenting & Relationship | panjang\* | foto + overlay |

Rubrik Polling dikirim sebagai polling Threads (`poll_attachment`, field `polling` di antrian). Slot mingguan hanya
bisa disimpan dan tampil di `status` pada harinya. Kode slot untuk perintah WA memakai nama slotnya (`skip u1230`,
`revisi ujum 1: …`).

**Tanpa usulan.** Untuk tiap slot ada dua cron job: **"Threads buat <slot>"** 60 menit (utas panjang) atau 30 menit
(pendek) sebelum jam posting membuat satu konten sesuai tema akun dan rubrik slotnya (riset, tulisan, gambar) dan menyimpannya sebagai sudah disetujui, tanpa pesan WA;
**"Threads posting <slot>"** di jam slotnya memposting dan mengirim tautannya ke WA, jadi Anda bisa memeriksa dan
menghapusnya di aplikasi Threads bila perlu. Sebelum tayang Anda masih bisa `skip 14`, `revisi 14 1: …`,
`ganti topik 14`, atau `status` (`u1230`, `ujum`, dst. untuk @nasir19noor). Karena tidak diperiksa dulu, konten otomatis
menghindari topik sensitif (duka, politik, SARA, kesehatan berisiko, isu hukum, saran investasi) dan memilih topik
evergreen bila kabar terbaru belum pasti. Konten juga **tidak mengarang pengalaman pribadi** (mis. "sore ini saya
beli mendoan…", "anak saya tadi…"); sudutnya fakta, tips, opini, atau pertanyaan ke pembaca. Cerita pribadi hanya
dipakai bila Anda sendiri yang menceritakannya. Satu-satunya fiksi: rubrik Kisah Fiktif @lantip.ai.id, yang
selalu diakui fiktif, memakai orang ketiga dengan nama karangan, dan tidak menyebut orang/perusahaan nyata.

Jadwal, tema, dan rubrik ada di `antrian.py` (`JADWAL`, `HARI`, `TEMA`, `RUBRIK`, `OTOMATIS`, `jam_buat`; cek dengan
`jalankan antrian jadwal`); `cron-setup.sh` membacanya lewat `antrian.py cron-tabel`. Slot akun utama: harian `u09`,
`u1230`, `u15`, `u17`, `u1930`; mingguan `usen`, `usel`, `urab`, `ukam`, `ujum`, `usab`, `umin`.
`THREADS_AKUN_JADWAL` di `.env` tidak dipakai lagi (boleh dihapus).

### Hapus semua cron job Threads dan daftarkan ulang

Dipakai saat pindah versi, atau bila daftar job di server tidak lagi cocok dengan repo (mis. job buatan tangan).
Job yang namanya diawali **"Threads "** dihapus semua, lalu 39 job didaftarkan ulang: bisnis 7 buat + 7 posting,
utama 12 buat + 12 posting (5 harian + 7 mingguan), laporan mingguan 1. Job bawaan OpenClaw (Heartbeat, memory) tidak disentuh.

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
Jam itu sesudah posting terakhir (20.00) dan sebelum konten pertama dibuat (07.00), jadi gambar slot terjadwal tidak
ikut terhapus sebelum tayang; gambar yang sudah diposting sudah tersimpan di imgbb/Threads. Sebelum menghapus,
workflow mencetak daftar file (waktu ubah, ukuran, nama) ke log dan ke ringkasan run, beserta jumlahnya. Bisa juga dijalankan manual: **Actions → Hapus gambar konten-threads → Run workflow**.
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
