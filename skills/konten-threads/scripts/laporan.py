#!/usr/bin/env python3
"""Laporan mingguan Threads per akun: performa utas, follower, dan pelajaran untuk utas berikutnya.

  jalankan laporan buat [--akun A]          ambil data minggu ini (Senin 00.00 WIB s.d. sekarang) dan
                                            minggu lalu (angka final), simpan, cetak pesan WA per akun
  jalankan laporan saran --akun A --minggu 2026-W47   simpan saran minggu depan (teks dari stdin)
  jalankan laporan ringkas [--akun A]       pelajaran 4 laporan terakhir + tren 8 minggu (dibaca agen
                                            sebelum menyusun usulan)
  jalankan laporan snapshot [--akun A]      catat jumlah follower saja (titik awal penambahan follower)

Tanpa --akun: semua akun yang punya token (lihat post_threads --daftar-akun).
Butuh izin token `threads_manage_insights` (selain threads_basic & threads_content_publish).

Data disimpan di samping folder antrian ($KONTEN_DATA_DIR/../laporan/):
  laporan.db                 SQLite: postingan, metrik (per pengambilan), follower, laporan
  <akun>/<YYYY-Www>.json     ringkasan angka minggu itu
  <akun>/<YYYY-Www>.md       pesan WA + saran
  pelajaran.md               4 laporan terakhir per akun (diperbarui otomatis)
Metrik utas = postingan pertamanya (hook); balasan berantai di bawahnya tidak dijumlahkan.
"""
import argparse
import datetime as dt
import json
import sqlite3
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import antrian  # noqa: E402
import post_threads as pt  # noqa: E402

WIB = antrian.WIB
DIR = antrian.DATA.parent / "laporan"
DB = DIR / "laporan.db"
DESAIN = antrian.DATA.parent / "desain"
METRIK = ("views", "likes", "replies", "reposts", "quotes", "shares")
BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]

SKEMA = """
CREATE TABLE IF NOT EXISTS postingan (
  akun TEXT NOT NULL, media_id TEXT NOT NULL, waktu TEXT NOT NULL, teks TEXT, permalink TEXT,
  media_type TEXT, kategori TEXT, topik TEXT, format TEXT, visual TEXT, slot TEXT,
  PRIMARY KEY (akun, media_id));
CREATE TABLE IF NOT EXISTS metrik (
  akun TEXT NOT NULL, media_id TEXT NOT NULL, diambil TEXT NOT NULL,
  views INTEGER, likes INTEGER, replies INTEGER, reposts INTEGER, quotes INTEGER, shares INTEGER,
  PRIMARY KEY (akun, media_id, diambil));
CREATE TABLE IF NOT EXISTS follower (
  akun TEXT NOT NULL, diambil TEXT NOT NULL, jumlah INTEGER NOT NULL, PRIMARY KEY (akun, diambil));
CREATE TABLE IF NOT EXISTS laporan (
  akun TEXT NOT NULL, minggu TEXT NOT NULL, dibuat TEXT NOT NULL, ringkasan TEXT NOT NULL, saran TEXT,
  PRIMARY KEY (akun, minggu));
"""


def db() -> sqlite3.Connection:
    DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.executescript(SKEMA)
    return con


# ---------------------------------------------------------------- waktu & angka

def sekarang() -> dt.datetime:
    return dt.datetime.now(WIB)


def awal_minggu(t: dt.datetime) -> dt.datetime:
    """Senin 00.00 WIB minggu yang memuat t."""
    senin = t.astimezone(WIB).date() - dt.timedelta(days=t.astimezone(WIB).weekday())
    return dt.datetime.combine(senin, dt.time(0), WIB)


def label_minggu(t: dt.datetime) -> str:
    th, mg, _ = t.astimezone(WIB).date().isocalendar()
    return f"{th}-W{mg:02d}"


def rentang_teks(mulai: dt.datetime, akhir: dt.datetime) -> str:
    a, b = mulai.date(), (akhir - dt.timedelta(seconds=1)).date()
    if a.month == b.month:
        return f"{a.day}–{b.day} {BULAN[b.month - 1]} {b.year}"
    return f"{a.day} {BULAN[a.month - 1]} – {b.day} {BULAN[b.month - 1]} {b.year}"


