#!/usr/bin/env python3
"""Render visual konten Threads (PNG 1080x1350) dari template HTML.

Contoh:
  python3 render_visual.py --kategori parenting \
      --judul "Screen time bukan musuh, *tanpa aturan* yang musuh" \
      --isi "3 kesepakatan sederhana yang bikin rumah lebih tenang." \
      --label "Parenting · Tips" --out /tmp/contoh.png

Tanda *...* pada judul akan diberi warna aksen.
Watermark (handle di kaki gambar) wajib sesuai akun yang memposting: --slot jam14 (akun dari slot),
atau --akun bisnis / --akun utama (slot manual), atau --akun @handle.
Gaya: --poin "a|b|c" untuk daftar; --gaya kutipan untuk kutipan besar (--isi = sumber/penulis);
--angka "73%" untuk angka besar di atas judul.

Agar tidak seragam, tata letak, pasangan font, dan varian palet dipilih otomatis: yang paling
lama tidak dipakai (dicatat di ragam.json, lihat ragam.py). Bisa dipaksa dengan --tata-letak,
--font, --palet. Tata letak: kartu, poster, split, catatan, gelap, bingkai, majalah.
Butuh: pip install playwright && python3 -m playwright install chromium
(atau Google Chrome/Chromium/Edge terpasang sebagai cadangan).
"""
import argparse
import datetime as dt
import html
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ragam  # noqa: E402

DIR = Path(__file__).resolve().parent.parent
TEMPLATE = DIR / "templates" / "visual.html"

