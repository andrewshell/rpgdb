#!/usr/bin/env python3
"""TTRPG collection: SQLite catalogue fed by DriveThruRPG, exported as data for the 11ty site."""
import argparse
import difflib
import html
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "books.db"
COVERS = ROOT / "covers"
SITE = ROOT / "site"

API = "https://api.drivethrurpg.com/api/vBeta"
IMAGES = "https://d1vzi28wh99zvq.cloudfront.net/images/"
UA = {"User-Agent": "Mozilla/5.0 (personal collection tracker)"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
  id INTEGER PRIMARY KEY,
  source TEXT NOT NULL,            -- 'dtrpg' or 'manual'
  source_id TEXT NOT NULL,         -- DriveThruRPG productId, or a slug for manual entries
  title TEXT NOT NULL,
  authors TEXT NOT NULL DEFAULT '[]',
  artists TEXT NOT NULL DEFAULT '[]',
  publisher TEXT,
  categories TEXT NOT NULL DEFAULT '[]',
  isbn TEXT,
  pages INTEGER,
  description TEXT,
  url TEXT,
  cover TEXT,                      -- full-size cover, relative to covers/
  thumb TEXT,                      -- small cover for the site, relative to covers/
  copies INTEGER NOT NULL DEFAULT 1,
  notes TEXT,
  added_at TEXT NOT NULL,
  UNIQUE (source, source_id)
);
"""


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def get_json(path, **params):
    url = f"{API}/{path}?" + urllib.parse.urlencode({"siteId": 10, **params})
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        return json.load(r)


def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        dest.write_bytes(r.read())


def norm(s):
    s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    return " ".join(w for w in s.split() if w not in {"the", "a", "an", "of"})


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def find_owned(conn, query, limit=5):
    q = norm(query)
    scored = []
    for row in conn.execute("SELECT * FROM books"):
        t = norm(row["title"])
        words = set(norm(f'{row["title"]} {row["notes"] or ""}').split())
        score = 1.0 if q and all(w in words for w in q.split()) else difflib.SequenceMatcher(None, q, t).ratio()
        scored.append((score, row))
    scored.sort(key=lambda x: -x[0])
    return [(s, r) for s, r in scored[:limit] if s >= 0.6]


def describe(row):
    authors = ", ".join(json.loads(row["authors"]))
    bits = [f'#{row["id"]} {row["title"]}']
    if row["publisher"]:
        bits.append(row["publisher"])
    if authors:
        bits.append(authors)
    if row["copies"] > 1:
        bits.append(f'{row["copies"]} copies')
    if row["notes"]:
        bits.append(f'[{row["notes"]}]')
    return " — ".join(bits)


def cmd_search(args):
    data = get_json("products", keyword=args.query, pageSize=args.limit)["data"]
    if not data:
        print("NO RESULTS")
    for item in data:
        a = item["attributes"]
        bundle = " [BUNDLE]" if a.get("isBundle") else ""
        print(f'{a["productId"]}\t{a["description"]["name"]}{bundle}\t{", ".join(a["authors"])}')


def cmd_owned(args):
    hits = find_owned(db(), args.query)
    if not hits:
        print("NOT OWNED")
    for score, row in hits:
        print(f"{'OWNED' if score >= 0.85 else 'maybe'}\t{describe(row)}")


def bump_or_report(conn, existing, another_copy):
    if another_copy:
        conn.execute("UPDATE books SET copies = copies + 1 WHERE id = ?", (existing["id"],))
        conn.commit()
        print(f"ADDED COPY\t{describe(conn.execute('SELECT * FROM books WHERE id = ?', (existing['id'],)).fetchone())}")
    else:
        print(f"ALREADY OWNED\t{describe(existing)}")


def cmd_add(args):
    conn = db()
    pid = str(args.product_id)
    existing = conn.execute("SELECT * FROM books WHERE source='dtrpg' AND source_id=?", (pid,)).fetchone()
    if existing:
        return bump_or_report(conn, existing, args.another_copy)

    resp = get_json(f"products/{pid}")
    a = resp["data"]["attributes"]
    included = resp.get("included", [])
    publisher = next((i["attributes"]["name"] for i in included if i["type"] == "Publisher"), None)
    categories = [
        i["attributes"]["descriptions"][0]["name"]
        for i in included
        if i["type"] == "Category" and i["attributes"].get("descriptions")
    ]
    name = a["description"]["name"]
    desc = re.sub(r"<[^>]+>", "", html.unescape(a["description"].get("description") or "")).strip()

    cover = thumb = None
    if a.get("image"):
        cover = f"dtrpg-{pid}{Path(a['image']).suffix}"
        download(IMAGES + a["image"], COVERS / cover)
    small = a.get("thumbnail200") or a.get("thumbnail")
    if small:
        thumb = f"dtrpg-{pid}-thumb{Path(small).suffix}"
        download(IMAGES + small, COVERS / thumb)
    elif cover:
        thumb = make_thumb(cover, f"dtrpg-{pid}-thumb.jpg")

    conn.execute(
        """INSERT INTO books (source, source_id, title, authors, artists, publisher, categories, isbn, pages,
                              description, url, cover, thumb, notes, added_at)
           VALUES ('dtrpg', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            pid, name, json.dumps(a.get("authors") or []), json.dumps(a.get("artists") or []), publisher,
            json.dumps(categories), a.get("isbn") or None, a.get("pagecount") or None, desc,
            f"https://www.drivethrurpg.com/en/product/{pid}/{a['description'].get('slug', '')}",
            cover, thumb, args.notes, datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
    print(f"ADDED\t{describe(conn.execute('SELECT * FROM books WHERE source=? AND source_id=?', ('dtrpg', pid)).fetchone())}")


def cmd_add_manual(args):
    conn = db()
    sid = slug(args.title)
    existing = conn.execute("SELECT * FROM books WHERE source='manual' AND source_id=?", (sid,)).fetchone()
    if existing:
        return bump_or_report(conn, existing, args.another_copy)

    cover = thumb = None
    if args.cover:
        cover, thumb = save_cover(args.cover, f"manual-{sid}")
    conn.execute(
        """INSERT INTO books (source, source_id, title, authors, publisher, url, cover, thumb, notes, added_at)
           VALUES ('manual', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            sid, args.title, json.dumps(args.author or []), args.publisher, args.url, cover, thumb, args.notes,
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
    print(f"ADDED\t{describe(conn.execute('SELECT * FROM books WHERE source=? AND source_id=?', ('manual', sid)).fetchone())}")


def make_thumb(cover, thumb):
    subprocess.run(
        ["sips", "-s", "format", "jpeg", "-Z", "400", str(COVERS / cover), "--out", str(COVERS / thumb)],
        check=True, capture_output=True,
    )
    return thumb


def save_cover(src, stem):
    src = Path(src)
    cover = f"{stem}{src.suffix.lower()}"
    COVERS.mkdir(exist_ok=True)
    shutil.copyfile(src, COVERS / cover)
    return cover, make_thumb(cover, f"{stem}-thumb.jpg")


def cmd_set_cover(args):
    conn = db()
    row = conn.execute("SELECT * FROM books WHERE id=?", (args.id,)).fetchone()
    if not row:
        sys.exit(f"no book #{args.id}")
    cover, thumb = save_cover(args.image, f"{row['source']}-{row['source_id']}-own")
    for f in (row["cover"], row["thumb"]):
        if f and f not in (cover, thumb):
            (COVERS / f).unlink(missing_ok=True)
    conn.execute("UPDATE books SET cover=?, thumb=? WHERE id=?", (cover, thumb, args.id))
    conn.commit()
    print(f"COVER SET\t{describe(row)}")


def cmd_edit(args):
    conn = db()
    changes = {k: v for k, v in (("title", args.title), ("publisher", args.publisher), ("notes", args.notes)) if v is not None}
    if not changes:
        sys.exit("nothing to change; pass --title, --publisher and/or --notes")
    cur = conn.execute(
        f"UPDATE books SET {', '.join(f'{k}=?' for k in changes)} WHERE id=?", (*changes.values(), args.id)
    )
    if not cur.rowcount:
        sys.exit(f"no book #{args.id}")
    conn.commit()
    print(f"EDITED\t{describe(conn.execute('SELECT * FROM books WHERE id=?', (args.id,)).fetchone())}")


def cmd_remove(args):
    conn = db()
    row = conn.execute("SELECT * FROM books WHERE id=?", (args.id,)).fetchone()
    if not row:
        sys.exit(f"no book #{args.id}")
    conn.execute("DELETE FROM books WHERE id=?", (args.id,))
    conn.commit()
    for f in (row["cover"], row["thumb"]):
        if f:
            (COVERS / f).unlink(missing_ok=True)
    print(f"REMOVED\t{describe(row)}")


def cmd_list(args):
    for row in db().execute("SELECT * FROM books ORDER BY title COLLATE NOCASE"):
        print(describe(row))


def cmd_export(args):
    src = Path(args.out) / "src"
    covers = src / "covers"
    shutil.rmtree(covers, ignore_errors=True)
    covers.mkdir(parents=True)
    (src / "_data").mkdir(exist_ok=True)
    books = []
    for row in db().execute("SELECT * FROM books ORDER BY title COLLATE NOCASE"):
        if row["thumb"]:
            shutil.copyfile(COVERS / row["thumb"], covers / row["thumb"])
        books.append({
            "title": row["title"],
            "publisher": row["publisher"] or "",
            "authors": json.loads(row["authors"]),
            "copies": row["copies"],
            "notes": row["notes"] or "",
            "thumb": f"covers/{row['thumb']}" if row["thumb"] else None,
            "url": row["url"],
        })
    (src / "_data" / "books.json").write_text(json.dumps(books, indent=1))
    print(f"EXPORTED {len(books)} books to {src}/ — run `npm run build` in {args.out}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(required=True)

    s = sub.add_parser("search", help="search DriveThruRPG; prints productId, title, authors")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=5)
    s.set_defaults(fn=cmd_search)

    s = sub.add_parser("owned", help="fuzzy-check the local collection for a title")
    s.add_argument("query")
    s.set_defaults(fn=cmd_owned)

    s = sub.add_parser("add", help="add a DriveThruRPG product by productId")
    s.add_argument("product_id", type=int)
    s.add_argument("--another-copy", action="store_true", help="increment copies if already owned")
    s.add_argument("--notes")
    s.set_defaults(fn=cmd_add)

    s = sub.add_parser("add-manual", help="add a book DriveThruRPG doesn't carry")
    s.add_argument("title")
    s.add_argument("--author", action="append")
    s.add_argument("--publisher")
    s.add_argument("--cover", help="image file, e.g. a crop from the table photo")
    s.add_argument("--url")
    s.add_argument("--another-copy", action="store_true")
    s.add_argument("--notes")
    s.set_defaults(fn=cmd_add_manual)

    s = sub.add_parser("set-cover", help="replace a book's cover with your own image (e.g. a special edition)")
    s.add_argument("id", type=int)
    s.add_argument("image")
    s.set_defaults(fn=cmd_set_cover)

    s = sub.add_parser("edit", help="change a book's title, publisher or notes (notes are searchable)")
    s.add_argument("id", type=int)
    s.add_argument("--title")
    s.add_argument("--publisher")
    s.add_argument("--notes")
    s.set_defaults(fn=cmd_edit)

    s = sub.add_parser("remove", help="delete a book by its local #id")
    s.add_argument("id", type=int)
    s.set_defaults(fn=cmd_remove)

    s = sub.add_parser("list", help="list the collection")
    s.set_defaults(fn=cmd_list)

    s = sub.add_parser("export", help="write books.json and covers into the 11ty site")
    s.add_argument("--out", default=str(SITE))
    s.set_defaults(fn=cmd_export)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