def angka(n) -> str:
    return f"{int(n or 0):,}".replace(",", ".")


def persen(x) -> str:
    return "-" if x is None else f"{x * 100:.1f}%".replace(".", ",")


def selisih(n) -> str:
    return f"+{angka(n)}" if n >= 0 else f"-{angka(-n)}"


def cuplik(teks: str, maks: int = 60) -> str:
    baris = next((b.strip() for b in (teks or "").splitlines() if b.strip()), "(tanpa teks)")
    return baris if len(baris) <= maks else baris[: maks - 1].rstrip() + "…"


def waktu_bagian(waktu_iso: str) -> str:
    jam = dt.datetime.fromisoformat(waktu_iso).astimezone(WIB).hour
    return "pagi" if jam < 11 else "siang" if jam < 17 else "malam"


def interaksi(m: dict) -> int:
    return sum(int(m.get(k) or 0) for k in ("likes", "replies", "reposts", "quotes", "shares"))


def rasio(inter: int, views: int):
    return inter / views if views else None


# ---------------------------------------------------------------- Threads API

def api(path: str, **param) -> dict:
    param["access_token"] = pt.token()
    return pt.http("GET", f"{pt.API}/{path}?{urllib.parse.urlencode(param)}")


def nilai(item: dict) -> int:
    if "total_value" in item:
        return int(item["total_value"].get("value") or 0)
    vals = item.get("values") or [{}]
    return int(vals[-1].get("value") or 0)


def daftar_postingan(mulai: dt.datetime, akhir: dt.datetime) -> list:
    """Postingan utama akun (bukan balasan, bukan repost) dalam rentang waktu."""
    hasil, r = [], api(f"{pt.user_id()}/threads", fields="id,text,timestamp,permalink,media_type",
                         since=int(mulai.timestamp()), until=int(akhir.timestamp()), limit=100)
    while True:
        hasil += [p for p in r.get("data", []) if p.get("media_type") != "REPOST_FACADE"]
        nxt = (r.get("paging") or {}).get("next")
        if not nxt or len(hasil) > 500:
            break
        r = pt.http("GET", nxt)
    return hasil


def insight_postingan(media_id: str) -> dict:
    try:
        r = api(f"{media_id}/insights", metric=",".join(METRIK))
    except RuntimeError:
        # "shares" belum tersedia di semua akun/versi API: coba tanpa itu
        r = api(f"{media_id}/insights", metric=",".join(METRIK[:-1]))
    m = {k: 0 for k in METRIK}
    for item in r.get("data", []):
        if item.get("name") in m:
            m[item["name"]] = nilai(item)
    return m


def jumlah_follower() -> int:
    r = api(f"{pt.user_id()}/threads_insights", metric="followers_count")
    for item in r.get("data", []):
        if item.get("name") == "followers_count":
            return nilai(item)
    raise RuntimeError("followers_count tidak ada di jawaban API")


def pesan_galat(e: Exception) -> str:
    t = str(e)
    if "threads_manage_insights" in t or "permission" in t.lower() or '"code":10' in t:
        return ("Token belum punya izin threads_manage_insights. Tambahkan izin itu di aplikasi Meta, "
                "buat token baru, lalu isi ulang di ~/.openclaw/.env.")
    return t


# ---------------------------------------------------------------- data dari antrian

def jenis_visual(gambar) -> str:
    if not gambar:
        return "tanpa gambar"
    p = Path(str(gambar))
    if (DESAIN / f"{p.stem}.html").exists():
        return "desain bebas"
    if p.parent.name == "gambar":
        return "template"
    return "foto"


def info_antrian(mulai: dt.datetime, akhir: dt.datetime) -> dict:
    """media_id utama -> kategori/topik/format/visual/slot dari usulan yang diposting skill."""
    info, h = {}, mulai.date() - dt.timedelta(days=1)
    while h <= akhir.date():
        d = antrian.muat(h.isoformat())
        for slot, s in d.get("slot", {}).items():
            ids = s.get("media_ids") or []
            if s.get("status") != "terposting" or not ids or not s.get("disetujui"):
                continue
            o = s["opsi"][s["disetujui"] - 1]
            posts = o.get("posts") or []
            fmt = o.get("format") or ("utas" if len(posts) > 1 else "pendek")
            if fmt == "panjang":
                fmt = "utas"
            info[str(ids[0])] = {"kategori": o.get("kategori"), "topik": o.get("topik"), "format": fmt,
                                 "visual": jenis_visual(o.get("gambar")), "slot": slot}
        h += dt.timedelta(days=1)
    return info


