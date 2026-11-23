# Konten Threads Otomatis — OpenClaw + Claude

Alur:

```
@lantip.ai.id (bisnis) — tema teknologi (AI, cloud, DevOps) & bisnis, 7 posting/hari
  usulan 06.30: jam08 (utas panjang) + jam10 · 11.00: jam12 + jam14 + jam16 · 17.00: jam18 + jam20
  posting 08.00 10.00 12.00 14.00 16.00 18.00 20.00 WIB
@nasir19noor (utama) — tema teknologi, parenting, kuliner, 3 posting/hari
  usulan 07.00: u09 (utas panjang) · 10.30: u12 · 17.30: u19
  posting 09.00 12.00 19.00 WIB

cron "usulan" → riset sesuai tema akun → 2 opsi + visual per slot → WA pemilik
Anda balas "OK 12 1, OK u12 2" / "revisi 16 1: ..." / "skip u19" (dari nomor pemilik)
cron "posting" → opsi yang disetujui diposting ke akun slotnya → tautan ke WA
Minggu 21.00 WIB           cron "laporan" → laporan mingguan per akun (engagement, reply, follower, saran) → WA
                                           → disimpan sebagai acuan usulan berikutnya
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
  scripts/antrian.py        antrian usulan & persetujuan per slot
  scripts/post_threads.py   posting ke Threads API (utas berantai + gambar)
  scripts/laporan.py        laporan mingguan dari Threads Insights → SQLite + JSON/MD + pesan WA
pasang.sh                   memasang skill + mengisi nomor pemilik dari ~/.openclaw/.env
cron-setup.sh               mendaftarkan 17 cron job (bisnis 3+7, utama 3+3, 1 laporan); `utama` = 6 job utama saja
.github/workflows/deploy.yml  deploy otomatis ke server OpenClaw (self-hosted runner)
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
openclaw cron run <id "Threads usulan siang">   # usulan jam12, jam14, jam16 harus masuk ke WA pemilik
```
Balas "OK 12 1" dari nomor pemilik, lalu uji posting tanpa benar-benar memposting:
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
| `OK 14 2` | setujui opsi 2 slot 14.00 @lantip.ai.id (`jam14`) |
| `OK u12 1` | setujui opsi 1 slot 12.00 @nasir19noor (`u12`); `OK 12 …` selalu @lantip.ai.id |
| `OK 12 1, u12 2, 16 1` | setujui beberapa slot sekaligus |
| `OK 2` | hanya jika tinggal satu slot yang menunggu; selain itu bot menanyakan slotnya |
| `revisi 14 2: lebih santai, tambah sudut Purwokerto` | opsi 2 slot 14.00 ditulis ulang |
| `ganti topik 16` | 2 usulan baru untuk slot 16.00 |
| `skip 10` / `skip u19` | slot itu dilewati hari ini |
| `status` | ringkasan hari ini, semua slot kedua akun (`[bisnis]` / `[utama]`) |
| `contoh: <teks postingan Anda>` | disimpan sebagai acuan gaya bahasa |
| `daftar contoh` / `hapus contoh 3` | kelola contoh gaya |
| `buatkan konten tema parenting gen alpha untuk jam 20` | usulan bertema |
| `analisa tren teknologi minggu ini` | ringkasan + ide konten |
| `threads laporan` / `threads laporan @bisnis` | laporan mingguan sekarang (semua akun / satu akun) |

## Tema & jadwal per akun (sejak skill 1.9.0)

| Akun | Tema | Posting otomatis | Usulan dikirim |
|---|---|---|---|
| @lantip.ai.id (`bisnis`) | teknologi (AI, cloud, DevOps) dan bisnis | 7×: 08.00 (utas panjang), 10.00, 12.00, 14.00, 16.00, 18.00, 20.00 | 06.30, 11.00, 17.00 |
| @nasir19noor (`utama`) | teknologi, parenting, kuliner | 3×: 09.00 (utas panjang), 12.00, 19.00 | 07.00, 10.30, 17.30 |

Jadwal dan tema ada di `antrian.py` (`JADWAL`, `TEMA`; cek dengan `jalankan antrian jadwal`) dan harus sama dengan
`cron-setup.sh`. Slot akun utama bernama `u09`, `u12`, `u19`, dan dibalas dengan kode itu (`OK u12 1`), karena jam
12.00 dipakai kedua akun. `THREADS_AKUN_JADWAL` di `.env` tidak dipakai lagi (boleh dihapus).

**Menambah jadwal akun utama ke server yang sudah berjalan.** Job akun bisnis yang ada tetap dipakai; cukup:
```bash
bash cron-setup.sh utama      # 3 job usulan + 3 job posting untuk @nasir19noor
openclaw cron list            # total 17 job: bisnis 3+7, utama 3+3, laporan 1
```

## Jadwal 7 slot (sejak skill 1.8.0)

Akun bisnis (@lantip.ai.id) posting tiap 2 jam, **08.00–20.00 WIB**. Slot `jam08` berupa utas panjang (4–7 postingan), enam
slot lain satu postingan pendek. Usulan dikirim dalam **3 gelombang** (06.30, 11.00, 17.00), **2 opsi per slot**,
dengan topik yang tidak berulang dalam satu hari. Slot yang tidak disetujui sampai jamnya tidak diposting.
Desain bebas dipakai untuk satu opsi per gelombang; sisanya template yang tampilannya otomatis berganti.

**Pindah dari jadwal lama (pagi/siang/malam).** Nama slot lama sudah tidak dikenal, jadi 6 job lama harus diganti:
1. `openclaw cron list` → hapus job **Threads usulan pagi/siang/malam** dan **Threads posting pagi/siang/malam**
   (lihat `openclaw cron --help` untuk perintah hapusnya, mis. `openclaw cron rm <id>`). Job **Threads laporan
   mingguan** biarkan.
2. Daftarkan job baru. Paling mudah: hapus juga job laporan mingguan, lalu `bash cron-setup.sh` (mendaftarkan
   ke-11 job sekaligus). Atau jalankan hanya bagian usulan dan posting dari `cron-setup.sh`.
3. `openclaw cron list` → harus ada 3 job usulan, 7 job posting (`jam08` … `jam20`), 1 laporan.

Usulan lama yang tersimpan dengan slot pagi/siang/malam tetap terlihat di `status`, tetapi tidak akan diposting.

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
  menyusun usulan.
- **Syarat:** token setiap akun punya izin `threads_manage_insights`. Token lama belum punya: tambahkan izinnya di
  aplikasi Meta, buat token baru untuk tiap akun, isi `~/.openclaw/.env`, lalu `openclaw gateway restart`.
- **Sudah menjalankan `cron-setup.sh` sebelumnya?** Jangan ulangi (job lain jadi dobel); tambahkan job ini saja
  (ganti `<nomor pemilik>`):
  ```bash
  openclaw cron add --name "Threads laporan mingguan" --cron "0 21 * * 0" --tz "Asia/Jakarta" \
    --session isolated \
    --message "Jalankan skill konten-threads Mode 5: laporan mingguan semua akun, satu pesan WA per akun ke <nomor pemilik>, lalu simpan sarannya." \
    --announce --channel whatsapp --to "<nomor pemilik>"
  ```

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
Cron tidak perlu didaftarkan ulang saat deploy.

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
