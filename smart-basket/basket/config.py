"""Paths and JSON helpers. All persistent "memory" lives in data/ and memory/."""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(os.environ.get("SMART_BASKET_ROOT", Path(__file__).resolve().parent.parent))
DATA = ROOT / "data"
CATALOG_FILE = DATA / "catalog.json"
STORES_FILE = DATA / "stores.json"
DEALS_FILE = DATA / "manual_deals.json"
RECEIPTS_DIR = DATA / "receipts"
REPORTS_DIR = DATA / "reports"
PRICES_DB = DATA / "prices.db"
RAW_DIR = DATA / "raw"


def load_json(path: Path, default):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(path)
