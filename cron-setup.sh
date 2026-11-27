#!/usr/bin/env bash
# Mendaftarkan cron job konten Threads di OpenClaw (zona waktu WIB). Kedua akun posting otomatis
# tanpa usulan: job "buat" sebelum jam posting membuat & menyimpan konten (Mode 6; 60 menit sebelumnya
# untuk utas panjang, 30 menit untuk pendek), job "posting" di jam slotnya memposting dan mengirim
# tautannya ke WA (Mode 3).
#   akun bisnis (@lantip.ai.id): jam08 … jam20 (tiap 2 jam, satu rubrik per slot) -> 7 buat + 7 posting
#   akun utama (@nasir19noor):   5 slot harian + 7 slot mingguan (satu per hari)  -> 12 buat + 12 posting
#   laporan mingguan Minggu 21.00                                                 -> 1
# Total 39 job (2 per slot + 1). Slot, jam, dan format dibaca dari antrian.py (`antrian.py cron-tabel`), satu sumber
# dengan antrian.JADWAL / RUBRIK / jam_buat.
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

# Slot, jam, dan format dari antrian.py — dibaca SEBELUM reset menghapus apa pun.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TABEL="$(python3 "$DIR/skills/konten-threads/scripts/antrian.py" cron-tabel)"
N_SLOT="$(wc -l <<< "$TABEL")"
if [[ -z "$TABEL" ]] || awk 'NF != 8 { bad = 1 } END { exit !bad }' <<< "$TABEL"; then
  echo "cron-tabel tidak berisi baris 8 kolom yang sah:" >&2
  echo "$TABEL" >&2
  exit 1
fi
N_JOB=$((N_SLOT * 2 + 1))

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

# Per slot: "buat" (Mode 6, rubrik dibaca agen lewat `antrian rubrik`) lalu "posting" (Mode 3).
# Hari "*" = setiap hari; angka = slot mingguan (0 = Minggu … 6 = Sabtu).
while read -r AKUN SLOT MENIT JAM_BUAT MENIT_POST JAM HARI FORMAT; do
  openclaw cron add --name "Threads buat $SLOT" --cron "$MENIT $JAM_BUAT * * $HARI" --tz "$TZ_ID" \
    --session isolated \
    --message "Jalankan skill konten-threads Mode 6: akun=$AKUN, slot=$SLOT ($FORMAT, posting $(printf %02d.%02d "$JAM" "$MENIT_POST") WIB). Baca rubriknya dulu: $SKRIP antrian rubrik --slot $SLOT . Tanpa usulan ke WA." \
    --announce --channel whatsapp --to "$PEMILIK"
  openclaw cron add --name "Threads posting $SLOT" --cron "$MENIT_POST $JAM * * $HARI" --tz "$TZ_ID" \
    --session isolated --light-context \
    --message "Jalankan skill konten-threads Mode 3: $SKRIP post_threads --slot $SLOT . Laporkan hasilnya singkat (tautan postingan, atau alasan tidak diposting)." \
    --announce --channel whatsapp --to "$PEMILIK"
done <<< "$TABEL"

# ---- Laporan mingguan (Minggu 21.00 WIB, setelah posting terakhir) ----
openclaw cron add --name "Threads laporan mingguan" --cron "0 21 * * 0" --tz "$TZ_ID" \
  --session isolated \
  --message "Jalankan skill konten-threads Mode 5: laporan mingguan semua akun, satu pesan WA per akun ke $PEMILIK, lalu simpan sarannya." \
  --announce --channel whatsapp --to "$PEMILIK"

openclaw cron list
echo "Selesai: $N_JOB job Threads. Uji: openclaw cron run <id \"Threads buat jam10\">, lalu jalankan antrian status."
