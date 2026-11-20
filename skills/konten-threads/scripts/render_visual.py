#!/usr/bin/env python3
"""Render visual konten Threads (PNG 1080x1350) dari template HTML.

Contoh:
  python3 render_visual.py --kategori parenting \
      --judul "Screen time bukan musuh, *tanpa aturan* yang musuh" \
      --isi "3 kesepakatan sederhana yang bikin rumah lebih tenang." \
      --label "Parenting · Tips" --out /tmp/contoh.png

Tanda *...* pada judul akan diberi warna aksen.
Gaya: --poin "a|b|c" untuk daftar; --gaya kutipan untuk kutipan besar (--isi = sumber/penulis).
Butuh: pip install playwright && python3 -m playwright install chromium
(atau Google Chrome/Chromium terpasang sebagai cadangan).
"""
import argparse
import datetime as dt
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DIR = Path(__file__).resolve().parent.parent
TEMPLATE = DIR / "templates" / "visual.html"

PALET = {
    #            aksen      aksen muda  dasar
    "teknologi": ("#2457d6", "#d9e4ff", "#f3f6ff"),
    "buku":      ("#b86b00", "#ffe3b3", "#fff8ec"),
    "parenting": ("#1f8a5b", "#cdeedd", "#f1fbf5"),
    "lokal":     ("#b23a2a", "#f8d5cc", "#fff5f1"),
    "umum":      ("#6a3fd1", "#e3d9ff", "#f7f4ff"),
}
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]


def tanggal_id(d: dt.date) -> str:
    return f"{d.day} {BULAN[d.month - 1]} {d.year}"


def judul_html(teks: str) -> str:
    aman = html.escape(teks)
    return re.sub(r"\*(.+?)\*", r"<em>\1</em>", aman)


def ukuran_judul(teks: str, ada_poin: bool) -> int:
    n = len(teks.replace("*", ""))
    if ada_poin:
        return 76 if n <= 40 else 64
    if n <= 28:
        return 112
    if n <= 45:
        return 96
    if n <= 65:
        return 82
    return 70


def bangun_html(a) -> str:
    aksen, muda, dasar = PALET[a.kategori]
    poin = [p.strip() for p in (a.poin or "").split("|") if p.strip()][:4]
    if poin:
        konten = "<ol>" + "".join(f"<li>{html.escape(p)}</li>" for p in poin) + "</ol>"
    elif a.isi:
        konten = f'<p class="isi">{html.escape(a.isi)}</p>'
    else:
        konten = ""
    isi = TEMPLATE.read_text(encoding="utf-8")
    ganti = {
        "{{AKSEN}}": aksen, "{{AKSEN_MUDA}}": muda, "{{DASAR}}": dasar,
        "{{LABEL}}": html.escape(a.label or a.kategori.upper()),
        "{{JUDUL}}": judul_html(a.judul),
        "{{UKURAN_JUDUL}}": str(ukuran_judul(a.judul, bool(poin))),
        "{{KONTEN}}": konten,
        "{{GAYA}}": a.gaya,
        "{{AKUN}}": html.escape(a.akun or os.environ.get("THREADS_HANDLE", "")),
        "{{TANGGAL}}": tanggal_id(dt.date.today()),
    }
    for k, v in ganti.items():
        isi = isi.replace(k, v)
    return isi


def render_playwright(html_path: Path, out: Path) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1080, "height": 1350})
            pg.goto(html_path.as_uri())
            try:
                pg.wait_for_load_state("networkidle", timeout=6000)
            except Exception:
                pass  # font online gagal dimuat -> pakai font cadangan
            pg.screenshot(path=str(out), full_page=False)
            b.close()
        return True
    except Exception as e:  # browser playwright belum terpasang, dll.
        print(f"[peringatan] playwright gagal: {e}", file=sys.stderr)
        return False


def render_chrome(html_path: Path, out: Path) -> bool:
    for nama in ("google-chrome", "chromium", "chromium-browser", "chrome",
                 "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
        exe = shutil.which(nama) or (nama if Path(nama).exists() else None)
        if not exe:
            continue
        cmd = [exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-sandbox",
               "--virtual-time-budget=5000", "--window-size=1080,1350",
               f"--screenshot={out}", html_path.as_uri()]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if r.returncode == 0 and out.exists():
            return True
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kategori", choices=PALET.keys(), default="umum")
    ap.add_argument("--judul", required=True)
    ap.add_argument("--isi", default="")
    ap.add_argument("--poin", default="", help="Poin dipisah '|', maks 4")
    ap.add_argument("--gaya", choices=["kartu", "kutipan"], default="kartu",
                    help="kartu = judul + kalimat/poin; kutipan = kutipan besar, --isi = nama sumber")
    ap.add_argument("--label", default="")
    ap.add_argument("--akun", default="", help="Handle Threads di kaki gambar, mis. @namaakun")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    out = Path(os.path.expanduser(a.out)).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        hp = Path(tmp) / "visual.html"
        hp.write_text(bangun_html(a), encoding="utf-8")
        if not (render_playwright(hp, out) or render_chrome(hp, out)):
            sys.exit("Gagal render. Pasang: pip install playwright && python3 -m playwright install chromium")
    print(out)


if __name__ == "__main__":
    main()
