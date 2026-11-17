"""Find the price of one catalog product in one store."""
from __future__ import annotations

import math
import sqlite3
from dataclasses import asdict, dataclass

from . import prices
from .normalize import norm_text


@dataclass
class Offer:
    store_key: str
    item_code: str
    name: str
    price: float          # regular shelf price (per pack, or per kg if weighted)
    effective: float      # after promo / manual deal
    packs: float          # packs (or kg) bought
    cost: float           # effective * packs
    unit_price: float | None
    promo: str | None = None
    exact: bool = True    # False = substitute found via flex rule

    def to_dict(self) -> dict:
        return asdict(self)


def _need_amount(product: dict) -> tuple[float, dict | None]:
    need = product.get("need", {}) or {}
    return float(need.get("qty") or 1), need.get("size")


def _apply_promo(con, store_key, row, packs, clubs) -> tuple[float, str | None]:
    pr = prices.best_promo_price(con, store_key, row["item_code"], packs, row["price"], clubs)
    return (pr[0], pr[1]) if pr else (row["price"], None)


def _need_base_amount(product: dict) -> tuple[float | None, str | None]:
    """Total amount needed per trip in base units (g/ml/unit), if known."""
    qty, size = _need_amount(product)
    if size and size.get("qty"):
        return size["qty"] * qty, size.get("unit")
    if (product.get("need") or {}).get("unit") == "kg":
        return qty * 1000.0, "g"
    return None, None


def _offer_for_row(con, store_key, row, product, clubs, exact) -> Offer:
    qty, _ = _need_amount(product)
    amount, unit = _need_base_amount(product)
    if row["is_weighted"]:
        packs = amount / 1000.0 if (amount and unit == "g") else qty   # priced per kg
    elif not exact and amount and row["size_qty"] and unit == row["size_unit"]:
        packs = max(1, math.ceil(amount / row["size_qty"] - 1e-9))     # enough packs to cover the need
    else:
        packs = qty
    eff, promo = _apply_promo(con, store_key, row, packs, clubs)
    return Offer(store_key, row["item_code"], row["name"], row["price"], eff, round(packs, 3),
                 round(eff * packs, 2), row["unit_price"], promo, exact)


def flex_candidates(con: sqlite3.Connection, store_key: str, rule: dict) -> list[sqlite3.Row]:
    inc = [norm_text(t) for t in rule.get("include", []) if t]
    if not inc:
        return []
    where = " AND ".join([f"name_norm LIKE ? {prices.LIKE_ESC}"] * len(inc))
    params = [prices.like(t) for t in inc]
    rows = con.execute(f"SELECT * FROM items WHERE store_key=? AND {where}", [store_key] + params).fetchall()
    exc = [norm_text(t) for t in rule.get("exclude", []) if t]
    brands = [norm_text(b) for b in rule.get("brands", []) if b]
    out = []
    for r in rows:
        nm = r["name_norm"]
        if any(e in nm for e in exc):
            continue
        if brands and not any(b in nm or b in norm_text(r["manufacturer"]) for b in brands):
            continue
        if "weighted" in rule and bool(r["is_weighted"]) != bool(rule["weighted"]):
            continue
        if rule.get("unit") and not r["is_weighted"] and r["size_unit"] != rule["unit"]:
            continue
        if rule.get("size_min") and (r["size_qty"] or 0) < rule["size_min"]:
            continue
        if rule.get("size_max") and (r["size_qty"] or 1e12) > rule["size_max"]:
            continue
        out.append(r)
    return out


def best_offer(con: sqlite3.Connection, store_key: str, product: dict, clubs=()) -> Offer | None:
    m = product.get("match", {}) or {}
    offers: list[Offer] = []
    for code in m.get("barcodes", []) or []:
        row = prices.by_barcode(con, store_key, code)
        if row:
            offers.append(_offer_for_row(con, store_key, row, product, clubs, exact=True))
    if m.get("type") == "flex":
        for row in flex_candidates(con, store_key, m):
            offers.append(_offer_for_row(con, store_key, row, product, clubs, exact=False))
    if not offers:
        return None
    return min(offers, key=lambda o: o.cost)


def all_offers(con, store_key: str, product: dict, clubs=(), limit: int = 8) -> list[Offer]:
    """For the UI 'why this price' drill-down."""
    m = product.get("match", {}) or {}
    rows = [prices.by_barcode(con, store_key, c) for c in m.get("barcodes", []) or []]
    offs = [_offer_for_row(con, store_key, r, product, clubs, True) for r in rows if r]
    if m.get("type") == "flex":
        offs += [_offer_for_row(con, store_key, r, product, clubs, False)
                 for r in flex_candidates(con, store_key, m)]
    return sorted(offs, key=lambda o: o.cost)[:limit]