# ---------------------------------------------------------------- menyimpan & membaca

def simpan_postingan(con, akun: str, posts: list, info: dict, diambil: str) -> None:
    for p in posts:
        mid = str(p["id"])
        meta = info.get(mid, {})
        waktu = dt.datetime.strptime(p["timestamp"], "%Y-%m-%dT%H:%M:%S%z").astimezone(WIB).isoformat()
        con.execute(
            """INSERT INTO postingan (akun, media_id, waktu, teks, permalink, media_type, kategori, topik, format, visual, slot)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(akun, media_id) DO UPDATE SET teks=excluded.teks, permalink=excluded.permalink,
                 kategori=COALESCE(excluded.kategori, postingan.kategori), topik=COALESCE(excluded.topik, postingan.topik),
                 format=COALESCE(excluded.format, postingan.format), visual=COALESCE(excluded.visual, postingan.visual),
                 slot=COALESCE(excluded.slot, postingan.slot)""",
            (akun, mid, waktu, p.get("text", ""), p.get("permalink", ""), p.get("media_type"),
             meta.get("kategori"), meta.get("topik"), meta.get("format"), meta.get("visual"), meta.get("slot")))
        m = insight_postingan(mid)
        con.execute("INSERT OR REPLACE INTO metrik VALUES (?,?,?,?,?,?,?,?,?)",
                    (akun, mid, diambil, *[m[k] for k in METRIK]))


def postingan_rentang(con, akun: str, mulai: dt.datetime, akhir: dt.datetime) -> list:
    """Postingan dalam rentang dengan metrik terbarunya."""
    rows = con.execute(
        """SELECT p.*, m.views, m.likes, m.replies, m.reposts, m.quotes, m.shares FROM postingan p
           JOIN metrik m ON m.akun = p.akun AND m.media_id = p.media_id
           WHERE p.akun = ? AND p.waktu >= ? AND p.waktu < ?
             AND m.diambil = (SELECT MAX(diambil) FROM metrik WHERE akun = p.akun AND media_id = p.media_id)
           ORDER BY p.waktu""",
        (akun, mulai.isoformat(), akhir.isoformat())).fetchall()
    return [dict(r) for r in rows]


def follower_lalu(con, akun: str, acuan: dt.datetime):
    """Jumlah follower terakhir yang dicatat ≥ 6 hari sebelum acuan (titik awal minggu ini)."""
    r = con.execute("SELECT jumlah, diambil FROM follower WHERE akun = ? AND diambil <= ? ORDER BY diambil DESC LIMIT 1",
                    (akun, (acuan - dt.timedelta(days=6)).isoformat())).fetchone()
    return (r["jumlah"], r["diambil"]) if r else (None, None)


# ---------------------------------------------------------------- menghitung

def statistik(posts: list) -> dict:
    views = sum(int(p.get("views") or 0) for p in posts)
    inter = sum(interaksi(p) for p in posts)
    return {"utas": len(posts), "views": views, "interaksi": inter, "rasio": rasio(inter, views),
            "likes": sum(int(p.get("likes") or 0) for p in posts),
            "replies": sum(int(p.get("replies") or 0) for p in posts)}


def kelompok(posts: list, kunci) -> list:
    """[(nilai, rasio, jumlah utas)] urut rasio tertinggi; kunci = nama kolom atau fungsi."""
    grup = {}
    for p in posts:
        k = kunci(p) if callable(kunci) else p.get(kunci)
        if k:
            grup.setdefault(k, []).append(p)
    hasil = [(k, statistik(v)["rasio"], len(v)) for k, v in grup.items()]
    return sorted(hasil, key=lambda x: (x[1] is not None, x[1] or 0, x[2]), reverse=True)


def teratas(posts: list) -> dict:
    if not posts:
        return {}
    pilih = lambda f: max(posts, key=f)  # noqa: E731
    return {"interaksi": pilih(interaksi), "reply": pilih(lambda p: int(p.get("replies") or 0)),
            "views": pilih(lambda p: int(p.get("views") or 0)), "sepi": min(posts, key=interaksi)}


