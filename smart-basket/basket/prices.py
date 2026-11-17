"""Price database (SQLite cache) and parsers for the Israeli price-transparency XML files.

Under the Food Act (Price Transparency, 2014) every big chain publishes, per store:
  Stores*.xml     – list of branches
  PriceFull*.xml  – every item with price, barcode (ItemCode), size, manufacturer
  PromoFull*.xml  – promotions
Tag names vary slightly between chains (case, Item/Product), so parsing is tag-insensitive.
"""
from __future__ import annotations

import gzip
import io
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator
from xml.etree import ElementTree as ET

from . import config
from .normalize import norm_text, size_from_feed, unit_price

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    store_key TEXT NOT NULL,
    item_code TEXT NOT NULL,
    name TEXT,
    name_norm TEXT,
    manufacturer TEXT,
    size_qty REAL,
    size_unit TEXT,
    is_weighted INTEGER DEFAULT 0,
    price REAL,
    unit_price REAL,
    updated TEXT,
    PRIMARY KEY (store_key, item_code)
);
CREATE INDEX IF NOT EXISTS idx_items_code ON items(item_code);
CREATE TABLE IF NOT EXISTS promos (
    store_key TEXT NOT NULL,
    item_code TEXT NOT NULL,
    promo_id TEXT,
    description TEXT,
    discounted_price REAL,
    min_qty REAL,
    starts TEXT,
    ends TEXT,
    club TEXT,
    is_coupon INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_promos ON promos(store_key, item_code);
CREATE TABLE IF NOT EXISTS fetch_log (
    store_key TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    n_items INTEGER,
    n_promos INTEGER,
    source TEXT
);
"""


def like(token: str) -> str:
    """LIKE pattern for a literal substring (escapes % and _ — '3%' must not be a wildcard)."""
    return "%" + token.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


LIKE_ESC = "ESCAPE '\\'"


def connect(path: Path | None = None) -> sqlite3.Connection:
    path = path or config.PRICES_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


# ---------------------------------------------------------------- XML helpers

def open_payload(data: bytes) -> bytes:
    """Files come as .gz, sometimes .zip, sometimes plain XML."""
    if data[:2] == b"\x1f\x8b":
        return gzip.decompress(data)
    if data[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            return z.read(z.namelist()[0])
    return data


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _fields(elem: ET.Element) -> dict[str, str]:
    return {_local(c.tag): (c.text or "").strip() for c in elem}


def iter_items(xml_bytes: bytes) -> Iterator[dict[str, str]]:
    root = ET.fromstring(xml_bytes.lstrip(b"\xef\xbb\xbf").strip())
    for el in root.iter():
        if _local(el.tag) in ("item", "product") and len(el):
            f = _fields(el)
            if f.get("itemcode"):
                yield f


def iter_promos(xml_bytes: bytes) -> Iterator[tuple[dict[str, str], list[dict[str, str]]]]:
    root = ET.fromstring(xml_bytes.lstrip(b"\xef\xbb\xbf").strip())
    for el in root.iter():
        if _local(el.tag) == "promotion":
            head = _fields(el)
            items = []
            for sub in el.iter():
                if sub is el or not len(sub):
                    continue
                f = _fields(sub)
                if f.get("itemcode"):
                    items.append(f)
            yield head, items


def _num(s: str | None) -> float | None:
    try:
        return float(s) if s not in (None, "") else None
    except ValueError:
        return None


# ---------------------------------------------------------------- loaders

def load_price_file(con: sqlite3.Connection, store_key: str, xml_bytes: bytes) -> int:
    rows = []
    for f in iter_items(xml_bytes):
        price = _num(f.get("itemprice"))
        if price is None or price <= 0:
            continue
        name = f.get("itemname") or f.get("manufactureritemdescription") or ""
        weighted = f.get("bisweighted") in ("1", "true")
        size = size_from_feed(f.get("quantity"), f.get("unitofmeasure") or f.get("unitqty"), name)
        up = price if weighted else unit_price(price, size)  # weighted items are priced per kg
        rows.append((
            store_key, f["itemcode"].lstrip("0") or "0", name, norm_text(name),
            f.get("manufacturename") or f.get("manufacturername") or "",
            size.qty if size else None, size.unit if size else None,
            1 if weighted else 0, price, up, f.get("priceupdatedate") or f.get("priceupdatetime") or "",
        ))
    con.execute("DELETE FROM items WHERE store_key=?", (store_key,))
    con.executemany("INSERT OR REPLACE INTO items VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


def load_promo_file(con: sqlite3.Connection, store_key: str, xml_bytes: bytes) -> int:
    now = datetime.now().isoformat()
    rows = []
    for head, items in iter_promos(xml_bytes):
        end = head.get("promotionenddatetime") or head.get("promotionenddate") or ""
        if end and end[:10] < now[:10]:
            continue
        is_coupon = head.get("additionaliscoupon") in ("1", "true") or "קופון" in (head.get("promotiondescription") or "")
        for it in items:
            dp = _num(it.get("discountedprice")) or _num(head.get("discountedprice"))
            mq = _num(it.get("minqty")) or _num(head.get("minqty")) or 1.0
            rows.append((
                store_key, it["itemcode"].lstrip("0") or "0", head.get("promotionid"),
                head.get("promotiondescription"), dp, mq,
                head.get("promotionstartdatetime") or head.get("promotionstartdate") or "", end,
                head.get("clubid") or "", 1 if is_coupon else 0,
            ))
    con.execute("DELETE FROM promos WHERE store_key=?", (store_key,))
    con.executemany("INSERT INTO promos VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


def log_fetch(con, store_key: str, n_items: int, n_promos: int, source: str) -> None:
    con.execute("INSERT INTO fetch_log VALUES (?,?,?,?,?)",
                (store_key, datetime.now().isoformat(timespec="seconds"), n_items, n_promos, source))
    con.commit()


# ---------------------------------------------------------------- queries

def last_fetch(con, store_key: str) -> sqlite3.Row | None:
    return con.execute("SELECT * FROM fetch_log WHERE store_key=? ORDER BY fetched_at DESC LIMIT 1",
                       (store_key,)).fetchone()


def by_barcode(con, store_key: str, code: str) -> sqlite3.Row | None:
    return con.execute("SELECT * FROM items WHERE store_key=? AND item_code=?",
                       (store_key, code.lstrip("0"))).fetchone()


def search(con, text: str, store_keys: Iterable[str] | None = None, limit: int = 30) -> list[sqlite3.Row]:
    """All tokens of `text` must appear in the item name (or manufacturer)."""
    toks = norm_text(text).split()
    if not toks:
        return []
    where = " AND ".join([f"(name_norm LIKE ? {LIKE_ESC} OR manufacturer LIKE ? {LIKE_ESC})"] * len(toks))
    params: list = []
    for t in toks:
        params += [like(t), like(t)]
    if store_keys:
        keys = list(store_keys)
        where += f" AND store_key IN ({','.join('?' * len(keys))})"
        params += keys
    sql = f"SELECT * FROM items WHERE {where} ORDER BY unit_price IS NULL, unit_price LIMIT ?"
    return con.execute(sql, params + [limit]).fetchall()


def best_promo_price(con, store_key: str, code: str, qty: float, regular: float,
                     clubs_ok: Iterable[str] = ()) -> tuple[float, str] | None:
    """Effective per-unit price from a promotion, or None.

    Conservative rules (documented in CLAUDE.md):
      * coupons are ignored;
      * club promos are used only if the club name contains one of `clubs_ok`
        (club "0 - כלל הלקוחות" / empty is always OK);
      * multi-buy (min_qty>1) is used only if we buy at least min_qty;
      * if discounted_price looks like a bundle total (> 90% of regular price) it is divided by min_qty.
    """
    best = None
    for p in con.execute("SELECT * FROM promos WHERE store_key=? AND item_code=? AND is_coupon=0",
                         (store_key, code.lstrip("0"))):
        dp, mq = p["discounted_price"], p["min_qty"] or 1.0
        if not dp or dp <= 0:
            continue
        club = p["club"] or ""
        if club and not club.startswith("0") and "כלל" not in club and not any(c in club for c in clubs_ok):
            continue
        if mq > 1 and qty < mq:
            continue
        per_unit = dp / mq if (mq > 1 and dp > regular * 0.9) else dp
        if per_unit < regular and (best is None or per_unit < best[0]):
            best = (round(per_unit, 2), p["description"] or "מבצע")
    return best
