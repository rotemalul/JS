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
    report = {"receipt": rid, "matched": 0, "new": [], "lines": len(r.get("lines", [])), "sum_lines": 0.0}
    index = catalog.by_id(cat)
    for ln in r.get("lines", []):
        raw = (ln.get("raw_name") or "").strip()
        if not raw:
            continue
        p = index.get(ln.get("product_id") or "") or catalog.find(cat, barcode=ln.get("barcode"), name=raw)
        if p is None:
            p = catalog.new_product(cat, raw, barcode=ln.get("barcode"))
            index[p["id"]] = p
            report["new"].append(p["id"])
        else:
            report["matched"] += 1
        if ln.get("barcode") and p["match"].get("type") == "barcode":
            codes = p["match"].setdefault("barcodes", [])
            if ln["barcode"] not in codes:
                codes.append(ln["barcode"])
        qty = float(ln.get("qty") or 1)
        catalog.record_purchase(p, receipt_id=rid, date=r.get("date", ""), qty=qty,
                                price=ln.get("unit_price"), store=r.get("store", ""), raw_name=raw)
        report["sum_lines"] += float(ln.get("total") or 0) - float(ln.get("discount") or 0)
    report["sum_lines"] = round(report["sum_lines"], 2)
    report["printed_total"] = r.get("total")
    return report


def import_all(paths: list[Path] | None = None) -> list[dict]:
    cat = catalog.load()
    paths = paths or sorted(config.RECEIPTS_DIR.glob("*.json"))
    reports = [import_receipt(p, cat) for p in paths]
    order = [r.get("id") or r["_file"].removesuffix(".json") for r in list_receipts()]
    reports.append({"status_counts": catalog.relearn(cat, order)})
    catalog.save(cat)
    return reports