def baris_kelompok(judul: str, grup: list) -> str:
    isi = " · ".join(f"{k} {persen(r)} ({n})" for k, r, n in grup)
    return f"- {judul}: {isi}"


def susun_pesan(handle: str, label: str, rentang: str, ini: list, lalu: list, follower: dict) -> str:
    s = statistik(ini)
    baris = [f"📊 Laporan mingguan {handle} — {rentang}", ""]
    if ini:
        baris.append(f"Ringkasan: {s['utas']} utas · {angka(s['views'])} views · "
                     f"{angka(s['interaksi'])} interaksi ({persen(s['rasio'])})")
    else:
        baris.append("Belum ada postingan minggu ini.")
    if follower.get("awal") is None:
        baris.append(f"Follower: {angka(follower['sekarang'])} (titik awal; penambahan tampil mulai laporan berikutnya)")
    else:
        b = f"Follower: {angka(follower['awal'])} → {angka(follower['sekarang'])} ({selisih(follower['tambah'])})"
        if follower.get("tambah_lalu") is not None:
            b += f" · minggu lalu {selisih(follower['tambah_lalu'])}"
        baris.append(b)

    if ini:
        t = teratas(ini)
        i = t["interaksi"]
        baris += ["",
                  f"🏆 Interaksi terbanyak: \"{cuplik(i['teks'])}\" — {angka(interaksi(i))} "
                  f"(like {angka(i['likes'])} · reply {angka(i['replies'])} · repost {angka(i['reposts'])})",
                  f"💬 Reply terbanyak: \"{cuplik(t['reply']['teks'])}\" — {angka(t['reply']['replies'])} reply",
                  f"👀 Views terbanyak: \"{cuplik(t['views']['teks'])}\" — {angka(t['views']['views'])}"]
        if len(ini) > 1:
            baris.append(f"📉 Paling sepi: \"{cuplik(t['sepi']['teks'])}\" — {angka(interaksi(t['sepi']))} interaksi")

        pola = [(judul, kelompok(ini, k)) for judul, k in (
            ("Kategori", "kategori"), ("Waktu", lambda p: waktu_bagian(p["waktu"])),
            ("Format", "format"), ("Visual", "visual"))]
        pola = [(j, g) for j, g in pola if g]
        if pola:
            baris += ["", "Pola minggu ini (rasio interaksi/views, jumlah utas):"]
            baris += [baris_kelompok(j, g) for j, g in pola]

    if lalu:
        sl, tl = statistik(lalu), teratas(lalu)["interaksi"]
        baris += ["", f"Minggu lalu (angka final): {sl['utas']} utas · {angka(sl['views'])} views · "
                      f"{angka(sl['interaksi'])} interaksi ({persen(sl['rasio'])}) · terbaik: "
                      f"\"{cuplik(tl['teks'], 45)}\" — {angka(interaksi(tl))}"]

    if ini:
        tautan = sorted(ini, key=interaksi, reverse=True)[:3]
        baris += ["", "Tautan 3 teratas:"] + [f"{n}. {p['permalink']}" for n, p in enumerate(tautan, 1) if p.get("permalink")]
    return "\n".join(baris)


def ringkasan_json(label, rentang, ini, lalu, follower) -> dict:
    t = teratas(ini)
    pilih = lambda p: p and {"media_id": p["media_id"], "teks": cuplik(p["teks"], 80), "permalink": p["permalink"],  # noqa: E731
                             "interaksi": interaksi(p), "replies": p["replies"], "views": p["views"]}
    return {
        "minggu": label, "rentang": rentang, "statistik": statistik(ini), "minggu_lalu": statistik(lalu),
        "follower": follower,
        "teratas": {k: pilih(v) for k, v in t.items()},
        "pola": {"kategori": kelompok(ini, "kategori"), "waktu": kelompok(ini, lambda p: waktu_bagian(p["waktu"])),
                 "format": kelompok(ini, "format"), "visual": kelompok(ini, "visual")},
    }


# ---------------------------------------------------------------- perintah

def akun_target(a) -> list:
    return [a.akun] if a.akun else pt.daftar_akun()


