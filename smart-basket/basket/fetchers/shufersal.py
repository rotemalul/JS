"""Shufersal: https://prices.shufersal.co.il  (verified working Nov 2026).

catID: 2 = PriceFull, 4 = PromoFull, 5 = Stores. Shufersal ONLINE is store 413.
The listing returns signed Azure-blob links, newest first.
"""
from __future__ import annotations

import html
import re

from .base import FetchResult, Fetcher, parse_stores_xml

BASE = "https://prices.shufersal.co.il/FileObject/UpdateCategory?catID={cat}&storeId={store}&page=1"


class ShufersalFetcher(Fetcher):
    def _latest(self, cat: int, store_id: str) -> tuple[str, str] | None:
        page = self.get(BASE.format(cat=cat, store=int(store_id))).text
        links = re.findall(r'href="(https://pricesprodpublic[^"]+)"', page)
        if not links:
            return None
        url = html.unescape(links[0])
        name = url.split("?")[0].rsplit("/", 1)[-1]
        return url, name

    def fetch(self, store: dict) -> FetchResult:
        sid = store["store_id"]
        price = self._latest(2, sid)
        if not price:
            raise RuntimeError(f"No PriceFull file for Shufersal store {sid}")
        promo = self._latest(4, sid)
        return FetchResult(
            price_xml=self.download(price[0]),
            promo_xml=self.download(promo[0]) if promo else None,
            source=price[1] + (f" + {promo[1]}" if promo else ""),
        )

    def list_stores(self, store: dict) -> list[dict]:
        latest = self._latest(5, "0")
        if not latest:
            return []
        return parse_stores_xml(self.download(latest[0]))
