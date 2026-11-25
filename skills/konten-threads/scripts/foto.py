#!/usr/bin/env python3
"""Cari dan unduh foto asli berlisensi bebas (Wikimedia Commons, Openverse) untuk visual.

  jalankan foto cari "mendoan"                  # kandidat + lisensi, dari Commons lalu Openverse
  jalankan foto cari "Nadiem Makarim" --jumlah 3
  jalankan foto ambil commons:File:Mendoan.jpg  # unduh; cetak path, URI file://, dan teks kredit
  jalankan foto ambil openverse:<id>

Lisensi diperiksa skrip dari API sumbernya (bukan dari agen): hanya CC0, domain publik, CC BY, dan CC BY-SA.
NC (non-komersial) dan ND (tanpa turunan) ditolak, karena gambar akan diberi teks dan dipakai akun bisnis.
`ambil` menyimpan foto di <folder gambar>/foto/ beserta <foto>.sumber.json (halaman, penulis, lisensi, kredit).
render_html hanya menerima foto lokal dari folder itu, dan teks kreditnya harus tampil di desain.
"""
import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

GAMBAR = Path(os.path.expanduser(os.environ.get(
    "KONTEN_GAMBAR_DIR", "~/.openclaw/workspace/konten-threads/gambar")))
FOTO = GAMBAR / "foto"
UA = "konten-threads/1.13 (OpenClaw skill; foto berlisensi bebas)"
COMMONS = "https://commons.wikimedia.org/w/api.php"
OPENVERSE = "https://api.openverse.org/v1/images/"
MAKS_BYTE = 20 * 1024 * 1024
JENIS = {b"\xff\xd8\xff": ".jpg", b"\x89PNG": ".png", b"RIFF": ".webp"}


def ambil_url(url: str, maks: int = 2 * 1024 * 1024) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for coba in (1, 2):  # API sumber kadang 5xx sesaat
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read(maks + 1)
            break
        except urllib.error.HTTPError as e:
            if coba == 2 or e.code < 500:
                raise RuntimeError(f"HTTP {e.code} dari {urllib.parse.urlparse(url).netloc}") from None
    if len(data) > maks:
        raise RuntimeError(f"berkas terlalu besar (> {maks // 1024 // 1024} MB): {url}")
    return data


def json_url(url: str, **q) -> dict:
    return json.loads(ambil_url(url + ("?" + urllib.parse.urlencode(q) if q else "")))


