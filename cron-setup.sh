#!/usr/bin/env bash
# Mendaftarkan cron job konten Threads di OpenClaw (zona waktu WIB):
#   akun bisnis (@lantip.ai.id): 3 gelombang usulan + 7 posting (08.00–20.00 tiap 2 jam)
#   akun utama (@nasir19noor):   3 buat-konten otomatis (tanpa usulan) + 3 posting (09.00, 12.00, 19.00)
#   1 laporan mingguan
# Jalankan sekali: bash cron-setup.sh          (semua, 17 job)
#                  bash cron-setup.sh utama    (hanya 6 job akun utama)
#                  bash cron-setup.sh utama-buat (hanya 3 job buat-konten akun utama)
# Sudah pernah dijalankan? Jangan ulangi (job akan dobel) — lihat README.
set -euo pipefail
BAGIAN="${1:-semua}"
if [[ "$BAGIAN" != semua && "$BAGIAN" != utama && "$BAGIAN" != utama-buat ]]; then
  echo "Pemakaian: bash cron-setup.sh [utama | utama-buat]" >&2
  exit 1
fi

# Nomor penerima usulan & pemberi persetujuan: THREADS_PEMILIK di ~/.openclaw/.env
# (tidak ditulis di repo).
ENV_FILE="$HOME/.openclaw/.env"
PEMILIK="$(grep -E '^THREADS_PEMILIK=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"'"'"' ')"
if ! [[ "$PEMILIK" =~ ^\+[0-9]{9,15}$ ]]; then
  echo "THREADS_PEMILIK belum diisi dengan benar di $ENV_FILE (mis. THREADS_PEMILIK=+62812xxxxxxx)" >&2
  exit 1
fi
TZ_ID="Asia/Jakarta"

openclaw config set cron.enabled true

if [[ "$BAGIAN" == semua ]]; then
# ==== Akun bisnis (@lantip.ai.id): teknologi (AI, cloud, DevOps) & bisnis, 7x sehari ====
# ---- Usulan konten per gelombang (riset + draf + visual -> WA), 2 opsi per slot ----
# Harus sama dengan antrian.GELOMBANG.
openclaw cron add --name "Threads usulan pagi" --cron "30 6 * * *" --tz "$TZ_ID" \
  --session isolated \
  --message "Jalankan skill konten-threads Mode 1: akun=bisnis, gelombang=pagi, slot=jam08 (utas panjang, posting 08.00 WIB), jam10 (pendek, 10.00 WIB). Kirim 2 opsi per slot ke $PEMILIK." \
  --announce --channel whatsapp --to "$PEMILIK"

openclaw cron add --name "Threads usulan siang" --cron "0 11 * * *" --tz "$TZ_ID" \
  --session isolated \
  --message "Jalankan skill konten-threads Mode 1: akun=bisnis, gelombang=siang, slot=jam12, jam14, jam16 (pendek; posting 12.00, 14.00, 16.00 WIB). Kirim 2 opsi per slot ke $PEMILIK." \
  --announce --channel whatsapp --to "$PEMILIK"

openclaw cron add --name "Threads usulan sore" --cron "0 17 * * *" --tz "$TZ_ID" \
  --session isolated \
  --message "Jalankan skill konten-threads Mode 1: akun=bisnis, gelombang=sore, slot=jam18 (pendek, 18.00 WIB), jam20 (pendek reflektif, 20.00 WIB). Kirim 2 opsi per slot ke $PEMILIK." \
  --announce --channel whatsapp --to "$PEMILIK"

# ---- Posting ke Threads (hanya jika sudah disetujui), tiap 2 jam 08.00–20.00 ----
for JAM in 08 10 12 14 16 18 20; do
  SLOT="jam$JAM"
  openclaw cron add --name "Threads posting $SLOT" --cron "0 $((10#$JAM)) * * *" --tz "$TZ_ID" \
    --session isolated --light-context \
    --message "Jalankan skill konten-threads Mode 3: ~/.openclaw/workspace/skills/konten-threads/scripts/jalankan post_threads --slot $SLOT . Laporkan hasilnya singkat (tautan postingan, atau alasan tidak diposting)." \
    --announce --channel whatsapp --to "$PEMILIK"
done

# ---- Laporan mingguan (Minggu 21.00 WIB, setelah posting malam) ----
openclaw cron add --name "Threads laporan mingguan" --cron "0 21 * * 0" --tz "$TZ_ID" \
  --session isolated \
  --message "Jalankan skill konten-threads Mode 5: laporan mingguan semua akun, satu pesan WA per akun ke $PEMILIK, lalu simpan sarannya." \
  --announce --channel whatsapp --to "$PEMILIK"
fi

# ==== Akun utama (@nasir19noor): teknologi, parenting, kuliner, 3x sehari ====
# Tanpa usulan: 30 menit sebelum jam posting, konten dibuat & langsung disetujui (Mode 6);
# job posting di jam slotnya memposting dan mengirim tautannya ke WA. Harus sama dengan antrian.GELOMBANG.
openclaw cron add --name "Threads buat utama pagi" --cron "30 8 * * *" --tz "$TZ_ID" \
  --session isolated \
  --message "Jalankan skill konten-threads Mode 6: akun=utama, slot=u09 (utas panjang, posting 09.00 WIB). Tanpa usulan ke WA." \
  --announce --channel whatsapp --to "$PEMILIK"

openclaw cron add --name "Threads buat utama siang" --cron "30 11 * * *" --tz "$TZ_ID" \
  --session isolated \
  --message "Jalankan skill konten-threads Mode 6: akun=utama, slot=u12 (pendek, posting 12.00 WIB). Tanpa usulan ke WA." \
  --announce --channel whatsapp --to "$PEMILIK"

openclaw cron add --name "Threads buat utama malam" --cron "30 18 * * *" --tz "$TZ_ID" \
  --session isolated \
  --message "Jalankan skill konten-threads Mode 6: akun=utama, slot=u19 (pendek, posting 19.00 WIB). Tanpa usulan ke WA." \
  --announce --channel whatsapp --to "$PEMILIK"

[[ "$BAGIAN" == utama-buat ]] && { openclaw cron list; exit 0; }

for JAM in 09 12 19; do
  SLOT="u$JAM"
  openclaw cron add --name "Threads posting $SLOT" --cron "0 $((10#$JAM)) * * *" --tz "$TZ_ID" \
    --session isolated --light-context \
    --message "Jalankan skill konten-threads Mode 3: ~/.openclaw/workspace/skills/konten-threads/scripts/jalankan post_threads --slot $SLOT . Laporkan hasilnya singkat (tautan postingan, atau alasan tidak diposting)." \
    --announce --channel whatsapp --to "$PEMILIK"
done

openclaw cron list
echo "Selesai. Uji sekarang: openclaw cron run <id-job-usulan-siang>"