def snapshot(con, akun: str, waktu: dt.datetime) -> int:
    n = jumlah_follower()
    con.execute("INSERT OR REPLACE INTO follower VALUES (?,?,?)", (akun, waktu.isoformat(timespec="seconds"), n))
    return n


def buat_satu(con, akun: str, kini: dt.datetime) -> str:
    pt.AKUN = akun
    awal = awal_minggu(kini)
    awal_lalu = awal - dt.timedelta(days=7)
    diambil = kini.isoformat(timespec="seconds")
    info = info_antrian(awal_lalu, kini)
    simpan_postingan(con, akun, daftar_postingan(awal_lalu, kini), info, diambil)

    awal_f, _ = follower_lalu(con, akun, kini)
    n = snapshot(con, akun, kini)
    label = label_minggu(kini)
    lap_lalu = con.execute("SELECT ringkasan FROM laporan WHERE akun = ? AND minggu = ?",
                           (akun, label_minggu(awal_lalu))).fetchone()
    tambah_lalu = json.loads(lap_lalu["ringkasan"])["follower"].get("tambah") if lap_lalu else None
    follower = {"sekarang": n, "awal": awal_f, "tambah": None if awal_f is None else n - awal_f,
                "tambah_lalu": tambah_lalu}

    ini = postingan_rentang(con, akun, awal, kini)
    lalu = postingan_rentang(con, akun, awal_lalu, awal)
    rentang = rentang_teks(awal, awal + dt.timedelta(days=7))
    handle = pt.handle(akun)
    pesan = susun_pesan(handle, label, rentang, ini, lalu, follower)
    ringkas = ringkasan_json(label, rentang, ini, lalu, follower)
    ringkas["akun"], ringkas["handle"] = akun, handle
    con.execute(
        """INSERT INTO laporan (akun, minggu, dibuat, ringkasan) VALUES (?,?,?,?)
           ON CONFLICT(akun, minggu) DO UPDATE SET dibuat=excluded.dibuat, ringkasan=excluded.ringkasan""",
        (akun, label, diambil, json.dumps(ringkas, ensure_ascii=False)))
    con.commit()

    folder = DIR / akun
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{label}.json").write_text(json.dumps(ringkas, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / f"{label}.md").write_text(pesan + "\n", encoding="utf-8")
    return pesan


def cmd_buat(a):
    con, kini, gagal, akun = db(), sekarang(), 0, akun_target(a)
    if not akun:
        sys.exit("Belum ada akun: isi THREADS_ACCESS_TOKEN di ~/.openclaw/.env")
    for nama in akun:
        print(f"=== {pt.handle(nama)} (akun {nama}, minggu {label_minggu(kini)}) ===")
        try:
            print(buat_satu(con, nama, kini))
        except (Exception, SystemExit) as e:  # satu akun gagal (token, jaringan) tidak menghentikan akun lain
            con.rollback()
            gagal += 1
            print(f"⚠️ Laporan {pt.handle(nama)} gagal: {pesan_galat(e)}")
        print()
    tulis_pelajaran(con)
    if gagal == len(akun):
        sys.exit(1)


def cmd_saran(a):
    teks = sys.stdin.read().strip()
    if not teks:
        sys.exit("Saran kosong (kirim lewat stdin).")
    con = db()
    cur = con.execute("UPDATE laporan SET saran = ? WHERE akun = ? AND minggu = ?", (teks, a.akun, a.minggu))
    if cur.rowcount == 0:
        sys.exit(f"Belum ada laporan {a.akun} minggu {a.minggu}; jalankan 'laporan buat' dulu.")
    con.commit()
    md = DIR / a.akun / f"{a.minggu}.md"
    if md.exists():
        isi = md.read_text(encoding="utf-8").split("\n💡 Saran minggu depan:")[0].rstrip()
        md.write_text(f"{isi}\n\n💡 Saran minggu depan:\n{teks}\n", encoding="utf-8")
    tulis_pelajaran(con)
    print(f"Saran tersimpan: {a.akun} {a.minggu}")


