#!/usr/bin/env python3
"""Antrian usulan konten Threads per tanggal (WIB) dan slot (jam08 … jam20).

Perintah:
  simpan   --slot S [--akun A]      JSON {"opsi":[...]} dari stdin (menimpa usulan slot S hari ini)
  ganti    --slot S --opsi N        JSON satu opsi dari stdin (revisi opsi N)
  setujui  --slot S --opsi N        tandai opsi N disetujui
  skip     --slot S                 lewati slot hari ini
  status   [--tanggal YYYY-MM-DD]   ringkasan hari ini
  riwayat  [--hari 7]               topik yang sudah diposting/diusulkan N hari terakhir
  ambil    --slot S                 cetak opsi yang disetujui (JSON)
  slot-baru                         cetak nama slot manual berikutnya hari ini (manual1, manual2, ...)

Slot terjadwal: jam08, jam10, jam12, jam14, jam16, jam18, jam20 (posting tiap 2 jam, 08.00–20.00 WIB;
jam08 = utas panjang, sisanya pendek), atau manualN (trigger manual dari WhatsApp).
Usulan dibuat per gelombang (GELOMBANG): pagi → jam08+jam10, siang → jam12–jam16, sore → jam18+jam20.
Akun: tiap slot mencatat akun Threads tujuannya; post_threads.py memakai akun itu.
Slot terjadwal selalu ke **akun jadwal**: THREADS_AKUN_JADWAL di
~/.openclaw/.env (default `utama`). Slot manual: `--akun`, default `utama`.

Lokasi data: $KONTEN_DATA_DIR atau ~/.openclaw/workspace/konten-threads/antrian
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    WIB = ZoneInfo("Asia/Jakarta")
except Exception:  # pragma: no cover
    WIB = dt.timezone(dt.timedelta(hours=7))

SLOT = {f"jam{j:02d}": f"{j:02d}:00" for j in range(8, 21, 2)}  # jam08 … jam20
# Slot yang formatnya utas panjang (4–7 postingan); slot lain 1 postingan pendek.
SLOT_PANJANG = {"jam08"}
# Gelombang usulan: satu putaran riset/usulan menyiapkan beberapa slot sekaligus (cron-setup.sh).
GELOMBANG = {
    "pagi": ["jam08", "jam10"],
    "siang": ["jam12", "jam14", "jam16"],
    "sore": ["jam18", "jam20"],
}


def slot_type(s: str) -> str:
    """Validasi nama slot untuk argparse."""
    if s in SLOT or re.fullmatch(r"manual\d+", s):
        return s
    raise argparse.ArgumentTypeError(f"slot tidak dikenal: {s} ({', '.join(SLOT)} atau manualN)")


AKUN_UTAMA = "utama"


def akun_type(s: str) -> str:
    """Nama akun: huruf kecil dan angka, diawali huruf (jadi akhiran nama variabel env)."""
    s = s.strip().lstrip("@").lower()
    if re.fullmatch(r"[a-z][a-z0-9]{0,19}", s):
        return s
    raise argparse.ArgumentTypeError(f"nama akun tidak sah: {s} (huruf kecil/angka, diawali huruf)")


def akun_slot(s: dict) -> str:
    return (s or {}).get("akun") or AKUN_UTAMA


ENV_FILE = Path(os.path.expanduser("~/.openclaw/.env"))


def muat_env() -> None:
    """Isi os.environ dari ~/.openclaw/.env (yang sudah ada di environment menang)."""
    if ENV_FILE.exists():
        for baris in ENV_FILE.read_text().splitlines():
            baris = baris.strip()
            if baris and not baris.startswith("#") and "=" in baris:
                k, v = baris.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def akun_jadwal() -> str:
    """Akun yang dipakai posting terjadwal: THREADS_AKUN_JADWAL, default `utama`."""
    muat_env()
    nilai = os.environ.get("THREADS_AKUN_JADWAL", "").strip()
    if not nilai:
        return AKUN_UTAMA
    try:
        return akun_type(nilai)
    except argparse.ArgumentTypeError as e:
        sys.exit(f"THREADS_AKUN_JADWAL tidak sah: {e}")


def jam_slot(slot: str, s: dict = None) -> str:
    if slot in SLOT:
        return SLOT[slot] + " WIB"
    return (s or {}).get("jadwal") or "menunggu instruksi"
BATAS = 500
DATA = Path(os.path.expanduser(os.environ.get(
    "KONTEN_DATA_DIR", "~/.openclaw/workspace/konten-threads/antrian")))


def hari_ini() -> str:
    return dt.datetime.now(WIB).date().isoformat()


def panjang_threads(teks: str) -> int:
    """Perkiraan hitungan Threads: huruf biasa = 1, emoji/simbol = jumlah byte UTF-8."""
    n = 0
    for ch in teks:
        cat = unicodedata.category(ch)
        if ord(ch) > 0x2000 and (cat.startswith("S") or ord(ch) > 0xFFFF or cat == "Cf"):
            n += len(ch.encode("utf-8"))
        else:
            n += 1
    return n


def berkas(tanggal: str) -> Path:
    return DATA / f"{tanggal}.json"


def muat(tanggal: str) -> dict:
    p = berkas(tanggal)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"tanggal": tanggal, "slot": {}}


def tulis(data: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    p = berkas(data["tanggal"])
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def validasi_opsi(o: dict, slot: str, idx: int) -> list:
    err = []
    posts = o.get("posts")
    if not isinstance(posts, list) or not posts:
        return [f"opsi {idx}: 'posts' wajib berupa array tidak kosong"]
    fmt = o.get("format") or ("panjang" if slot in SLOT_PANJANG else "pendek")
    if fmt not in ("panjang", "pendek"):
        return [f"opsi {idx}: format harus 'panjang' atau 'pendek'"]
    o["format"] = fmt
    if fmt == "panjang" and not (2 <= len(posts) <= 10):
        err.append(f"opsi {idx}: format panjang sebaiknya 4–7 postingan (sekarang {len(posts)})")
    if fmt == "pendek" and len(posts) != 1:
        err.append(f"opsi {idx}: format pendek harus 1 postingan (sekarang {len(posts)})")
    for j, t in enumerate(posts, 1):
        n = panjang_threads(t)
        if n > BATAS:
            err.append(f"opsi {idx} postingan {j}: {n} karakter (> {BATAS}), persingkat")
        if t.count("http") > 5:
            err.append(f"opsi {idx} postingan {j}: lebih dari 5 tautan")
    g = o.get("gambar")
    if g and not Path(os.path.expanduser(g)).exists():
        err.append(f"opsi {idx}: gambar tidak ditemukan: {g}")
    tag = (o.get("tag") or "").lstrip("#")
    if any(c in tag for c in ".&"):
        err.append(f"opsi {idx}: tag tidak boleh berisi '.' atau '&'")
    o["tag"] = tag
    return err


def baca_stdin() -> dict:
    raw = sys.stdin.read()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        sys.exit(f"JSON tidak valid: {e}")


def cmd_simpan(a):
    masuk = baca_stdin()
    opsi = masuk.get("opsi", [])
    err = [e for i, o in enumerate(opsi, 1) for e in validasi_opsi(o, a.slot, i)]
    if not opsi:
        err.append("tidak ada opsi")
    if err:
        sys.exit("GAGAL VALIDASI:\n- " + "\n- ".join(err))
    if a.slot in SLOT:
        jadwal = akun_jadwal()
        if a.akun and a.akun != jadwal:
            sys.exit(f"Slot {a.slot} terjadwal selalu untuk akun jadwal ({jadwal}, THREADS_AKUN_JADWAL); "
                     "akun lain lewat slot manual (slot-baru).")
        a.akun = jadwal
    else:
        a.akun = a.akun or AKUN_UTAMA
    d = muat(a.tanggal)
    d["slot"][a.slot] = {"status": "menunggu", "disetujui": None, "opsi": opsi,
                         "akun": a.akun, "jadwal": a.jadwal or None,
                         "dibuat": dt.datetime.now(WIB).isoformat(timespec="seconds")}
    tulis(d)
    print(f"Tersimpan: {a.tanggal} slot {a.slot} (akun {a.akun}), {len(opsi)} opsi.")


def ambil_slot(d, slot):
    s = d["slot"].get(slot)
    if not s:
        sys.exit(f"Belum ada usulan untuk slot {slot} tanggal {d['tanggal']}.")
    return s


def cmd_ganti(a):
    o = baca_stdin()
    err = validasi_opsi(o, a.slot, a.opsi)
    if err:
        sys.exit("GAGAL VALIDASI:\n- " + "\n- ".join(err))
    d = muat(a.tanggal)
    s = ambil_slot(d, a.slot)
    if not 1 <= a.opsi <= len(s["opsi"]):
        sys.exit(f"Opsi {a.opsi} tidak ada (1–{len(s['opsi'])}).")
    s["opsi"][a.opsi - 1] = o
    if s.get("disetujui") == a.opsi and s["status"] == "disetujui":
        s["status"] = "menunggu"  # revisi membatalkan persetujuan lama
        s["disetujui"] = None
    tulis(d)
    print(f"Opsi {a.opsi} slot {a.slot} diperbarui. Perlu persetujuan ulang.")


def cmd_setujui(a):
    d = muat(a.tanggal)
    s = ambil_slot(d, a.slot)
    if s["status"] == "terposting":
        sys.exit(f"Slot {a.slot} sudah terposting.")
    if not 1 <= a.opsi <= len(s["opsi"]):
        sys.exit(f"Opsi {a.opsi} tidak ada (1–{len(s['opsi'])}).")
    s["status"], s["disetujui"] = "disetujui", a.opsi
    if a.jadwal:
        s["jadwal"] = a.jadwal
    tulis(d)
    print(f"Disetujui: slot {a.slot} opsi {a.opsi}, posting {jam_slot(a.slot, s)}.")


def cmd_skip(a):
    d = muat(a.tanggal)
    s = d["slot"].setdefault(a.slot, {"opsi": []})
    s["status"], s["disetujui"] = "dilewati", None
    tulis(d)
    print(f"Slot {a.slot} dilewati.")


def cmd_status(a):
    d = muat(a.tanggal)
    print(f"Status {d['tanggal']}:")
    semua = list(SLOT) + sorted(k for k in d["slot"] if k not in SLOT)
    for sl in semua:
        s = d["slot"].get(sl)
        jam = jam_slot(sl, s)
        if not s:
            print(f"- {sl} ({jam}): belum ada usulan")
            continue
        info = s["status"]
        if akun_slot(s) != AKUN_UTAMA:
            info = f"[{akun_slot(s)}] " + info
        if s.get("disetujui"):
            info += f" (opsi {s['disetujui']}: {s['opsi'][s['disetujui'] - 1].get('topik', '')})"
        if s.get("tautan"):
            info += f" → {s['tautan']}"
        print(f"- {sl} ({jam}): {info}")


def cmd_riwayat(a):
    hari = dt.datetime.now(WIB).date()
    for i in range(a.hari):
        t = (hari - dt.timedelta(days=i)).isoformat()
        if not berkas(t).exists():
            continue
        d = muat(t)
        for sl, s in d["slot"].items():
            for k, o in enumerate(s.get("opsi", []), 1):
                tanda = "✔ diposting" if s.get("status") == "terposting" and s.get("disetujui") == k else "usulan"
                print(f"{t} {sl} ({akun_slot(s)}) [{tanda}] {o.get('kategori', '')}: {o.get('topik', '')}")


def cmd_ambil(a):
    d = muat(a.tanggal)
    s = ambil_slot(d, a.slot)
    if s["status"] != "disetujui":
        print(json.dumps({"status": s["status"]}))
        sys.exit(2)
    print(json.dumps(s["opsi"][s["disetujui"] - 1], ensure_ascii=False, indent=2))


def cmd_slot_baru(a):
    d = muat(a.tanggal)
    n = 1
    while f"manual{n}" in d["slot"]:
        n += 1
    print(f"manual{n}")


def tandai_terposting(tanggal, slot, tautan, ids):
    d = muat(tanggal)
    s = d["slot"][slot]
    s.update(status="terposting", tautan=tautan, media_ids=ids,
             diposting=dt.datetime.now(WIB).isoformat(timespec="seconds"))
    tulis(d)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nama, fn, opsi in [("simpan", cmd_simpan, False), ("ganti", cmd_ganti, True),
                           ("setujui", cmd_setujui, True), ("skip", cmd_skip, False),
                           ("ambil", cmd_ambil, False)]:
        p = sub.add_parser(nama)
        p.add_argument("--slot", required=True, type=slot_type)
        if opsi:
            p.add_argument("--opsi", required=True, type=int)
        if nama in ("simpan", "setujui"):
            p.add_argument("--jadwal", default="", help="Teks jadwal posting, mis. 'sekarang' atau '2026-11-20 15:30 WIB'")
        if nama == "simpan":
            p.add_argument("--akun", default=None, type=akun_type,
                           help="Akun Threads tujuan (slot terjadwal: akun jadwal; manual: default utama)")
        p.add_argument("--tanggal", default=hari_ini())
        p.set_defaults(fn=fn)
    p = sub.add_parser("status"); p.add_argument("--tanggal", default=hari_ini()); p.set_defaults(fn=cmd_status)
    p = sub.add_parser("slot-baru"); p.add_argument("--tanggal", default=hari_ini()); p.set_defaults(fn=cmd_slot_baru)
    p = sub.add_parser("riwayat"); p.add_argument("--hari", type=int, default=7); p.set_defaults(fn=cmd_riwayat)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
