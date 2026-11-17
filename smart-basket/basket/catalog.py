"""The family product catalog — the long-term "memory" of what we buy.

data/catalog.json = {"version": 1, "products": [Product, ...]}

Product fields:
  id          stable slug
  name        display name (Hebrew)
  category    e.g. "חלב ומוצריו"
  match       how to find it in a store's price file:
                {"type": "barcode", "barcodes": ["7290004131074", ...]}      exact product (fixed)
                {"type": "flex", "include": ["קורנפלקס"], "exclude": ["דבש"],
                 "brands": [], "unit": "g", "size_min": 500, "size_max": 1000,
                 "barcodes": [preferred codes, optional]}                  any equivalent product
  need        {"qty": 2, "size": {"qty": 1000, "unit": "ml"}}   per typical shopping trip
              {"qty": 1.2, "unit": "kg"}  for things bought by weight (meat, produce): qty is kg
              "locked": true inside need -> learning won't overwrite qty
              for flex items price = cheapest unit price * qty * size; for weighted produce
              size is in grams (e.g. 1500 g of tomatoes)
  aliases     names as printed on receipts (normalized match)
  status      core | occasional | candidate | ignored
  locked      true -> status set by the user, learning will not change it
  stats       {"times_bought", "receipts", "qty_history", "last_bought", "last_price", "last_store"}
  notes       free text (preferences, "kids only eat this one", ...)
"""
from __future__ import annotations

import re
from statistics import median

from . import config
from .normalize import norm_text

CORE_FREQ = 0.4        # bought in >= 40% of recent receipts -> core
OCCASIONAL_FREQ = 0.15
RECENT_RECEIPTS = 12   # learning window


def load() -> dict:
    return config.load_json(config.CATALOG_FILE, {"version": 1, "products": []})


def save(cat: dict) -> None:
    cat["products"].sort(key=lambda p: (p.get("category") or "~", p["name"]))
    config.save_json(config.CATALOG_FILE, cat)


def slug(name: str, existing: set[str]) -> str:
    base = re.sub(r"[^\w\-]", "", re.sub(r"\s+", "-", norm_text(name)))[:40] or "item"
    s, i = base, 2
    while s in existing:
        s, i = f"{base}-{i}", i + 1
    return s


def is_real_barcode(code: str | None) -> bool:
    """Store-internal codes (produce, deli counter) are short; real EAN barcodes are 8+ digits."""
    return bool(code) and code.isdigit() and len(code.lstrip("0")) >= 8


def by_id(cat: dict) -> dict[str, dict]:
    return {p["id"]: p for p in cat["products"]}


def find(cat: dict, *, barcode: str | None = None, name: str | None = None) -> dict | None:
    if barcode and is_real_barcode(barcode):
        code = barcode.lstrip("0")
        for p in cat["products"]:
            if code in [b.lstrip("0") for b in p.get("match", {}).get("barcodes", [])]:
                return p
    if name:
        n = norm_text(name)
        for p in cat["products"]:
            if n == norm_text(p["name"]) or n in [norm_text(a) for a in p.get("aliases", [])]:
                return p
    return None


def new_product(cat: dict, name: str, *, barcode: str | None = None, category: str = "") -> dict:
    p = {
        "id": slug(name, {x["id"] for x in cat["products"]}),
        "name": name,
        "category": category,
        "match": {"type": "barcode", "barcodes": [barcode]} if barcode else
                 {"type": "flex", "include": norm_text(name).split()[:2], "exclude": [], "brands": []},
        "need": {"qty": 1},
        "aliases": [name],
        "status": "candidate",
        "locked": False,
        "stats": {"times_bought": 0, "receipts": [], "qty_history": []},
        "notes": "auto-created from receipt; review match rule",
    }
    cat["products"].append(p)
    return p


def record_purchase(p: dict, *, receipt_id: str, date: str, qty: float, price: float | None,
                    store: str, raw_name: str, paid: float | None = None) -> None:
    st = p.setdefault("stats", {"times_bought": 0, "receipts": [], "qty_history": []})
    if receipt_id in st["receipts"]:
        return  # idempotent re-import
    st["receipts"].append(receipt_id)
    st["times_bought"] = st.get("times_bought", 0) + 1
    st["qty_history"] = (st.get("qty_history", []) + [qty])[-RECENT_RECEIPTS:]
    if not st.get("last_bought") or date >= st["last_bought"]:
        st["last_bought"], st["last_price"], st["last_store"] = date, price, store
        st["last_paid_total"] = paid
    if raw_name and norm_text(raw_name) not in [norm_text(a) for a in p.setdefault("aliases", [])]:
        p["aliases"].append(raw_name)


def relearn(cat: dict, receipt_ids_by_date: list[str]) -> dict[str, int]:
    """Recompute status + typical quantity from the last RECENT_RECEIPTS receipts."""
    recent = set(receipt_ids_by_date[-RECENT_RECEIPTS:])
    n = max(len(recent), 1)
    counts = {"core": 0, "occasional": 0, "candidate": 0, "ignored": 0}
    for p in cat["products"]:
        st = p.get("stats", {})
        if st.get("qty_history") and not p.get("need", {}).get("locked"):
            p.setdefault("need", {})["qty"] = round(median(st["qty_history"]), 2)
        if not p.get("locked"):
            hits = len(recent & set(st.get("receipts", [])))
            freq = hits / n
            # core needs repetition: at least 2 receipts (one big shop is not a habit yet)
            p["status"] = "core" if (freq >= CORE_FREQ and hits >= 2) else "occasional" if freq >= OCCASIONAL_FREQ else "candidate"
            p.setdefault("stats", {})["frequency"] = round(freq, 2)
        counts[p.get("status", "candidate")] = counts.get(p.get("status", "candidate"), 0) + 1
    return counts


def basket(cat: dict, statuses: tuple[str, ...] = ("core",), extra_ids: list[str] | None = None) -> list[dict]:
    ids = set(extra_ids or [])
    return [p for p in cat["products"] if p.get("status") in statuses or p["id"] in ids]
