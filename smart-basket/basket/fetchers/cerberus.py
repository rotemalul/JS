"""Cerberus portal https://url.publishedprices.co.il — used by many chains.

Each chain has a public username (no password) that the chain publishes by law, e.g.
  RamiLevi, yohananof, osherad, TivTaam, doralon, Keshet, SalachD, Stop_Market, freshmarket
Flow: GET /login (csrftoken) -> POST /login/user -> POST /file/json/dir (list) -> GET /file/d/<name>.

STATUS: written from the portal's known API but NOT yet verified from the dev sandbox
(network access was blocked there). Run `python -m basket fetch --store <key> -v` on your machine
and fix here if the portal changed.
"""
from __future__ import annotations

import re

from .base import FetchResult, Fetcher, parse_stores_xml

HOST = "https://url.publishedprices.co.il"


class CerberusFetcher(Fetcher):
    def _csrf(self, html_text: str) -> str:
        m = re.search(r'name="csrftoken"\s+content="([^"]+)"', html_text)
        if not m:
            raise RuntimeError("Cerberus: csrftoken not found (portal layout changed?)")
        return m.group(1)

    def _login(self, username: str, password: str = "") -> str:
        tok = self._csrf(self.get(f"{HOST}/login").text)
        r = self.s.post(f"{HOST}/login/user", timeout=self.timeout,
                        data={"username": username, "password": password, "csrftoken": tok, "r": ""})
        r.raise_for_status()
        return self._csrf(self.get(f"{HOST}/file").text)

    def _list(self, tok: str, search: str) -> list[str]:
        r = self.s.post(f"{HOST}/file/json/dir", timeout=self.timeout,
                        data={"iDisplayLength": 100000, "sSearch": search, "csrftoken": tok, "cd": "/"})
        r.raise_for_status()
        names = [row.get("fname") or row.get("name") for row in r.json().get("aaData", [])]
        return sorted([n for n in names if n], reverse=True)  # names end with YYYYMMDDHHMM -> newest first

    def _pick(self, names: list[str], kind: str, store_id: str) -> str | None:
        sid = str(store_id).zfill(3)
        for n in names:
            if n.lower().startswith(kind.lower()) and re.search(rf"-{sid}-\d{{8,}}", n):
                return n
        return None

    def fetch(self, store: dict) -> FetchResult:
        tok = self._login(store["username"], store.get("password", ""))
        names = self._list(tok, store.get("chain_id", ""))
        price = self._pick(names, "PriceFull", store["store_id"])
        if not price:
            raise RuntimeError(f"Cerberus: no PriceFull for {store['username']} store {store['store_id']}")
        promo = self._pick(names, "PromoFull", store["store_id"])
        return FetchResult(
            price_xml=self.download(f"{HOST}/file/d/{price}"),
            promo_xml=self.download(f"{HOST}/file/d/{promo}") if promo else None,
            source=price + (f" + {promo}" if promo else ""),
        )

    def list_stores(self, store: dict) -> list[dict]:
        tok = self._login(store["username"], store.get("password", ""))
        names = [n for n in self._list(tok, "Stores") if n.lower().startswith("stores")]
        if not names:
            return []
        return parse_stores_xml(self.download(f"{HOST}/file/d/{names[0]}"))
