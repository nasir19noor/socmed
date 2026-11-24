#!/usr/bin/env python3
"""Render desain HTML/SVG bebas (ditulis agen) menjadi PNG 1080x1350.

  jalankan render_html --html /path/desain.html --out /path/hasil.png --arah "koran"

Desain harus satu file HTML mandiri (CSS & SVG di dalam file). Lihat referensi/desain-bebas.md.
Skrip menolak desain yang memuat gambar/skrip dari luar (kecuali Google Fonts) dan memperingatkan
jika isi halaman melebihi kanvas 1080x1350. --arah mencatat arah seni yang dipakai (ragam.py),
agar desain berikutnya memilih arah lain. --slot atau --akun wajib: desain harus memuat handle akun yang
memposting (watermark) dan tidak boleh memuat handle akun lain.
"""
import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ragam  # noqa: E402
from render_visual import render_chrome  # noqa: E402

LEBAR, TINGGI = 1080, 1350
DIIZINKAN = ("https://fonts.googleapis.com", "https://fonts.gstatic.com")


def periksa(html: str) -> list:
    masalah = []
    for url in re.findall(r"""(?:src|href)\s*=\s*["'](https?://[^"']+)""", html, re.I):
        if not url.startswith(DIIZINKAN):
            masalah.append(f"sumber luar tidak diizinkan: {url}")
    for url in re.findall(r"""url\(\s*["']?(https?://[^"')]+)""", html, re.I):
        if not url.startswith(DIIZINKAN):
            masalah.append(f"url() luar tidak diizinkan: {url}")
    if re.search(r"<script[^>]+src=", html, re.I):
        masalah.append("<script src=...> tidak diizinkan")
    return masalah


def render_playwright(html_path: Path, out: Path) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": LEBAR, "height": TINGGI})
            pg.goto(html_path.as_uri())
            try:
                pg.wait_for_load_state("networkidle", timeout=6000)
            except Exception:
                pass
            pg.evaluate("document.fonts && document.fonts.ready")
            w, h = pg.evaluate("[document.documentElement.scrollWidth, document.documentElement.scrollHeight]")
            if w > LEBAR + 2 or h > TINGGI + 2:
                print(f"[peringatan] isi melebihi kanvas ({w}x{h}); bagian luar akan terpotong. "
                      "Perkecil teks/elemen.", file=sys.stderr)
            pg.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": LEBAR, "height": TINGGI})
            b.close()
        return True
    except Exception as e:
        print(f"[peringatan] playwright gagal: {e}", file=sys.stderr)
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--html", required=True, help="File HTML desain")
    ap.add_argument("--out", required=True, help="File PNG keluaran")
    ap.add_argument("--arah", default="", help="Arah seni desain ini, mis. 'koran' (lihat: jalankan ragam --saran)")
    ap.add_argument("--akun", default="", help="Akun yang memposting (utama/bisnis) atau @handle")
    ap.add_argument("--slot", default="", help="Slot tujuan; akun diambil dari pemilik slot")
    a = ap.parse_args()
    antrian = ragam.antrian
    handle = antrian.handle_watermark(a.akun, a.slot)

    src = Path(os.path.expanduser(a.html)).resolve()
    html = src.read_text(encoding="utf-8")
    masalah = periksa(html)
    if handle.lower() not in html.lower():
        masalah.append(f"watermark {handle} tidak ada di desain (tampilkan handle akun yang memposting)")
    for akun in antrian.HANDLE_BAWAAN:
        lain = antrian.handle_akun(akun)
        if lain.lower() != handle.lower() and re.search(re.escape(lain) + r"(?![\w.])", html, re.I):
            masalah.append(f"desain memuat handle akun lain ({lain}); posting ini untuk {handle}")
    if masalah:
        sys.exit("DESAIN DITOLAK:\n- " + "\n- ".join(masalah))
    # kunci ukuran kanvas
    kunci = (f"<style>html,body{{width:{LEBAR}px;height:{TINGGI}px;margin:0;overflow:hidden}}</style>")
    html = re.sub(r"</head>", kunci + "</head>", html, count=1, flags=re.I) if re.search(r"</head>", html, re.I) else kunci + html

    out = Path(os.path.expanduser(a.out)).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        hp = Path(tmp) / "desain.html"
        hp.write_text(html, encoding="utf-8")
        if not (render_playwright(hp, out) or render_chrome(hp, out)):
            sys.exit("Gagal render. Pasang playwright di venv: pip install playwright && python -m playwright install chromium")
    if a.arah:
        ragam.catat("arah", a.arah.strip().lower())
    antrian.berkas_watermark(out).write_text(handle, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
