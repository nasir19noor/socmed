#!/usr/bin/env python3
"""Ingatan gaya visual, agar gambar berturut-turut tidak seragam.

  jalankan ragam                 gaya yang dipakai belakangan (tata letak, font, palet, arah desain bebas)
  jalankan ragam --saran         3 arah desain bebas yang paling lama tidak dipakai
  jalankan ragam --catat-arah "koran"   catat arah desain bebas yang dipakai (render_html melakukannya sendiri)

render_visual.py memilih tata letak, font, dan palet yang paling lama tidak dipakai dan mencatatnya
di sini; render_html.py mencatat arah desain bebas (--arah). Berkas: ragam.json di samping folder
antrian ($KONTEN_DATA_DIR/../ragam.json).
"""
import argparse
import datetime as dt
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import antrian  # noqa: E402

BERKAS = antrian.DATA.parent / "ragam.json"
SIMPAN_MAKS = 80

# Arah seni untuk desain bebas (referensi/desain-bebas.md menjelaskan masing-masing).
ARAH = [
    "editorial majalah", "poster swiss", "risograph", "koran", "neon teknologi",
    "batik banyumasan", "infografis", "catatan tangan", "kolase kertas", "minimalis jepang",
    "retro 70-an", "cetak saring (screen print)", "peta & denah", "papan tulis",
]


def muat() -> list:
    try:
        return json.loads(BERKAS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def catat(jenis: str, nilai: str) -> None:
    data = muat()
    data.append({"waktu": dt.datetime.now(antrian.WIB).isoformat(timespec="seconds"), "jenis": jenis, "nilai": nilai})
    try:
        BERKAS.parent.mkdir(parents=True, exist_ok=True)
        BERKAS.write_text(json.dumps(data[-SIMPAN_MAKS:], ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError as e:  # ingatan gaya tidak boleh menggagalkan render
        print(f"[peringatan] ragam tidak tercatat: {e}", file=sys.stderr)


def pilih(jenis: str, calon: list, acak: random.Random) -> str:
    """Calon yang paling lama tidak dipakai (belum pernah = paling lama); seri diacak."""
    data = muat()
    terakhir = {}
    for i, d in enumerate(data):
        if d.get("jenis") == jenis:
            terakhir[d.get("nilai")] = i
    paling_lama = min(terakhir.get(c, -1) for c in calon)
    return acak.choice([c for c in calon if terakhir.get(c, -1) == paling_lama])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--saran", action="store_true")
    ap.add_argument("--catat-arah", default="")
    ap.add_argument("--jumlah", type=int, default=15)
    a = ap.parse_args()
    if a.catat_arah:
        catat("arah", a.catat_arah.strip().lower())
        print(f"Tercatat: {a.catat_arah}")
    elif a.saran:
        acak, sisa, saran = random.Random(), list(ARAH), []
        for _ in range(3):
            pilihan = pilih("arah", sisa, acak)
            saran.append(pilihan)
            sisa.remove(pilihan)
        print("Arah desain bebas yang paling lama tidak dipakai: " + ", ".join(saran))
    else:
        data = muat()[-a.jumlah:]
        if not data:
            print("Belum ada gaya tercatat.")
        for d in data:
            print(f"{d['waktu'][:16]}  {d['jenis']:<7} {d['nilai']}")


if __name__ == "__main__":
    main()
