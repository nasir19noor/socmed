#!/usr/bin/env python3
"""Kelola contoh postingan asli pemilik (acuan gaya).

  jalankan contoh tambah --label "budaya Jawa · pepatah" < teks.txt   (teks dari stdin)
  jalankan contoh daftar                                              (ringkasan semua contoh)
  jalankan contoh hapus --nomor 3                                     (hapus contoh ke-3)
"""
import argparse
import re
import sys
from pathlib import Path

BERKAS = Path(__file__).resolve().parent.parent / "referensi" / "contoh-postingan.md"
PEMISAH = "\n\n---\n\n"
POLA = re.compile(r"\n\s*---\s*\n")


def bagian():
    teks = BERKAS.read_text(encoding="utf-8")
    potong = [b.strip("\n") for b in POLA.split(teks)]
    kepala, potong = potong[0], potong[1:]
    contoh = [b for b in potong if b.startswith("## ")]
    ekor = [b for b in potong if not b.startswith("## ")]
    return kepala, contoh, "\n".join(e for e in ekor if e.strip())


def tulis(kepala, contoh, ekor):
    isi = PEMISAH.join([kepala] + contoh + ([ekor.strip("\n")] if ekor else []))
    BERKAS.write_text(isi + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tambah"); t.add_argument("--label", default="contoh")
    sub.add_parser("daftar")
    h = sub.add_parser("hapus"); h.add_argument("--nomor", type=int, required=True)
    a = ap.parse_args()

    kepala, contoh, ekor = bagian()
    if a.cmd == "tambah":
        teks = sys.stdin.read().strip()
        if not teks:
            sys.exit("Teks contoh kosong.")
        contoh.append(f"## [{a.label}]\n{teks}")
        tulis(kepala, contoh, ekor)
        print(f"Contoh ke-{len(contoh)} tersimpan.")
    elif a.cmd == "daftar":
        for i, c in enumerate(contoh, 1):
            judul, _, isi = c.partition("\n")
            print(f"{i}. {judul[3:]} — {isi.strip()[:70].replace(chr(10), ' ')}…")
    elif a.cmd == "hapus":
        if not 1 <= a.nomor <= len(contoh):
            sys.exit(f"Nomor tidak ada (1–{len(contoh)}).")
        buang = contoh.pop(a.nomor - 1)
        tulis(kepala, contoh, ekor)
        print(f"Dihapus: {buang.splitlines()[0][3:]}")


if __name__ == "__main__":
    main()
