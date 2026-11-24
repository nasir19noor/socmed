#!/usr/bin/env bash
# Mendaftarkan cron job konten Threads di OpenClaw (zona waktu WIB). Kedua akun posting otomatis
# tanpa usulan: job "buat" 30 menit sebelum jam posting membuat & menyimpan konten (Mode 6), job
# "posting" di jam slotnya memposting dan mengirim tautannya ke WA (Mode 3).
#   akun bisnis (@lantip.ai.id): jam08 … jam20 (tiap 2 jam)  -> 7 buat + 7 posting
#   akun utama (@nasir19noor):   u09, u12, u19                 -> 3 buat + 3 posting
#   laporan mingguan Minggu 21.00                              -> 1
# Total 21 job. Jadwal harus sama dengan antrian.JADWAL / antrian.jam_buat.
#
#   bash cron-setup.sh          daftarkan (jangan diulang: job akan dobel)
#   bash cron-setup.sh reset    hapus SEMUA job yang namanya diawali "Threads ", lalu daftarkan ulang
#                               (job bawaan OpenClaw seperti Heartbeat tidak disentuh)
set -euo pipefail
BAGIAN="${1:-}"
if [[ -n "$BAGIAN" && "$BAGIAN" != reset ]]; then
  echo "Pemakaian: bash cron-setup.sh [reset]" >&2
  exit 1
fi

# Nomor penerima laporan & pemberi perintah: THREADS_PEMILIK di ~/.openclaw/.env
# (tidak ditulis di repo).
ENV_FILE="$HOME/.openclaw/.env"
PEMILIK="$(grep -E '^THREADS_PEMILIK=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"'"'"' ')"
if ! [[ "$PEMILIK" =~ ^\+[0-9]{9,15}$ ]]; then
  echo "THREADS_PEMILIK belum diisi dengan benar di $ENV_FILE (mis. THREADS_PEMILIK=+62812xxxxxxx)" >&2
  exit 1
fi
TZ_ID="Asia/Jakarta"
SKRIP="~/.openclaw/workspace/skills/konten-threads/scripts/jalankan"

# ID semua job yang namanya diawali "Threads ". Format JSON `cron list` tidak didokumentasikan, jadi
# diterima larik langsung atau objek berisi larik (jobs/items/data/automations); teks lain sebelum
# JSON (spanduk CLI) dilewati. Format tak dikenal -> berhenti, agar tidak ada job dobel.
id_job_threads() {
  openclaw cron list --all --json | python3 -c '
import json, sys
teks = sys.stdin.read()
awal = min([i for i in (teks.find("["), teks.find("{")) if i >= 0], default=-1)
if awal < 0:
    sys.exit("cron list --json tidak berisi JSON")
d, _ = json.JSONDecoder().raw_decode(teks[awal:])
if isinstance(d, dict):
    d = next((d[k] for k in ("jobs", "items", "data", "automations") if isinstance(d.get(k), list)), None)
if not isinstance(d, list):
    sys.exit("format JSON cron list tidak dikenal")
for j in d:
    nama = str(j.get("name") or j.get("displayName") or "")
    jid = j.get("id") or j.get("jobId")
    if jid and nama.startswith("Threads "):
        print(jid)
'
}

if [[ "$BAGIAN" == reset ]]; then
  IDS="$(id_job_threads)"
  N=0
  for ID in $IDS; do
    openclaw cron remove "$ID"
    N=$((N + 1))
  done
  echo "Dihapus: $N job Threads."
  SISA="$(id_job_threads)"
  if [[ -n "$SISA" ]]; then
    echo "Masih ada job Threads yang belum terhapus:" >&2
    echo "$SISA" >&2
    exit 1
  fi
fi

openclaw config set cron.enabled true

# $1 akun, $2 slot, $3 jam posting (HH), $4 format
daftar_slot() {
  local akun="$1" slot="$2" jam=$((10#$3)) format="$4"
  openclaw cron add --name "Threads buat $slot" --cron "30 $((jam - 1)) * * *" --tz "$TZ_ID" \
    --session isolated \
    --message "Jalankan skill konten-threads Mode 6: akun=$akun, slot=$slot ($format, posting $3.00 WIB). Tanpa usulan ke WA." \
    --announce --channel whatsapp --to "$PEMILIK"
  openclaw cron add --name "Threads posting $slot" --cron "0 $jam * * *" --tz "$TZ_ID" \
    --session isolated --light-context \
    --message "Jalankan skill konten-threads Mode 3: $SKRIP post_threads --slot $slot . Laporkan hasilnya singkat (tautan postingan, atau alasan tidak diposting)." \
    --announce --channel whatsapp --to "$PEMILIK"
}

# ==== Akun bisnis (@lantip.ai.id): teknologi (AI, cloud, DevOps) & bisnis, 7x sehari ====
for JAM in 08 10 12 14 16 18 20; do
  case "$JAM" in
    08) FORMAT="utas panjang" ;;
    20) FORMAT="pendek, santai/reflektif" ;;
    *)  FORMAT="pendek" ;;
  esac
  daftar_slot bisnis "jam$JAM" "$JAM" "$FORMAT"
done

# ==== Akun utama (@nasir19noor): teknologi, parenting, kuliner, 3x sehari ====
daftar_slot utama u09 09 "utas panjang"
daftar_slot utama u12 12 "pendek"
daftar_slot utama u19 19 "pendek, santai/reflektif"

# ---- Laporan mingguan (Minggu 21.00 WIB, setelah posting terakhir) ----
openclaw cron add --name "Threads laporan mingguan" --cron "0 21 * * 0" --tz "$TZ_ID" \
  --session isolated \
  --message "Jalankan skill konten-threads Mode 5: laporan mingguan semua akun, satu pesan WA per akun ke $PEMILIK, lalu simpan sarannya." \
  --announce --channel whatsapp --to "$PEMILIK"

openclaw cron list
echo "Selesai: 21 job Threads. Uji: openclaw cron run <id \"Threads buat jam10\">, lalu jalankan antrian status."