def teks_polos(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", str(s or "")))).strip()


def lisensi_bebas(nama: str) -> bool:
    n = (nama or "").lower().replace("-", " ")
    if re.search(r"\b(nc|nd)\b|non ?commercial|no ?deriv", n):
        return False
    return bool(re.match(r"(cc0|cc ?zero|public domain|pd\b|cc by( sa)?\b|by( sa)?\b)", n))


def kredit(penulis: str, sumber: str, lisensi: str) -> str:
    penulis = (penulis or "").strip()
    if len(penulis) > 40:
        penulis = penulis[:38].rstrip() + "…"
    return f"Foto: {penulis + ' / ' if penulis else ''}{sumber}, {lisensi}"


# ---- Wikimedia Commons ----------------------------------------------------------------------

def info_commons(page: dict) -> dict:
    ii = (page.get("imageinfo") or [{}])[0]
    meta = {k: teks_polos(v.get("value", "")) for k, v in (ii.get("extmetadata") or {}).items()}
    lis = meta.get("LicenseShortName", "")
    return {"id": "commons:" + page["title"], "judul": re.sub(r"^File:", "", page["title"]),
            "deskripsi": meta.get("ImageDescription", "")[:160], "penulis": meta.get("Artist", ""),
            "lisensi": lis, "lisensi_url": meta.get("LicenseUrl", ""), "halaman": ii.get("descriptionurl", ""),
            "unduh": ii.get("thumburl") or ii.get("url", ""), "ukuran": f"{ii.get('width')}x{ii.get('height')}",
            "sumber": "Wikimedia Commons", "boleh": lisensi_bebas(lis)}


def query_commons(**q) -> list:
    d = json_url(COMMONS, action="query", format="json", prop="imageinfo",
                 iiprop="url|size|mime|extmetadata", iiurlwidth=1600, **q)
    return [info_commons(p) for p in (d.get("query", {}).get("pages") or {}).values() if "imageinfo" in p]


def cari_commons(kata: str, n: int) -> list:
    return query_commons(generator="search", gsrnamespace=6, gsrlimit=n * 3,
                         gsrsearch=f"{kata} filetype:bitmap")


# ---- Openverse ------------------------------------------------------------------------------

def info_openverse(r: dict) -> dict:
    lis = f"CC {r.get('license', '').upper()} {r.get('license_version') or ''}".strip()
    if r.get("license") in ("cc0", "pdm"):
        lis = "CC0" if r["license"] == "cc0" else "Public domain"
    return {"id": "openverse:" + r["id"], "judul": r.get("title") or "", "deskripsi": "",
            "penulis": r.get("creator") or "", "lisensi": lis, "lisensi_url": r.get("license_url") or "",
            "halaman": r.get("foreign_landing_url") or "", "unduh": r.get("url") or "",
            "ukuran": f"{r.get('width')}x{r.get('height')}",
            "sumber": (r.get("source") or "Openverse").replace("_", " ").title() + " via Openverse",
            "boleh": lisensi_bebas(lis)}


def cari_openverse(kata: str, n: int) -> list:
    d = json_url(OPENVERSE, q=kata, license_type="commercial,modification", page_size=n * 2)
    return [info_openverse(r) for r in d.get("results", [])]


# ---- perintah -------------------------------------------------------------------------------

def cmd_cari(a):
    hasil = []
    for nama, fn in (("Commons", cari_commons), ("Openverse", cari_openverse)):
        try:
            hasil += [h for h in fn(a.kata, a.jumlah) if h["boleh"] and h["unduh"]][:a.jumlah]
        except Exception as e:
            print(f"[peringatan] {nama} gagal: {e}", file=sys.stderr)
    if not hasil:
        sys.exit(f"Tidak ada foto berlisensi bebas untuk '{a.kata}'. Pakai visual tanpa foto.")
    for i, h in enumerate(hasil, 1):
        print(f"{i}. {h['id']}\n   {h['judul']} ({h['ukuran']}) — {h['penulis'] or 'penulis tidak disebut'}, "
              f"{h['lisensi']}\n   {h['deskripsi'] or h['halaman']}")
    print("\nPeriksa judul/deskripsi: pastikan foto benar-benar subjek yang dimaksud, lalu: jalankan foto ambil <id>")


def cmd_ambil(a):
    sumber, _, kunci = a.id.partition(":")
    if sumber == "commons":
        daftar = query_commons(titles=kunci if kunci.startswith("File:") else "File:" + kunci)
    elif sumber == "openverse":
        daftar = [info_openverse(json_url(OPENVERSE + urllib.parse.quote(kunci) + "/"))]
    else:
        sys.exit("id harus commons:File:… atau openverse:<id> (lihat: jalankan foto cari …)")
    if not daftar:
        sys.exit(f"Foto tidak ditemukan: {a.id}")
    h = daftar[0]
    if not h["boleh"]:
        sys.exit(f"Lisensi tidak diizinkan: {h['lisensi'] or 'tidak diketahui'} (hanya CC0/PD/CC BY/CC BY-SA)")
    data = ambil_url(h["unduh"], MAKS_BYTE)
    ext = next((e for sig, e in JENIS.items() if data.startswith(sig)), None)
    if not ext or (ext == ".webp" and data[8:12] != b"WEBP"):
        sys.exit("Berkas yang diunduh bukan JPG/PNG/WebP.")
    nama = re.sub(r"[^a-z0-9]+", "-", (h["judul"] or kunci).lower()).strip("-")[:60] or "foto"
    FOTO.mkdir(parents=True, exist_ok=True)
    out = FOTO / f"{sumber}-{nama}{ext}"
    out.write_bytes(data)
    h["kredit"] = kredit(h["penulis"], h["sumber"], h["lisensi"])
    Path(str(out) + ".sumber.json").write_text(json.dumps(h, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"path:   {out}\nuri:    {out.as_uri()}\nkredit: {h['kredit']}\nhalaman: {h['halaman']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("cari"); p.add_argument("kata"); p.add_argument("--jumlah", type=int, default=4)
    p.set_defaults(fn=cmd_cari)
    p = sub.add_parser("ambil"); p.add_argument("id"); p.set_defaults(fn=cmd_ambil)
    a = ap.parse_args()
    try:
        a.fn(a)
    except (RuntimeError, OSError) as e:
        sys.exit(f"Gagal: {e}. Pakai foto lain atau visual tanpa foto.")


if __name__ == "__main__":
    main()
