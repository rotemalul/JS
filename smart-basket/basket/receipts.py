"""Receipt import — the main learning input.

Workflow (see CLAUDE.md): the user uploads receipt photos -> Claude reads them and writes
data/receipts/<date>_<store>.json in the schema below -> `python -m basket receipt import`.

{
  "id": "2026-11-10_victory-netivot",
  "date": "2026-11-10",
  "store": "ויקטורי נתיבות",
  "store_key": "victory-netivot",          # optional, matches data/stores.json
  "total": 523.40,                          # as printed, used for sanity check
  "lines": [
    {"raw_name": "חלב תנובה 3% 1ל", "barcode": "7290004131074", "qty": 4,
     "unit_price": 6.90, "total": 27.60, "discount": 0, "product_id": null}
  ]
}
For weighted produce use "qty" = kg (e.g. 1.235) and "unit_price" = price per kg.
"barcode" may be a store-internal code (produce/deli, < 8 digits): it is kept on the receipt but
never used as a cross-store barcode. Lines with "skip": true (bags, deposits, donations) are not products.
Receipt-level "extra_discounts": [{"label", "amount"}] for promos not attributable to one line.
"""
from __future__ import annotations

from pathlib import Path

from . import catalog, config


def list_receipts() -> list[dict]:
    out = []
    for f in sorted(config.RECEIPTS_DIR.glob("*.json")):
        r = config.load_json(f, None)
        if r:
            r["_file"] = f.name
            out.append(r)
    return sorted(out, key=lambda r: (r.get("date", ""), r.get("id", "")))


def import_receipt(path: Path, cat: dict) -> dict:
    r = config.load_json(path, None)
    if not r:
        raise ValueError(f"cannot read {path}")
    rid = r.get("id") or path.stem
    report = {"receipt": rid, "matched": 0, "new": [], "skipped": 0, "lines": len(r.get("lines", [])), "sum_lines": 0.0}
    index = catalog.by_id(cat)
    bought: dict[str, dict] = {}  # product id -> aggregated purchase on this receipt
    for ln in r.get("lines", []):
        report["sum_lines"] += float(ln.get("total") or 0) - float(ln.get("discount") or 0)
        raw = (ln.get("raw_name") or "").strip()
        if not raw or ln.get("skip"):
            report["skipped"] += 1
            continue
        code = ln.get("barcode") if catalog.is_real_barcode(ln.get("barcode")) else None
        p = index.get(ln.get("product_id") or "") or catalog.find(cat, barcode=code, name=raw)
        if p is None:
            p = catalog.new_product(cat, raw, barcode=code)
            index[p["id"]] = p
            report["new"].append(p["id"])
        else:
            report["matched"] += 1
        if code and p["match"].get("type") == "barcode":
            codes = p["match"].setdefault("barcodes", [])
            if code not in codes:
                codes.append(code)
        b = bought.setdefault(p["id"], {"qty": 0.0, "paid": 0.0, "raw": raw, "price": ln.get("unit_price")})
        b["qty"] += float(ln.get("qty") or 1)
        b["paid"] += float(ln.get("total") or 0) - float(ln.get("discount") or 0)
    for pid, b in bought.items():
        catalog.record_purchase(index[pid], receipt_id=rid, date=r.get("date", ""), qty=round(b["qty"], 3),
                                price=b["price"], store=r.get("store", ""), raw_name=b["raw"],
                                paid=round(b["paid"], 2))
    report["sum_lines"] -= sum(float(x.get("amount") or 0) for x in r.get("extra_discounts", []))
    report["sum_lines"] = round(report["sum_lines"], 2)
    report["printed_total"] = r.get("total")
    if r.get("total") is not None and abs(report["sum_lines"] - r["total"]) > 0.05:
        report["warning"] = "sum of lines does not match printed total"
    return report


def import_all(paths: list[Path] | None = None) -> list[dict]:
    cat = catalog.load()
    paths = paths or sorted(config.RECEIPTS_DIR.glob("*.json"))
    reports = [import_receipt(p, cat) for p in paths]
    order = [r.get("id") or r["_file"].removesuffix(".json") for r in list_receipts()]
    reports.append({"status_counts": catalog.relearn(cat, order)})
    catalog.save(cat)
    return reports
