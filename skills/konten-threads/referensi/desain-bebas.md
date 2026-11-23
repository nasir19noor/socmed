# Panduan desain bebas (HTML/SVG → PNG)

Dipakai saat pemilik memilih gambar **"desain bebas"**, dan untuk satu opsi per slot terjadwal.
Desain harus ringkas: satu file HTML pendek (±150 baris), tanpa ilustrasi SVG yang sangat rumit.
Kamu bertindak sebagai desainer grafis (art director): buat **satu file HTML mandiri** yang khusus untuk isi
postingan ini. Tujuannya: feed tidak terlihat seragam. Dua gambar berturut-turut **tidak boleh** terasa
seperti dari template yang sama.

## Spesifikasi teknis (wajib)
- Kanvas tepat **1080 × 1350 px** (rasio 4:5). Set `html, body { width:1080px; height:1350px; margin:0; overflow:hidden; }`.
- Semua CSS di `<style>`, semua ilustrasi pakai **SVG inline** atau CSS (gradien, bentuk, pola). Tanpa `<img>` dari internet,
  tanpa JavaScript eksternal. Satu-satunya sumber luar yang boleh: **Google Fonts**.
- Zona aman: jangan taruh teks penting dalam 64 px dari tepi.
- Ukuran teks minimal: judul ≥ 64 px, isi ≥ 32 px, keterangan kecil ≥ 24 px (dibaca di layar HP).
- Maksimal ±40 kata di dalam gambar. Gambar bukan tempat isi lengkap postingan.
- Kontras teks terhadap latar harus tinggi.
- Handle akun (dari env `THREADS_HANDLE` atau `THREADS_HANDLE_<AKUN>`, mis. `@akunanda`) tampil kecil di suatu tempat —
  posisinya bebas, tidak harus di kaki.

## Langkah 1: pilih arah seni yang berbeda
Jalankan `{SKILL_DIR}/scripts/jalankan ragam --saran` → 3 arah yang paling lama tidak dipakai.
Pilih salah satunya (atau arah lain dari daftar di bawah yang **tidak** muncul di `jalankan ragam`),
yang paling cocok dengan isi. Dalam satu slot, setiap opsi memakai arah yang berbeda.

| Arah | Ciri |
|---|---|
| **editorial majalah** | kop tebal, judul serif besar, kolom, nomor halaman/edisi, banyak ruang putih |
| **poster swiss** | grid tegas, sans-serif tebal rata kiri, blok warna datar, teks diputar 90°, angka besar |
| **risograph** | 2 warna cetak yang bertumpuk (multiply), tekstur bintik, sedikit meleset (misregistration) |
| **koran** | kertas kekuningan, judul headline serif hitam, garis kolom, kolom teks justify, cap tanggal |
| **neon teknologi** | latar sangat gelap, garis kisi, warna neon, font monospace untuk label, efek cahaya |
| **batik banyumasan** | motif SVG sederhana (parang, kawung) sebagai bingkai/latar, warna sogan cokelat-krem |
| **infografis** | satu diagram atau grafik SVG sebagai pusat (batang, donat, timeline, alur), angka bersumber |
| **catatan tangan** | kertas bergaris/kotak, font tulisan tangan untuk aksen, stabilo, coretan panah SVG |
| **kolase kertas** | potongan bentuk dengan bayangan, kertas sobek, selotip, label stiker miring |
| **minimalis jepang** | banyak ruang kosong, satu bentuk/lingkaran, teks kecil-tegas, aksen satu warna |
| **retro 70-an** | warna oranye-cokelat-mustard, garis pelangi melengkung, font display membulat |
| **cetak saring (screen print)** | 2–3 warna solid, bentuk besar berani, tekstur kasar, judul huruf kapital |
| **peta & denah** | peta/denah sederhana SVG (mis. Purwokerto, rute), pin, legenda |
| **papan tulis** | latar hijau/hitam papan, teks kapur putih, diagram tangan |

Arah lain yang sesuai isi juga boleh — yang penting berbeda dari yang dipakai belakangan.

## Langkah 2: rancang khusus untuk isinya
- Mulai dari **satu ide visual** yang langsung terkait isi: metafora, diagram sederhana, angka besar,
  perbandingan sebelum/sesudah, timeline, peta, ikon buku/HP/anak, dsb.
- **Palet:** bebas, pilih 2–3 warna + netral yang cocok dengan arah seni dan suasana topik. Warna kategori tidak wajib.
  Jangan memakai palet yang sama dengan gambar sebelumnya.
- **Font:** pasangkan display + teks yang cocok dengan arahnya. Contoh dari Google Fonts:
  serif — Fraunces, DM Serif Display, Playfair Display, Instrument Serif, Libre Caslon, Bodoni Moda, Young Serif;
  sans — Plus Jakarta Sans, Inter, Manrope, DM Sans, Space Grotesk, Bricolage Grotesque, Archivo, Syne, Unbounded;
  display — Archivo Black, Bebas Neue, Anton, Righteous, Shrikhand, Rubik Mono One;
  tangan — Caveat, Kalam, Patrick Hand; mono — JetBrains Mono, IBM Plex Mono, Space Mono.
  Selalu beri fallback, mis. `font-family: 'Syne', system-ui, sans-serif;`.
- **Komposisi:** variasikan titik berat (atas/bawah/kiri/tengah), skala judul, dan elemen penanda. Jangan selalu
  label kecil → judul → isi → kaki.
- Sentuhan lokal untuk topik Purwokerto/Banyumas: siluet Gunung Slamet, motif batik Banyumasan, mendoan, warna tanah/hijau.

## Hindari (ciri template standar)
Kombinasi **label pil + bulatan pastel di pojok + judul Fraunces + garis kaki `@akun —— tanggal`** adalah wajah
template `render_visual`. Desain bebas tidak boleh terlihat seperti itu.

## Larangan
- Tidak menggambar orang sungguhan, tokoh publik, logo/merek, atau karakter fiksi berhak cipta.
- Tidak menyalin desain poster/sampul buku yang sudah ada.
- Tidak memasukkan data/angka yang tidak ada sumbernya.

## Alur kerja
1. Tulis file ke `~/.openclaw/workspace/konten-threads/desain/<tanggal>-<slot>-<n>.html`.
2. Render dan catat arahnya:
   `{SKILL_DIR}/scripts/jalankan render_html --html <file.html> --out ~/.openclaw/workspace/konten-threads/gambar/<tanggal>-<slot>-<n>.png --arah "<arah>"`
3. Jika muncul peringatan "isi melebihi kanvas" atau "DESAIN DITOLAK", perbaiki HTML lalu render ulang.
4. Jika tool membaca gambar tersedia, buka PNG hasilnya dan periksa: teks terbaca, tidak terpotong, tidak bertumpuk,
   dan tidak mirip gambar sebelumnya. Perbaiki maksimal 1 kali; jika masih gagal, pakai `render_visual`
   (tata letak dipilih otomatis) sebagai cadangan.
