#!/usr/bin/env bash
# Memasang (atau memperbarui) skill konten-threads di OpenClaw.
#   bash pasang.sh
#
# - Menyalin skills/konten-threads ke ~/.openclaw/workspace/skills/konten-threads.
# - Mengisi nomor pemilik (THREADS_PEMILIK di ~/.openclaw/.env) ke SKILL.md.
#   Nomor itu sengaja tidak ditulis di repo.
# - Contoh gaya yang sudah tersimpan di server (referensi/contoh-postingan.md,
#   diisi lewat "contoh: ..." dari WhatsApp) TIDAK ditimpa.
# - Menambahkan aturan pemicu "threads" (AGENTS-tambahan.md) ke AGENTS.md sekali
#   saja; jika sudah ada, bagian itu diperbarui.
# Aman dijalankan ulang setiap kali repo diperbarui.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$HOME/.openclaw/.env"
WORKSPACE="$HOME/.openclaw/workspace"
TUJUAN="$WORKSPACE/skills/konten-threads"
AGENTS="$WORKSPACE/AGENTS.md"
AWAL="<!-- konten-threads: awal -->"
AKHIR="<!-- konten-threads: akhir -->"

PEMILIK="$(grep -E '^THREADS_PEMILIK=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"'"'"' ')"
if ! [[ "$PEMILIK" =~ ^\+[0-9]{9,15}$ ]]; then
  echo "THREADS_PEMILIK belum diisi dengan benar di $ENV_FILE (mis. THREADS_PEMILIK=+62812xxxxxxx)" >&2
  exit 1
fi

# Contoh gaya di server disimpan dulu, lalu dikembalikan setelah disalin.
CONTOH="$TUJUAN/referensi/contoh-postingan.md"
SIMPAN=""
if [ -f "$CONTOH" ]; then
  SIMPAN="$(mktemp)"
  cp "$CONTOH" "$SIMPAN"
fi

mkdir -p "$WORKSPACE/skills"
rm -rf "$TUJUAN"
cp -r "$REPO/skills/konten-threads" "$TUJUAN"
find "$TUJUAN" -name '__pycache__' -type d -prune -exec rm -rf {} +
chmod +x "$TUJUAN/scripts/jalankan"
sed -i "s/{{PEMILIK}}/$PEMILIK/g" "$TUJUAN/SKILL.md"

if [ -n "$SIMPAN" ]; then
  cp "$SIMPAN" "$CONTOH"
  rm -f "$SIMPAN"
  echo "Contoh gaya yang sudah ada dipertahankan."
fi

# Aturan pemicu "threads" di AGENTS.md, di antara dua penanda agar bisa diganti.
touch "$AGENTS"
if ! grep -qF "$AWAL" "$AGENTS" && grep -qF "## Trigger manual konten Threads" "$AGENTS"; then
  echo "[peringatan] AGENTS.md sudah berisi aturan \"threads\" versi lama (ditempel manual)." >&2
  echo "            Hapus bagian \"## Trigger manual konten Threads\" itu sekali, lalu jalankan ulang." >&2
fi
if grep -qF "$AWAL" "$AGENTS"; then
  sed -i "/$AWAL/,/$AKHIR/d" "$AGENTS"
fi
{
  echo ""
  echo "$AWAL"
  sed "s/{{PEMILIK}}/$PEMILIK/g" "$REPO/AGENTS-tambahan.md"
  echo "$AKHIR"
} >> "$AGENTS"

if grep -q "{{PEMILIK}}" "$TUJUAN/SKILL.md" "$AGENTS"; then
  echo "Gagal mengisi nomor pemilik." >&2
  exit 1
fi
echo "Skill terpasang di $TUJUAN (pemilik: ${PEMILIK:0:6}…)."
echo "Jika baru pertama kali: lanjutkan ke langkah berikutnya di README.md."
