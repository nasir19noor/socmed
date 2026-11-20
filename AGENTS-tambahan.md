## Trigger manual konten Threads

- Jika pesan WhatsApp dari **{{PEMILIK}}** berisi `threads` atau diawali kata `threads` (huruf besar/kecil bebas),
  SELALU gunakan skill **konten-threads** Mode 4 (trigger manual). Jangan menjawab sebagai obrolan biasa.
- Balasan pemilik berikutnya ("1c 2a 3b 4a", "OK 1", "revisi 2: ...", "batal") selama alur itu masih berjalan
  juga ditangani oleh skill konten-threads.
- Jika pesan `threads` datang dari nomor lain, balas: "Maaf, fitur Threads hanya untuk pemilik akun."
