#!/usr/bin/env python3
"""Posting opsi yang sudah disetujui ke Threads (utas berantai + gambar di postingan pertama).

  python3 post_threads.py --slot jam08           # posting slot 08.00 hari ini (ke akun slot itu)
  python3 post_threads.py --slot jam08 --dry-run # simulasi tanpa memanggil API
  python3 post_threads.py --refresh-token [--akun A]  # perpanjang long-lived token (60 hari)
  python3 post_threads.py --cek [--akun A]       # cek token & akun
  python3 post_threads.py --daftar-akun          # akun yang disiapkan (tanpa menampilkan token)

Beberapa akun: akun `utama` memakai THREADS_USER_ID / THREADS_ACCESS_TOKEN / THREADS_HANDLE;
akun lain, mis. `bisnis`, memakai nama yang sama berakhiran _BISNIS. Slot di antrian mencatat
akunnya, jadi --slot selalu memposting ke akun yang benar. Posting terjadwal memakai akun
THREADS_AKUN_JADWAL (default utama).

Env: THREADS_USER_ID[_AKUN], THREADS_ACCESS_TOKEN[_AKUN], IMGBB_API_KEY (untuk hosting gambar)
Kode keluar: 0 sukses, 2 belum disetujui/sudah diposting/dilewati, 1 error.
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import antrian  # noqa: E402

API = "https://graph.threads.net/v1.0"
ENV_FILE = Path(os.path.expanduser("~/.openclaw/.env"))

# Akun yang sedang dipakai; diganti oleh --akun atau oleh akun slot yang diposting.
AKUN = antrian.AKUN_UTAMA


def nama_env(dasar: str, akun: str = None) -> str:
    """THREADS_ACCESS_TOKEN untuk akun utama, THREADS_ACCESS_TOKEN_BISNIS untuk akun bisnis."""
    akun = akun or AKUN
    return dasar if akun == antrian.AKUN_UTAMA else f"{dasar}_{akun.upper()}"


def muat_env():
    antrian.muat_env()


def http(method, url, data=None, timeout=60):
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code} {url.split('?')[0]}: {detail}") from None


def token():
    t = os.environ.get(nama_env("THREADS_ACCESS_TOKEN"))
    if not t:
        sys.exit(f"Akun {AKUN}: {nama_env('THREADS_ACCESS_TOKEN')} belum diisi di ~/.openclaw/.env")
    return t


def user_id():
    u = os.environ.get(nama_env("THREADS_USER_ID"))
    if not u:
        sys.exit(f"Akun {AKUN}: {nama_env('THREADS_USER_ID')} belum diisi di ~/.openclaw/.env")
    return u


def handle(akun: str = None) -> str:
    return os.environ.get(nama_env("THREADS_HANDLE", akun)) or f"akun {akun or AKUN}"


def daftar_akun() -> list:
    """Akun yang punya token di env: utama, lalu yang lain menurut abjad."""
    akun = []
    if os.environ.get("THREADS_ACCESS_TOKEN"):
        akun.append(antrian.AKUN_UTAMA)
    awalan = "THREADS_ACCESS_TOKEN_"
    akun += sorted(k[len(awalan):].lower() for k, v in os.environ.items() if k.startswith(awalan) and v)
    return akun


def unggah_gambar(path: str) -> str:
    key = os.environ.get("IMGBB_API_KEY")
    if not key:
        raise RuntimeError("IMGBB_API_KEY belum diisi (dibutuhkan agar Threads bisa mengambil gambar)")
    b64 = base64.b64encode(Path(os.path.expanduser(path)).read_bytes()).decode()
    r = http("POST", f"https://api.imgbb.com/1/upload?key={key}", {"image": b64})
    return r["data"]["url"]


def tunggu_siap(cid: str, maks=60):
    for _ in range(maks // 3):
        r = http("GET", f"{API}/{cid}?fields=status,error_message&access_token={token()}")
        st = r.get("status")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Container {cid} {st}: {r.get('error_message')}")
        time.sleep(3)
    raise RuntimeError(f"Container {cid} belum siap setelah {maks} detik")


def posting(teks, gambar_url=None, reply_to=None, tag=None):
    data = {"text": teks, "access_token": token()}
    if gambar_url:
        data.update(media_type="IMAGE", image_url=gambar_url)
    else:
        data["media_type"] = "TEXT"
    if reply_to:
        data["reply_to_id"] = reply_to
    if tag:
        data["topic_tag"] = tag
    cid = http("POST", f"{API}/{user_id()}/threads", data)["id"]
    tunggu_siap(cid)
    pid = http("POST", f"{API}/{user_id()}/threads_publish",
               {"creation_id": cid, "access_token": token()})["id"]
    return pid


def permalink(pid):
    try:
        return http("GET", f"{API}/{pid}?fields=permalink&access_token={token()}").get("permalink", "")
    except Exception:
        return ""


def jalankan(slot, tanggal, dry):
    global AKUN
    d = antrian.muat(tanggal)
    s = d["slot"].get(slot)
    if not s:
        print(f"Belum ada usulan slot {slot} ({tanggal})."); sys.exit(2)
    if s["status"] != "disetujui":
        print(f"Slot {slot} berstatus '{s['status']}', tidak diposting."); sys.exit(2)
    AKUN = antrian.akun_slot(s)
    o = s["opsi"][s["disetujui"] - 1]
    posts, tag, gbr = o["posts"], o.get("tag") or None, o.get("gambar")

    if dry:
        print(f"[DRY-RUN] slot {slot} → {handle()} ({AKUN}), opsi {s['disetujui']}, tag={tag}, gambar={gbr}")
        for i, t in enumerate(posts, 1):
            print(f"--- [{i}/{len(posts)}] ({antrian.panjang_threads(t)} karakter)\n{t}")
        return

    url_gbr = unggah_gambar(gbr) if gbr else None
    ids, induk = [], None
    for i, t in enumerate(posts):
        pid = posting(t, gambar_url=url_gbr if i == 0 else None,
                      reply_to=induk, tag=tag if i == 0 else None)
        ids.append(pid)
        induk = pid  # balasan berantai: tiap postingan membalas postingan sebelumnya
        if i < len(posts) - 1:
            time.sleep(4)
    link = permalink(ids[0])
    antrian.tandai_terposting(tanggal, slot, link, ids)
    print(f"✅ Terposting slot {slot} di {handle()} ({len(ids)} postingan): {link or ids[0]}")


def refresh():
    r = http("GET", "https://graph.threads.net/refresh_access_token?"
             + urllib.parse.urlencode({"grant_type": "th_refresh_token", "access_token": token()}))
    baru = r["access_token"]
    hari = int(r.get("expires_in", 0)) // 86400
    kunci = nama_env("THREADS_ACCESS_TOKEN")
    teks = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    baris = [b for b in teks.splitlines() if not b.startswith(f"{kunci}=")]
    baris.append(f"{kunci}={baru}")
    ENV_FILE.write_text("\n".join(baris) + "\n")
    print(f"Token akun {AKUN} diperbarui, berlaku ±{hari} hari. Restart gateway: openclaw gateway restart")


def cek():
    r = http("GET", f"{API}/me?fields=id,username&access_token={token()}")
    print(f"Token OK. Akun {AKUN}: @{r.get('username')} id={r.get('id')}")
    if r.get("id") != os.environ.get(nama_env("THREADS_USER_ID")):
        print(f"⚠️ {nama_env('THREADS_USER_ID')} di .env berbeda; seharusnya {r.get('id')}")


def main():
    muat_env()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slot", type=antrian.slot_type)
    ap.add_argument("--tanggal", default=antrian.hari_ini())
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--refresh-token", action="store_true")
    ap.add_argument("--cek", action="store_true")
    ap.add_argument("--akun", type=antrian.akun_type, default=antrian.AKUN_UTAMA,
                    help="Akun untuk --cek / --refresh-token (--slot memakai akun slotnya)")
    ap.add_argument("--daftar-akun", action="store_true")
    a = ap.parse_args()
    global AKUN
    AKUN = a.akun
    try:
        if a.daftar_akun:
            akun = daftar_akun()
            if not akun:
                print("Belum ada akun: isi THREADS_ACCESS_TOKEN di ~/.openclaw/.env")
            jadwal = antrian.akun_jadwal()
            for nama in akun:
                print(f"{nama}\t{handle(nama)}" + ("\t(posting terjadwal)" if nama == jadwal else ""))
            if jadwal not in akun:
                print(f"⚠️ THREADS_AKUN_JADWAL={jadwal}, tetapi akun itu belum punya token di .env")
        elif a.refresh_token:
            refresh()
        elif a.cek:
            cek()
        elif a.slot:
            jalankan(a.slot, a.tanggal, a.dry_run)
        else:
            ap.print_help()
    except RuntimeError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
