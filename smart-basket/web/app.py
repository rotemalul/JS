"""Local web UI:  python -m web.app   ->  http://127.0.0.1:8765"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from basket import catalog, config, optimizer, prices, receipts  # noqa: E402
from basket.cli import cmd_fetch  # noqa: E402

app = Flask(__name__)
app.secret_key = "local-only"

STATUSES = ["core", "occasional", "candidate", "ignored"]
STATUS_HE = {"core": "קבוע", "occasional": "מזדמן", "candidate": "מועמד", "ignored": "לא רלוונטי"}


@app.context_processor
def _globals():
    return {"STATUS_HE": STATUS_HE, "STATUSES": STATUSES}


def latest_report() -> dict | None:
    files = sorted(config.REPORTS_DIR.glob("compare_*.json"))
    return config.load_json(files[-1], None) if files else None


@app.get("/")
def home():
    cat = catalog.load()
    counts = {s: sum(1 for p in cat["products"] if p.get("status") == s) for s in STATUSES}
    con = prices.connect()
    stores = optimizer.load_stores(enabled_only=False)
    fetched = {s["key"]: prices.last_fetch(con, s["key"]) for s in stores}
    return render_template("home.html", counts=counts, stores=stores, fetched=fetched,
                           n_receipts=len(receipts.list_receipts()), report=latest_report())


@app.post("/fetch")
def fetch():
    class A:  # reuse CLI logic
        store = None
        verbose = False
    rc = cmd_fetch(A)
    flash("המחירים עודכנו" if rc == 0 else "חלק מהחנויות נכשלו – ראה טרמינל")
    return redirect(url_for("home"))


@app.post("/compare")
def compare():
    statuses = tuple(request.form.getlist("status")) or ("core",)
    on = date.fromisoformat(request.form["date"]) if request.form.get("date") else None
    cat = catalog.load()
    res = optimizer.optimize(catalog.basket(cat, statuses), on)
    optimizer.save_report(res)
    return redirect(url_for("report"))


@app.get("/report")
def report():
    res = latest_report()
    if not res:
        flash("עדיין אין השוואה")
        return redirect(url_for("home"))
    stores = {s["key"]: s.get("name", s["key"]) for s in optimizer.load_stores(enabled_only=False)}
    return render_template("report.html", r=res, stores=stores)


@app.get("/catalog")
def catalog_view():
    cat = catalog.load()
    status = request.args.get("status")
    items = [p for p in cat["products"] if not status or p.get("status") == status]
    return render_template("catalog.html", items=items, status=status)


@app.post("/catalog/<pid>")
def catalog_update(pid):
    cat = catalog.load()
    p = catalog.by_id(cat).get(pid)
    if not p:
        return "not found", 404
    f = request.form
    if f.get("status") in STATUSES:
        p["status"], p["locked"] = f["status"], True
    if f.get("qty"):
        p.setdefault("need", {})["qty"] = float(f["qty"])
    if "notes" in f:
        p["notes"] = f["notes"]
    if f.get("match"):
        try:
            p["match"] = json.loads(f["match"])
        except json.JSONDecodeError:
            flash("כלל ההתאמה אינו JSON תקין")
    catalog.save(cat)
    return redirect(request.referrer or url_for("catalog_view"))


@app.route("/deals", methods=["GET", "POST"])
def deals():
    if request.method == "POST":
        try:
            config.save_json(config.DEALS_FILE, json.loads(request.form["body"]))
            flash("נשמר")
        except json.JSONDecodeError as e:
            flash(f"JSON שגוי: {e}")
        return redirect(url_for("deals"))
    body = json.dumps(config.load_json(config.DEALS_FILE, {"deals": []}), ensure_ascii=False, indent=2)
    return render_template("deals.html", body=body)


@app.get("/receipts")
def receipts_view():
    return render_template("receipts.html", rs=list(reversed(receipts.list_receipts())))


@app.get("/search")
def search():
    q = request.args.get("q", "")
    rows = prices.search(prices.connect(), q, limit=60) if q else []
    return render_template("search.html", q=q, rows=rows)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8765, debug=False)
