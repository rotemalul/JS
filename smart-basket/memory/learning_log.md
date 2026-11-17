# Learning log

Append-only. Format: `YYYY-MM-DD — what changed — why`.

- 2026-11-17 — Project created. Shufersal ONLINE feed (store 413) verified; Rami Levy / Yochananof / Osher Ad / Victory fetchers written but not verified. Catalog empty — waiting for first receipts.
- 2026-11-17 — Imported 2 receipts (Victory Netivot 05/11 ₪1,261.72; Yochananof Netivot 13/11 ₪1,119.87). Both reconcile to the agora (Victory: smudged Tirosh price read as 19.60 — confirmed by Shufersal list price 19.90; packaging tare lines are part of gross, not discounts).
- 2026-11-17 — Built catalog: 103 products, 9 core (in both receipts). Produce/meat/deli store codes are internal (not barcodes) → flex rules. Note: Victory deli code 55350 = suffix of Tnuva barcode 7290000055350 (עמק 28%) — Victory internal codes may hide real barcodes.
- 2026-11-17 — Code: aggregate repeated lines per receipt, `skip` lines (bags/deposits/donations), receipt-level `extra_discounts`, core requires ≥2 receipts, `need.unit = kg` for weighted products, `need.locked`.
- 2026-11-17 — First comparison vs Shufersal ONLINE: 82/103 products found; core basket ₪248.89 + ₪29.90 delivery (placeholder) vs ~₪218 paid in stores. Flex rules tightened after bad matches (cat-food salmon, "אסאדור" hotdogs, massage brush for "עמק").
