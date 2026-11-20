#!/usr/bin/env bash
# Mendaftarkan 6 cron job konten Threads di OpenClaw (zona waktu WIB).
# Jalankan sekali: bash cron-setup.sh
set -euo pipefail

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

# ---- Usulan konten (riset + draf + visual -> WA) ----
openclaw cron add --name "Threads usulan pagi" --cron "30 6 * * *" --tz "$TZ_ID" \
  --session isolated \
  --message "Jalankan skill konten-threads Mode 1: slot=pagi (utas panjang, posting 08.00 WIB). Kirim 3 opsi ke $PEMILIK." \
  --announce --channel whatsapp --to "$PEMILIK"

openclaw cron add --name "Threads usulan siang" --cron "15 12 * * *" --tz "$TZ_ID" \
  --session isolated \
  --message "Jalankan skill konten-threads Mode 1: slot=siang (postingan pendek, posting 13.00 WIB). Kirim 3 opsi ke $PEMILIK." \
  --announce --channel whatsapp --to "$PEMILIK"

openclaw cron add --name "Threads usulan malam" --cron "15 19 * * *" --tz "$TZ_ID" \
  --session isolated \
  --message "Jalankan skill konten-threads Mode 1: slot=malam (postingan pendek reflektif, posting 20.00 WIB). Kirim 3 opsi ke $PEMILIK." \
  --announce --channel whatsapp --to "$PEMILIK"

# ---- Posting ke Threads (hanya jika sudah disetujui) ----
for s in "pagi:0 8" "siang:0 13" "malam:0 20"; do
  SLOT="${s%%:*}"; JAM="${s#*:}"
  openclaw cron add --name "Threads posting $SLOT" --cron "$JAM * * *" --tz "$TZ_ID" \
    --session isolated --light-context \
    --message "Jalankan skill konten-threads Mode 3: ~/.openclaw/workspace/skills/konten-threads/scripts/jalankan post_threads --slot $SLOT . Laporkan hasilnya singkat (tautan postingan, atau alasan tidak diposting)." \
    --announce --channel whatsapp --to "$PEMILIK"
done

openclaw cron list
echo "Selesai. Uji sekarang: openclaw cron run <id-job-usulan-siang>"