# Tiap kategori punya beberapa varian; kategori hanya mengarahkan suasana, bukan mengunci satu warna.
PALET = {
    #             aksen      aksen muda  dasar      tinta (gelap)
    "teknologi": [("#2457d6", "#d9e4ff", "#f3f6ff", "#0b1a3d"),
                  ("#0f9d8a", "#c9f2ea", "#f0fbf8", "#062b26"),
                  ("#7b2ff7", "#e6d9ff", "#f8f4ff", "#1a0b36")],
    "buku":      [("#b86b00", "#ffe3b3", "#fff8ec", "#3a2100"),
                  ("#8c2f39", "#f3d3d6", "#fbf3f1", "#2c0d11"),
                  ("#2f5d50", "#d3e6df", "#f5f1e8", "#0e2420")],
    "parenting": [("#1f8a5b", "#cdeedd", "#f1fbf5", "#0a2e1f"),
                  ("#e0672b", "#ffd9c2", "#fff6ef", "#3a1a08"),
                  ("#3a7bd5", "#d6e6fb", "#f4f8fe", "#0d2340")],
    "kuliner":   [("#c2410c", "#fed7aa", "#fff7ed", "#3b1305"),
                  ("#a16207", "#fde68a", "#fefce8", "#2f1d02"),
                  ("#9f1239", "#fecdd3", "#fff1f2", "#33060f")],
    "bisnis":    [("#1e3a8a", "#dbe4f7", "#f5f7fb", "#0a1430"),
                  ("#065f46", "#d1fae5", "#f3fbf7", "#04241b"),
                  ("#334155", "#e2e8f0", "#f8fafc", "#0f172a")],
    "lokal":    [("#b23a2a", "#f8d5cc", "#fff5f1", "#3a0f09"),
                  ("#6b4226", "#ead7c3", "#faf4ec", "#24150b"),
                  ("#1d6f72", "#cfe9e9", "#f2f8f7", "#082627")],
    "umum":      [("#6a3fd1", "#e3d9ff", "#f7f4ff", "#1e0f45"),
                  ("#d6336c", "#ffd6e4", "#fff4f8", "#3d0a1d"),
                  ("#3d3d3d", "#e6e6e6", "#f6f5f1", "#111111")],
}
# nama: (font judul, bobot judul, font teks, skala ukuran judul, parameter Google Fonts)
FONT = {
    "fraunces":   ("'Fraunces'", 600, "'Plus Jakarta Sans'", 1.0,
                   "Fraunces:opsz,wght@9..144,600&family=Plus+Jakarta+Sans:wght@500;600;700;800"),
    "dmserif":    ("'DM Serif Display'", 400, "'Inter'", 1.04,
                   "DM+Serif+Display:ital@0;1&family=Inter:wght@500;600;700"),
    "grotesk":    ("'Space Grotesk'", 700, "'Space Grotesk'", 0.95,
                   "Space+Grotesk:wght@500;600;700"),
    "playfair":   ("'Playfair Display'", 800, "'Manrope'", 0.96,
                   "Playfair+Display:ital,wght@0,800;1,800&family=Manrope:wght@500;600;700"),
    "bricolage":  ("'Bricolage Grotesque'", 800, "'Inter'", 0.94,
                   "Bricolage+Grotesque:opsz,wght@12..96,800&family=Inter:wght@500;600;700"),
    "instrument": ("'Instrument Serif'", 400, "'DM Sans'", 1.15,
                   "Instrument+Serif:ital@0;1&family=DM+Sans:wght@500;600;700"),
    "archivo":    ("'Archivo Black'", 400, "'Archivo'", 0.86,
                   "Archivo+Black&family=Archivo:wght@500;600;700"),
}
# nama: (skala ukuran judul, font tambahan)
TATA = {
    "kartu":   (1.0, ""),
    "poster":  (1.12, ""),
    "split":   (0.92, ""),
    "catatan": (0.9, "Caveat:wght@600"),
    "gelap":   (1.0, "JetBrains+Mono:wght@500"),
    "bingkai": (0.88, ""),
    "majalah": (1.05, ""),
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
        return 84 if n <= 40 else 70
    if n <= 28:
        return 112
    if n <= 45:
        return 96
    if n <= 65:
        return 82
    return 70


def pilih_gaya(a) -> None:
    """Isi a.tata_letak / a.font / a.palet yang 'auto' dengan yang paling lama tidak dipakai, lalu catat."""
    acak = random.Random()
    if a.tata_letak == "auto":
        a.tata_letak = ragam.pilih("tata", list(TATA), acak)
    if a.font == "auto":
        a.font = ragam.pilih("font", list(FONT), acak)
    varian = [f"{a.kategori}-{i + 1}" for i in range(len(PALET[a.kategori]))]
    if a.palet == "auto":
        a.palet = int(ragam.pilih("palet", varian, acak).rsplit("-", 1)[1])
    a.palet = min(max(a.palet, 1), len(varian))
    ragam.catat("tata", a.tata_letak)
    ragam.catat("font", a.font)
    ragam.catat("palet", f"{a.kategori}-{a.palet}")


def bangun_html(a) -> str:
    aksen, muda, dasar, tinta = PALET[a.kategori][a.palet - 1]
    f_judul, bobot, f_teks, skala_font, url_font = FONT[a.font]
    skala_tata, font_tambahan = TATA[a.tata_letak]
    url = "https://fonts.googleapis.com/css2?family=" + url_font
    if font_tambahan:
        url += "&family=" + font_tambahan
    url += "&display=swap"
    poin = [p.strip() for p in (a.poin or "").split("|") if p.strip()][:4]
    if poin:
        konten = "<ol>" + "".join(f"<li>{html.escape(p)}</li>" for p in poin) + "</ol>"
    elif a.isi:
        konten = f'<p class="isi">{html.escape(a.isi)}</p>'
    else:
        konten = ""
    ukuran = ukuran_judul(a.judul, bool(poin)) * skala_font * skala_tata
    if a.angka:
        ukuran *= 0.82
    isi = TEMPLATE.read_text(encoding="utf-8")
    ganti = {
        "{{FONT_URL}}": html.escape(url),
        "{{AKSEN}}": aksen, "{{AKSEN_MUDA}}": muda, "{{DASAR}}": dasar, "{{TINTA}}": tinta,
        "{{FONT_JUDUL}}": f_judul, "{{BOBOT_JUDUL}}": str(bobot), "{{FONT_TEKS}}": f_teks,
        "{{TATA}}": a.tata_letak,
        "{{LABEL}}": html.escape(a.label or a.kategori.upper()),
        "{{ANGKA}}": f'<div class="angka">{html.escape(a.angka)}</div>' if a.angka else "",
        "{{JUDUL}}": judul_html(a.judul),
        "{{UKURAN_JUDUL}}": str(round(ukuran)),
        "{{KONTEN}}": konten,
        "{{GAYA}}": a.gaya,
        "{{AKUN}}": html.escape(a.handle),
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
    for nama in ("google-chrome", "chromium", "chromium-browser", "chrome", "msedge",
                 "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                 r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                 r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"):
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
    ap.add_argument("--angka", default="", help="Angka/statistik besar di atas judul, mis. '73%%'")
    ap.add_argument("--gaya", choices=["kartu", "kutipan"], default="kartu",
                    help="kartu = judul + kalimat/poin; kutipan = kutipan besar, --isi = nama sumber")
    ap.add_argument("--tata-letak", choices=["auto", *TATA], default="auto")
    ap.add_argument("--font", choices=["auto", *FONT], default="auto")
    ap.add_argument("--palet", default="auto", help="auto atau nomor varian palet kategori (1-3)")
    ap.add_argument("--label", default="")
    ap.add_argument("--akun", default="", help="Akun yang memposting (utama/bisnis) atau @handle, untuk watermark")
    ap.add_argument("--slot", default="", help="Slot tujuan; watermark memakai akun pemilik slot (jam… = bisnis, u… = utama)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.palet != "auto":
        if not a.palet.isdigit():
            ap.error("--palet harus auto atau angka")
        a.palet = int(a.palet)
    a.handle = ragam.antrian.handle_watermark(a.akun, a.slot)
    pilih_gaya(a)

    out = Path(os.path.expanduser(a.out)).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        hp = Path(tmp) / "visual.html"
        hp.write_text(bangun_html(a), encoding="utf-8")
        if not (render_playwright(hp, out) or render_chrome(hp, out)):
            sys.exit("Gagal render. Pasang: pip install playwright && python3 -m playwright install chromium")
    ragam.antrian.berkas_watermark(out).write_text(a.handle, encoding="utf-8")
    print(out)
    print(f"watermark: {a.handle}", file=sys.stderr)
    print(f"gaya: tata letak {a.tata_letak}, font {a.font}, palet {a.kategori}-{a.palet}", file=sys.stderr)


if __name__ == "__main__":
    main()
