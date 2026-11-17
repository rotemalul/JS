"""End-to-end test on tiny fake price files: receipt -> catalog -> compare."""
import importlib
import json
from datetime import date

import pytest

PRICE_A = """<?xml version="1.0" encoding="utf-8"?><Root><ChainID>1</ChainID><StoreID>001</StoreID><Items>
<Item><ItemCode>7290004131074</ItemCode><ItemName>חלב בקרטון 3% שומן 1 ל</ItemName><ManufactureName>תנובה</ManufactureName>
 <Quantity>1</Quantity><UnitOfMeasure>ליטר</UnitOfMeasure><bIsWeighted>0</bIsWeighted><ItemPrice>7.35</ItemPrice></Item>
<Item><ItemCode>111</ItemCode><ItemName>קורנפלקס תלמה 750 גרם</ItemName><ManufactureName>תלמה</ManufactureName>
 <bIsWeighted>0</bIsWeighted><ItemPrice>18.90</ItemPrice></Item>
<Item><ItemCode>222</ItemCode><ItemName>קורנפלקס פרטי 1 ק"ג</ItemName><ManufactureName>פרטי</ManufactureName>
 <bIsWeighted>0</bIsWeighted><ItemPrice>15.00</ItemPrice></Item>
<Item><ItemCode>333</ItemCode><ItemName>עגבניה</ItemName><bIsWeighted>1</bIsWeighted><ItemPrice>8.90</ItemPrice></Item>
</Items></Root>"""

PRICE_B = """<Root><Items>
<Item><ItemCode>7290004131074</ItemCode><ItemName>חלב תנובה 3% 1 ליטר</ItemName><bIsWeighted>0</bIsWeighted><ItemPrice>6.90</ItemPrice></Item>
<Item><ItemCode>111</ItemCode><ItemName>קורנפלקס תלמה 750 גרם</ItemName><bIsWeighted>0</bIsWeighted><ItemPrice>21.90</ItemPrice></Item>
</Items></Root>"""

PROMO_A = """<Root><Promotions><Promotion><PromotionID>9</PromotionID><PromotionDescription>2 ב-12</PromotionDescription>
<PromotionEndDateTime>2099-01-01T00:00:00</PromotionEndDateTime><ClubID>0 - כלל הלקוחות</ClubID>
<PromotionItems><Item><ItemCode>7290004131074</ItemCode><MinQty>2</MinQty><DiscountedPrice>12</DiscountedPrice></Item></PromotionItems>
</Promotion></Promotions></Root>"""


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("SMART_BASKET_ROOT", str(tmp_path))
    from basket import config
    importlib.reload(config)
    import basket.catalog, basket.prices, basket.receipts, basket.optimizer, basket.matcher
    for m in (basket.prices, basket.catalog, basket.receipts, basket.matcher, basket.optimizer):
        importlib.reload(m)
    (tmp_path / "data" / "receipts").mkdir(parents=True)
    config.save_json(config.STORES_FILE, {"settings": {"split_min_saving": 1}, "stores": [
        {"key": "A", "name": "A", "source": "x", "delivery_fee": 0},
        {"key": "B", "name": "B", "source": "x", "delivery_fee": 0},
        {"key": "M", "name": "Market", "source": None},
    ]})
    config.save_json(config.DEALS_FILE, {"deals": [{"store_key": "M", "label": "שלישי שוק", "weekdays": ["tue"],
                                                    "items": [{"product_id": "tomato", "price": 2.9, "per": "kg"}]}]})
    con = basket.prices.connect()
    basket.prices.load_price_file(con, "A", PRICE_A.encode())
    basket.prices.load_promo_file(con, "A", PROMO_A.encode())
    basket.prices.load_price_file(con, "B", PRICE_B.encode())
    con.commit()
    return tmp_path


