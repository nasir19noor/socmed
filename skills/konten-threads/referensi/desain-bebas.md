# Panduan desain bebas (HTML/SVG → PNG)

Dipakai saat pemilik memilih gambar **"desain bebas"**, atau saat kamu ingin variasi visual (mis. utas pagi).
Kamu bertindak sebagai desainer grafis: buat **satu file HTML mandiri** yang khusus untuk isi postingan ini.

## Spesifikasi teknis (wajib)
- Kanvas tepat **1080 × 1350 px** (rasio 4:5). Set `html, body { width:1080px; height:1350px; margin:0; overflow:hidden; }`.
- Semua CSS di `<style>`, semua ilustrasi pakai **SVG inline** atau CSS (gradien, bentuk). Tanpa `<img>` dari internet,
  tanpa JavaScript eksternal. Satu-satunya sumber luar yang boleh: **Google Fonts**.
- Zona aman: jangan taruh teks penting dalam 64 px dari tepi.
- Ukuran teks minimal: judul ≥ 64 px, isi ≥ 32 px, keterangan kecil ≥ 24 px (dibaca di layar HP).
- Maksimal ±40 kata di dalam gambar. Gambar bukan tempat isi lengkap postingan.
- Kontras teks terhadap latar harus tinggi (teks gelap di latar terang atau sebaliknya).
- Sertakan handle akun (dari env `THREADS_HANDLE`, mis. `@akunanda`) kecil di pojok bawah.

## Arah desain
- Mulai dari **satu ide visual** yang langsung terkait isi: metafora, diagram sederhana, angka besar,
  perbandingan sebelum/sesudah, timeline, peta sederhana Banyumas, ikon buku/HP/anak, dsb.
- Variasikan tata letak antar postingan: angka raksasa, split dua kolom, kartu bertumpuk, poster tipografi,
  diagram alur, grafik batang sederhana (hanya dengan data yang bersumber).
- Palet: 2–3 warna + netral. Warna kategori sebagai aksen:
  teknologi `#2457d6`, buku `#b86b00`, parenting `#1f8a5b`, lokal `#b23a2a`, umum `#6a3fd1`.
- Font yang disarankan (Google Fonts): Plus Jakarta Sans, Fraunces, Space Grotesk, DM Serif Display, Inter.
  Selalu beri fallback: `font-family: 'Plus Jakarta Sans', system-ui, sans-serif;`.
- Sentuhan lokal untuk topik Purwokerto: siluet Gunung Slamet, motif batik Banyumasan sederhana, warna tanah/hijau.

## Larangan
- Tidak menggambar orang sungguhan, tokoh publik, logo/merek, atau karakter fiksi berhak cipta.
- Tidak menyalin desain poster/sampul buku yang sudah ada.
- Tidak memasukkan data/angka yang tidak ada sumbernya.

## Alur kerja
1. Tulis file ke `~/.openclaw/workspace/konten-threads/desain/<tanggal>-<slot>-<n>.html`.
2. Render:
   `{SKILL_DIR}/scripts/jalankan render_html --html <file.html> --out ~/.openclaw/workspace/konten-threads/gambar/<tanggal>-<slot>-<n>.png`
3. Jika muncul peringatan "isi melebihi kanvas" atau "DESAIN DITOLAK", perbaiki HTML lalu render ulang.
4. Jika tool membaca gambar tersedia, buka PNG hasilnya dan periksa: teks terbaca, tidak terpotong, tidak bertumpuk.
   Perbaiki maksimal 2 kali; jika masih gagal, pakai `render_visual` (template standar) sebagai cadangan.

## Kerangka awal

```html
<!DOCTYPE html>
<html lang="id"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;800&display=swap" rel="stylesheet">
<style>
  html,body{width:1080px;height:1350px;margin:0;overflow:hidden}
  body{font-family:'Plus Jakarta Sans',system-ui,sans-serif;background:#f3f6ff;color:#14161c;position:relative}
  /* ... desainmu ... */
</style></head>
<body>
  <!-- SVG ilustrasi + teks -->
</body></html>
```