def tren(con, akun: str, minggu: int = 8) -> list:
    """Rasio interaksi/views per kategori, waktu, format, visual selama N minggu (metrik terbaru)."""
    mulai = (awal_minggu(sekarang()) - dt.timedelta(weeks=minggu - 1)).isoformat()
    posts = [dict(r) for r in con.execute(
        """SELECT p.*, m.views, m.likes, m.replies, m.reposts, m.quotes, m.shares FROM postingan p
           JOIN metrik m ON m.akun = p.akun AND m.media_id = p.media_id
           WHERE p.akun = ? AND p.waktu >= ?
             AND m.diambil = (SELECT MAX(diambil) FROM metrik WHERE akun = p.akun AND media_id = p.media_id)""",
        (akun, mulai))]
    if not posts:
        return []
    return [baris_kelompok(j, g) for j, g in (
        ("Kategori", kelompok(posts, "kategori")), ("Waktu", kelompok(posts, lambda p: waktu_bagian(p["waktu"]))),
        ("Format", kelompok(posts, "format")), ("Visual", kelompok(posts, "visual"))) if g] + [
        f"- Total: {len(posts)} utas, rasio {persen(statistik(posts)['rasio'])}"]


def teks_pelajaran(con, akun_filter=None) -> str:
    akun = [r["akun"] for r in con.execute("SELECT DISTINCT akun FROM laporan ORDER BY akun")]
    if akun_filter:
        akun = [x for x in akun if x == akun_filter]
    if not akun:
        return "Belum ada laporan mingguan."
    out = ["# Pelajaran dari laporan mingguan Threads",
           "Acuan untuk memilih topik, format, waktu, dan visual — bukan aturan mutlak; gaya tetap mengikuti contoh-postingan.md.", ""]
    for nama in akun:
        rows = con.execute("SELECT minggu, ringkasan, saran FROM laporan WHERE akun = ? ORDER BY minggu DESC LIMIT 4",
                           (nama,)).fetchall()
        handle = json.loads(rows[0]["ringkasan"]).get("handle", nama)
        out.append(f"## {handle} (akun {nama})")
        t = tren(con, nama)
        if t:
            out += ["Tren 8 minggu (rasio interaksi/views, jumlah utas):"] + t
        for r in rows:
            j = json.loads(r["ringkasan"])
            s, top = j["statistik"], (j.get("teratas") or {}).get("interaksi")
            f = j.get("follower") or {}
            out.append(f"\n### {r['minggu']} ({j.get('rentang', '')})")
            out.append(f"- {s['utas']} utas, {angka(s['views'])} views, {angka(s['interaksi'])} interaksi ({persen(s['rasio'])})"
                       + (f", follower {selisih(f['tambah'])}" if f.get("tambah") is not None else ""))
            if top:
                out.append(f"- Terbaik: \"{top['teks']}\" — {angka(top['interaksi'])} interaksi, {angka(top['replies'])} reply")
            for kunci in ("kategori", "waktu", "format", "visual"):
                g = (j.get("pola") or {}).get(kunci) or []
                if len(g) > 1:
                    out.append(f"- {kunci.capitalize()} terbaik: {g[0][0]} ({persen(g[0][1])}), terlemah: {g[-1][0]} ({persen(g[-1][1])})")
            if r["saran"]:
                out.append("- Saran: " + r["saran"].replace("\n", " "))
        out.append("")
    return "\n".join(out)


def tulis_pelajaran(con) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    (DIR / "pelajaran.md").write_text(teks_pelajaran(con) + "\n", encoding="utf-8")


def cmd_ringkas(a):
    print(teks_pelajaran(db(), a.akun))


def cmd_snapshot(a):
    con, kini = db(), sekarang()
    for nama in akun_target(a):
        pt.AKUN = nama
        try:
            print(f"{pt.handle(nama)}: {angka(snapshot(con, nama, kini))} follower")
        except (Exception, SystemExit) as e:
            print(f"⚠️ {pt.handle(nama)}: {pesan_galat(e)}")
    con.commit()


def main():
    pt.muat_env()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nama, fn in (("buat", cmd_buat), ("ringkas", cmd_ringkas), ("snapshot", cmd_snapshot), ("saran", cmd_saran)):
        p = sub.add_parser(nama)
        p.set_defaults(fn=fn)
        p.add_argument("--akun", type=antrian.akun_type, required=(nama == "saran"))
        if nama == "saran":
            p.add_argument("--minggu", required=True, help="mis. 2026-W47 (tertera di judul blok 'laporan buat')")
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