def test_receipt_learning_and_compare(env):
    from basket import catalog, config, optimizer, receipts
    for i, d in enumerate(["2026-11-03", "2026-11-10"]):
        config.save_json(config.RECEIPTS_DIR / f"{d}_x.json", {"id": f"{d}_x", "date": d, "store": "X", "lines": [
            {"raw_name": "חלב תנובה 3% 1ל", "barcode": "7290004131074", "qty": 2, "unit_price": 7, "total": 14},
            {"raw_name": "קורנפלקס תלמה", "qty": 1, "unit_price": 19, "total": 19},
        ]})
    reps = receipts.import_all()
    assert reps[-1]["status_counts"]["core"] == 2
    cat = catalog.load()
    milk = catalog.find(cat, barcode="7290004131074")
    assert milk["stats"]["times_bought"] == 2 and milk["need"]["qty"] == 2
    # re-import is idempotent
    receipts.import_all()
    assert catalog.find(catalog.load(), barcode="7290004131074")["stats"]["times_bought"] == 2

    # make cornflakes flexible (any brand, 500g-1kg), add tomatoes for the Tuesday market
    cf = catalog.find(cat, name="קורנפלקס תלמה")
    cf["match"] = {"type": "flex", "include": ["קורנפלקס"], "unit": "g", "size_min": 500, "size_max": 1000}
    cf["need"] = {"qty": 1, "size": {"qty": 750, "unit": "g"}}
    cat["products"].append({"id": "tomato", "name": "עגבניות", "status": "core",
                            "match": {"type": "flex", "include": ["עגבני"], "weighted": True},
                            "need": {"qty": 1, "size": {"qty": 2000, "unit": "g"}}})
    catalog.save(cat)

    res = optimizer.optimize(on=date(2026, 11, 17))  # a Tuesday
    m = res["matrix"]
    assert m[milk["id"]]["A"]["effective"] == 6.0          # 2-for-12 promo applied
    assert m[milk["id"]]["B"]["cost"] == 13.8
    assert m[cf["id"]]["A"]["item_code"] == "222"          # cheaper private-label 1kg substitute
    assert m["tomato"]["A"]["cost"] == 17.8                # 2kg * 8.90
    assert m["tomato"]["M"]["cost"] == 5.8                 # Tuesday market
    assert res["best_pair"]["assign"]["tomato"] == "M"

    res_wed = optimizer.optimize(on=date(2026, 11, 18))
    assert res_wed["matrix"]["tomato"]["M"] is None


def test_parse_size():
    from basket.normalize import parse_size
    assert parse_size("שישיית מים 6*1.5 ליטר").qty == 9000
    assert parse_size("גבינה לבנה3% 250ג").qty == 250
    assert parse_size('קפה 1 ק"ג').qty == 1000


def test_receipt_aggregation_internal_codes_and_skip(env):
    from basket import catalog, config, receipts
    config.save_json(config.RECEIPTS_DIR / "r1.json", {"id": "r1", "date": "2026-11-13", "store": "Y", "total": 160.0,
        "extra_discounts": [{"label": "x", "amount": 1.0}], "lines": [
        {"raw_name": "טחון בקר", "barcode": "407869", "qty": 1.144, "unit_price": 64.9, "total": 74.25, "discount": 11.33},
        {"raw_name": "טחון בקר", "barcode": "407869", "qty": 1.352, "unit_price": 64.9, "total": 87.74, "discount": 13.38},
        {"raw_name": "שקית", "barcode": "34560", "qty": 15, "total": 1.5, "skip": True},
        {"raw_name": "עגבניה", "barcode": "725", "qty": 0.94, "unit_price": 7.9, "total": 7.43, "discount": 2.82},
        {"raw_name": "תרומה", "barcode": "101114", "qty": 1, "total": 17.61, "skip": True}]})
    rep = receipts.import_all()[0]
    assert rep["skipped"] == 2 and "warning" not in rep
    cat = catalog.load()
    beef = catalog.find(cat, name="טחון בקר")
    assert beef["stats"]["qty_history"] == [2.496]          # two lines, one purchase
    assert beef["match"]["type"] == "flex"                  # internal code is not a barcode
    assert catalog.find(cat, barcode="725") is None
