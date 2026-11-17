# Smart Basket — instructions for Claude

You are the "brain" of this project. The goal: **know the family's grocery basket and find, at a given
moment, the cheapest way to buy it online in Israel** — one store, or a split between two stores —
including manual deals that only exist in physical stores (e.g. "שלישי שוק" at Victory Netivot).

The user writes in Hebrew. Answer in Hebrew unless asked otherwise. Code, comments and JSON keys are English.

## Where the memory lives (read these first every session)

| File | What | Who edits |
|---|---|---|
| `memory/family_profile.md` | Household, preferences, brand loyalties, "never substitute" rules, where they shop | Claude, after every conversation that teaches something |
| `memory/learning_log.md` | Dated log of what was learned / changed and why | Claude, append-only |
| `data/catalog.json` | The product catalog (core list etc.) — the structured memory | `basket receipt import` + Claude |
| `data/receipts/*.json` | Transcribed receipts (source of truth for learning) | Claude |
| `data/manual_deals.json` | Deals not in the feeds (שלישי שוק...) | Claude / user |
| `data/stores.json` | Which stores to compare, delivery fees, club memberships | Claude / user |
| `data/reports/` | Saved comparisons (JSON) | `basket compare` |
| `data/prices.db` | SQLite price cache — not committed, rebuilt by `fetch` | `basket fetch` |

Never commit receipt photos (`data/receipts/images/` is git-ignored) — they contain private data.

## Setup

```bash
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
python -m pytest -q          # must pass
python -m basket fetch       # download prices
python -m web.app            # UI at http://127.0.0.1:8765
```

## Workflow 1 — the user uploads receipt photos

1. Read each image carefully. Transcribe **every line** into `data/receipts/<YYYY-MM-DD>_<store-slug>.json`
   (schema in `basket/receipts.py`). Rules:
   - `raw_name` exactly as printed (keep abbreviations); `barcode` if printed (Shufersal/Rami Levy often print it).
   - `qty` = units, or **kg** for weighted produce (then `unit_price` is per kg).
   - Discount lines ("הנחה", "מבצע") → put the amount in `discount` of the line they belong to.
   - Skip bags/deposit (פיקדון) unless the user wants them; note them in `notes`.
   - Fill `total` with the printed total and check `sum(lines) - discounts ≈ total`. If it doesn't match, say so.
   - If a line is unreadable, write your best guess and add `"uncertain": true`.
2. Before importing, try to link lines to existing products: set `product_id` when you're confident
   (`python -m basket catalog` lists ids). This avoids duplicates.
3. Run `python -m basket receipt import data/receipts/<file>.json`.
4. For every product in `"new"`:
   - Find it in the price DB: `python -m basket search "<words>"` → add the real barcode(s).
   - Decide **fixed vs flex** (see below), set `category`, `need.size` for flex items.
   - If it duplicates an existing product, merge (move aliases/stats, delete the duplicate).
5. Ask the user only about things you can't infer (e.g. "is this the only brand of hummus the kids eat?").
   Record the answers in `memory/family_profile.md`.
6. Append a line to `memory/learning_log.md`. Commit.

## Workflow 2 — "check prices" / "where is it cheapest now?"

1. `python -m basket fetch` (all enabled stores). Report stores that failed.
2. Ask (or infer) the shopping date — it matters for weekday deals. Tuesday → שלישי שוק is active.
3. `python -m basket compare --date YYYY-MM-DD` (add `--all` to include occasional items).
4. Present: best single store, best 2-store split (and saving vs. single), items missing per store,
   substitutes used (flex) and promos applied — the user must be able to sanity-check.
5. Flag anything suspicious: a price 50% below the last paid price (probably a wrong match or a club/coupon
   promo), substitutes that violate the profile, stale prices (> 2 days).

## Fixed vs flex products

- **fixed** (`match.type = "barcode"`): a specific product — "חלב תנובה 3% 1 ליטר", "קורנפלקס תלמה 750 ג'".
  List every barcode that is the same thing (carton vs. bag of the same milk only if the family accepts both).
- **flex** (`match.type = "flex"`): any equivalent product, compared by **unit price**:
  `{"type":"flex","include":["עגבניה"],"exclude":["שרי","מגי"],"weighted":true}`
  `{"type":"flex","include":["אורז","פרסי"],"unit":"g","size_min":900,"size_max":1100,"brands":["סוגת","מיה"]}`
  `need.size` is the amount per trip (e.g. `{"qty":2000,"unit":"g"}` for 2 kg tomatoes).
  Use `python -m basket offers <product_id>` to check what the rule actually matches and tighten
  `include`/`exclude` until only acceptable products remain.
- When unsure, start as fixed (safer) and ask the user whether a cheaper brand is OK.

## Status / learning rules (`basket/catalog.py`)

- `core` = bought in ≥ 40% of the last 12 receipts → always in the comparison basket.
- `occasional` ≥ 15%, otherwise `candidate`. `ignored` = never compare.
- A status set by the user (UI or chat) sets `locked: true`; learning won't override it.
- `need.qty` = median quantity per trip. The aim is a stable list covering 80–90% of spending.

## Price sources (Israeli Price Transparency Law — public XML files)

| Source | Chains | Status |
|---|---|---|
| `shufersal` – prices.shufersal.co.il | Shufersal (ONLINE = store 413, BE Netivot = 145) | ✅ verified 2026-11-17 |
| `cerberus` – url.publishedprices.co.il | Rami Levy (`RamiLevi`), Yochananof (`yohananof`), Osher Ad (`osherad`), Tiv Taam (`TivTaam`)… | ⚠️ coded, not yet verified |
| `laib` – laibcatalog.co.il | Victory, Mega Market… | ⚠️ coded, not yet verified |

To add a store: `python -m basket stores find <store-key> <text>` (e.g. `אינטרנט` / `נתיבות`) to get its
store_id, put it in `data/stores.json`, set `enabled: true`, `fetch -v` (saves raw XML in `data/raw/`
for debugging). Online stores usually appear in the feed as their own "store" (e.g. Shufersal 413).
The feeds don't include delivery fees — keep `delivery_fee` / `free_delivery_above` in stores.json updated.

## Promotions — conservative on purpose

`prices.best_promo_price`: coupons ignored; club promos only if the club is listed in the store's `clubs`;
multi-buy only if we buy ≥ min_qty. Feeds are inconsistent between chains — when a promo looks too good,
check it with `basket offers` and tell the user.

## Manual deals

`data/manual_deals.json`: `store_key`, `weekdays` (`mon..sun`), optional `valid_from/valid_until`,
`items: [{product_id, price, per: "kg"|"unit"}]`. A store with `"source": null` in stores.json is
"manual-only" (prices only from deals). When the user sends a flyer/sign photo — transcribe it here.

## Coding conventions

- Python 3.11+, stdlib + `requests` + `flask`. Keep it simple; no heavy frameworks.
- Every behaviour change → a test in `tests/`. Run `python -m pytest -q` before committing.
- JSON files are UTF-8 with `ensure_ascii=False` (Hebrew stays readable in diffs).
- This folder is meant to move to its own repository — keep all paths relative to the project root.
