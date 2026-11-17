"""Find the cheapest store — or the cheapest split between two stores — for the basket."""
from __future__ import annotations

import itertools
from datetime import date, datetime
from statistics import median

from . import catalog, config, matcher, prices
from .matcher import Offer

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def load_stores(enabled_only: bool = True) -> list[dict]:
    st = config.load_json(config.STORES_FILE, {"stores": []})["stores"]
    return [s for s in st if s.get("enabled", True) or not enabled_only]


def settings() -> dict:
    return config.load_json(config.STORES_FILE, {}).get("settings", {})


def active_deals(on: date) -> list[dict]:
    deals = config.load_json(config.DEALS_FILE, {"deals": []})["deals"]
    wd = WEEKDAYS[on.weekday()]
    iso = on.isoformat()
    out = []
    for d in deals:
        if d.get("weekdays") and wd not in d["weekdays"]:
            continue
        if d.get("valid_from") and iso < d["valid_from"]:
            continue
        if d.get("valid_until") and iso > d["valid_until"]:
            continue
        out.append(d)
    return out


def _deal_offer(deals: list[dict], store_key: str, product: dict) -> Offer | None:
    best = None
    for d in deals:
        if d.get("store_key") != store_key:
            continue
        for it in d.get("items", []):
            if it.get("product_id") != product["id"]:
                continue
            qty = float(product.get("need", {}).get("qty") or 1)
            size = product.get("need", {}).get("size")
            if it.get("per") == "kg" and size and size.get("unit") == "g":
                qty = size["qty"] * qty / 1000.0
            cost = round(it["price"] * qty, 2)
            o = Offer(store_key, "manual", it.get("name") or product["name"], it["price"], it["price"],
                      qty, cost, None, f"{d.get('label', 'מבצע ידני')} (ידני)", True)
            if best is None or o.cost < best.cost:
                best = o
    return best


def price_matrix(con, products: list[dict], stores: list[dict], on: date) -> dict[str, dict[str, Offer | None]]:
    deals = active_deals(on)
    m: dict[str, dict[str, Offer | None]] = {}
    for p in products:
        row: dict[str, Offer | None] = {}
        for s in stores:
            o = matcher.best_offer(con, s["key"], p, s.get("clubs", [])) if s.get("source") else None
            d = _deal_offer(deals, s["key"], p)
            if d and (o is None or d.cost < o.cost):
                o = d
            row[s["key"]] = o
        m[p["id"]] = row
    return m


def _fee(store: dict, subtotal: float) -> float:
    if subtotal <= 0:
        return 0.0
    free_above = store.get("free_delivery_above")
    if free_above and subtotal >= free_above:
        return 0.0
    return float(store.get("delivery_fee") or 0)


def optimize(products: list[dict] | None = None, on: date | None = None, store_keys: list[str] | None = None) -> dict:
    on = on or date.today()
    cat = catalog.load()
    products = products if products is not None else catalog.basket(cat)
    stores = [s for s in load_stores() if not store_keys or s["key"] in store_keys]
    cfg = settings()
    con = prices.connect()
    m = price_matrix(con, products, stores, on)

    # reference price for a missing item = median of what other stores charge
    ref = {}
    for pid, row in m.items():
        costs = [o.cost for o in row.values() if o]
        ref[pid] = median(costs) if costs else 0.0

    singles = []
    for s in stores:
        sub = sum(m[p["id"]][s["key"]].cost for p in products if m[p["id"]][s["key"]])
        missing = [p["id"] for p in products if not m[p["id"]][s["key"]]]
        fee = _fee(s, sub)
        singles.append({
            "store": s["key"], "name": s.get("name", s["key"]),
            "subtotal": round(sub, 2), "fee": fee, "total": round(sub + fee, 2),
            "missing": missing, "coverage": round(1 - len(missing) / max(len(products), 1), 3),
            "estimated_full": round(sub + fee + sum(ref[i] for i in missing), 2),
        })
    min_cov = cfg.get("min_coverage", 0.8)
    split_gain = cfg.get("split_min_saving", 25)
    # stores that can't supply most of the basket go to the bottom
    singles.sort(key=lambda x: (x["coverage"] < min_cov, x["estimated_full"]))
    pairs = []
    for a, b in itertools.combinations(stores, 2):
        assign, sub = {}, {a["key"]: 0.0, b["key"]: 0.0}
        missing = []
        for p in products:
            oa, ob = m[p["id"]][a["key"]], m[p["id"]][b["key"]]
            best = min([o for o in (oa, ob) if o], key=lambda o: o.cost, default=None)
            if best is None:
                missing.append(p["id"])
                continue
            assign[p["id"]] = best.store_key
            sub[best.store_key] += best.cost
        fees = _fee(a, sub[a["key"]]) + _fee(b, sub[b["key"]])
        total = sum(sub.values()) + fees
        pairs.append({
            "stores": [a["key"], b["key"]], "subtotals": {k: round(v, 2) for k, v in sub.items()},
            "fees": fees, "total": round(total, 2), "missing": missing,
            "coverage": round(1 - len(missing) / max(len(products), 1), 3),
            "estimated_full": round(total + sum(ref[i] for i in missing), 2), "assign": assign,
        })
    pairs.sort(key=lambda x: (x["coverage"] < min_cov, x["estimated_full"]))

    best_single = next((s for s in singles if s["coverage"] >= min_cov), singles[0] if singles else None)
    best_pair = next((p for p in pairs if p["coverage"] >= min_cov), pairs[0] if pairs else None)
    recommend = "single"
    if best_single and best_pair and best_single["estimated_full"] - best_pair["estimated_full"] >= split_gain:
        recommend = "split"

    return {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "for_date": on.isoformat(), "weekday": WEEKDAYS[on.weekday()],
        "deals_active": [d.get("label") for d in active_deals(on)],
        "products": [{"id": p["id"], "name": p["name"], "qty": p.get("need", {}).get("qty", 1)} for p in products],
        "matrix": {pid: {sk: (o.to_dict() if o else None) for sk, o in row.items()} for pid, row in m.items()},
        "singles": singles, "pairs": pairs[:10],
        "best_single": best_single, "best_pair": best_pair, "recommend": recommend,
        "price_age": {s["key"]: (dict(r)["fetched_at"] if (r := prices.last_fetch(con, s["key"])) else None)
                      for s in stores},
    }


def save_report(res: dict) -> str:
    path = config.REPORTS_DIR / f"compare_{res['generated'].replace(':', '').replace('-', '')}.json"
    config.save_json(path, res)
    return str(path)
