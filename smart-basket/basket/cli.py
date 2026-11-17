"""Command line:  python -m basket <command>

  fetch [--store KEY] [-v]          download latest prices for enabled stores
  stores list | find CHAIN_KEY TEXT show configured stores / search a chain's branch directory
  search TEXT [--store KEY]         search the price DB (to find barcodes for the catalog)
  receipt import [FILE ...]         learn from data/receipts/*.json
  catalog [--status core]           print the catalog
  compare [--date YYYY-MM-DD] [--all] [--store KEY ...]   cheapest basket
  offers PRODUCT_ID                 every candidate price for one product
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from . import catalog, config, matcher, optimizer, prices, receipts
from .fetchers import get_fetcher


def cmd_fetch(a) -> int:
    con = prices.connect()
    stores = optimizer.load_stores(enabled_only=not a.store)
    if a.store:
        stores = [s for s in stores if s["key"] in a.store]
    rc = 0
    for s in stores:
        if not s.get("source"):
            print(f"- {s['key']}: manual-only store (prices from data/manual_deals.json)")
            continue
        try:
            res = get_fetcher(s).fetch(s)
            if a.verbose:
                raw = config.RAW_DIR / s["key"]
                raw.mkdir(parents=True, exist_ok=True)
                (raw / "price.xml").write_bytes(res.price_xml)
                if res.promo_xml:
                    (raw / "promo.xml").write_bytes(res.promo_xml)
            n = prices.load_price_file(con, s["key"], res.price_xml)
            k = prices.load_promo_file(con, s["key"], res.promo_xml) if res.promo_xml else 0
            prices.log_fetch(con, s["key"], n, k, res.source)
            print(f"✓ {s['key']}: {n} items, {k} promo lines  ({res.source})")
        except Exception as e:  # keep going with other stores
            rc = 1
            print(f"✗ {s['key']}: {e}", file=sys.stderr)
    return rc


def cmd_stores(a) -> int:
    all_stores = optimizer.load_stores(enabled_only=False)
    if a.action == "list":
        for s in all_stores:
            flag = "on " if s.get("enabled", True) else "off"
            print(f"[{flag}] {s['key']:<22} {s.get('name', '')}  source={s.get('source')} store_id={s.get('store_id')}")
        return 0
    s = next((x for x in all_stores if x["key"] == a.key), None)
    if not s:
        print(f"unknown store key {a.key}", file=sys.stderr)
        return 1
    for b in get_fetcher(s).list_stores(s):
        if not a.text or a.text in b["name"] or a.text in b["address"] or a.text == b["city"]:
            print(f"{b['store_id']:>5}  {b['name']}  |  {b['address']}  city={b['city']}  type={b['type']}")
    return 0


def cmd_search(a) -> int:
    con = prices.connect()
    for r in prices.search(con, a.text, a.store, a.limit):
        up = f"{r['unit_price']:.2f}" if r["unit_price"] else "-"
        print(f"{r['store_key']:<20} {r['item_code']:>14}  {r['price']:>7.2f}  /unit {up:>7}  {r['name']}  ({r['manufacturer']})")
    return 0


def cmd_receipt(a) -> int:
    paths = [Path(p) for p in a.files] or None
    for rep in receipts.import_all(paths):
        print(json.dumps(rep, ensure_ascii=False))
    return 0


def cmd_catalog(a) -> int:
    cat = catalog.load()
    for p in cat["products"]:
        if a.status and p.get("status") != a.status:
            continue
        st = p.get("stats", {})
        print(f"{p.get('status', ''):<10} {p['id']:<30} {p['name']:<35} need={p.get('need', {}).get('qty')} "
              f"bought={st.get('times_bought', 0)} match={p.get('match', {}).get('type')}")
    return 0


def cmd_compare(a) -> int:
    cat = catalog.load()
    statuses = ("core", "occasional") if a.all else ("core",)
    res = optimizer.optimize(catalog.basket(cat, statuses), date.fromisoformat(a.date) if a.date else None, a.store)
    path = optimizer.save_report(res)
    names = {p["id"]: p["name"] for p in res["products"]}
    print(f"סל: {len(res['products'])} מוצרים | תאריך {res['for_date']} ({res['weekday']}) | מבצעים ידניים: {res['deals_active']}")
    print("\nחנות אחת:")
    for s in res["singles"]:
        print(f"  {s['name']:<25} ₪{s['total']:>8.2f}  כיסוי {s['coverage']:.0%}  הערכה לסל מלא ₪{s['estimated_full']:.2f}")
    if res["best_pair"]:
        bp = res["best_pair"]
        print(f"\nפיצול מומלץ: {' + '.join(bp['stores'])}  ₪{bp['total']:.2f} (כיסוי {bp['coverage']:.0%})")
        for sk in bp["stores"]:
            items = [names[i] for i, k in bp["assign"].items() if k == sk]
            print(f"  {sk} (₪{bp['subtotals'][sk]:.2f}): {', '.join(items)}")
    print(f"\nהמלצה: {'פיצול בין שתי חנויות' if res['recommend'] == 'split' else 'חנות אחת'}")
    print(f"דו\"ח נשמר: {path}")
    return 0


def cmd_offers(a) -> int:
    cat = catalog.load()
    p = catalog.by_id(cat).get(a.product_id)
    if not p:
        print("unknown product id", file=sys.stderr)
        return 1
    con = prices.connect()
    for s in optimizer.load_stores():
        for o in matcher.all_offers(con, s["key"], p, s.get("clubs", [])):
            print(f"{s['key']:<20} ₪{o.cost:>7.2f}  ({o.packs} x {o.effective:.2f}) {'exact' if o.exact else 'flex '} "
                  f"{o.item_code:>14} {o.name} {('· ' + o.promo) if o.promo else ''}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="basket", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch"); f.add_argument("--store", nargs="*"); f.add_argument("-v", "--verbose", action="store_true")
    f.set_defaults(fn=cmd_fetch)
    s = sub.add_parser("stores"); s.add_argument("action", choices=["list", "find"])
    s.add_argument("key", nargs="?"); s.add_argument("text", nargs="?", default=""); s.set_defaults(fn=cmd_stores)
    q = sub.add_parser("search"); q.add_argument("text"); q.add_argument("--store", nargs="*")
    q.add_argument("--limit", type=int, default=30); q.set_defaults(fn=cmd_search)
    r = sub.add_parser("receipt"); r.add_argument("action", choices=["import"]); r.add_argument("files", nargs="*")
    r.set_defaults(fn=cmd_receipt)
    c = sub.add_parser("catalog"); c.add_argument("--status"); c.set_defaults(fn=cmd_catalog)
    cp = sub.add_parser("compare"); cp.add_argument("--date"); cp.add_argument("--all", action="store_true")
    cp.add_argument("--store", nargs="*"); cp.set_defaults(fn=cmd_compare)
    o = sub.add_parser("offers"); o.add_argument("product_id"); o.set_defaults(fn=cmd_offers)
    a = ap.parse_args(argv)
    return a.fn(a)
