"""laibcatalog.co.il — Victory (chain 7290696200003), Mega Market and others.

STATUS: NOT verified (the host was unreachable from the dev sandbox). The page lists
files as links; we pick the newest link whose file name contains the chain id, the
store id and PriceFull / PromoFull. If the site changed, adjust `_links` below.

Note: "שלישי שוק" in Victory Netivot is a physical-store event and is entered by hand
in data/manual_deals.json — it will not appear in these files.
"""
from __future__ import annotations

import html
import re
from urllib.parse import urljoin

from .base import FetchResult, Fetcher, parse_stores_xml

HOST = "https://laibcatalog.co.il/"


class LaibFetcher(Fetcher):
    def _links(self) -> list[str]:
        page = self.get(HOST).text
        hrefs = [html.unescape(h) for h in re.findall(r'href="([^"]+)"', page)]
        return [urljoin(HOST, h.replace("\\", "/")) for h in hrefs if re.search(r"\.(gz|zip|xml)$", h, re.I)]

    def _pick(self, links: list[str], kind: str, chain_id: str, store_id: str | None) -> str | None:
        cands = [l for l in links if kind.lower() in l.lower() and chain_id in l]
        if store_id is not None:
            sid = str(store_id).zfill(3)
            cands = [l for l in cands if re.search(rf"-{sid}-\d{{8,}}", l)]
        return sorted(cands, key=lambda l: l.rsplit("/", 1)[-1], reverse=True)[0] if cands else None

    def fetch(self, store: dict) -> FetchResult:
        links = self._links()
        price = self._pick(links, "PriceFull", store["chain_id"], store["store_id"])
        if not price:
            raise RuntimeError(f"laib: no PriceFull for chain {store['chain_id']} store {store['store_id']}")
        promo = self._pick(links, "PromoFull", store["chain_id"], store["store_id"])
        return FetchResult(self.download(price), self.download(promo) if promo else None,
                           price.rsplit("/", 1)[-1])

    def list_stores(self, store: dict) -> list[dict]:
        link = self._pick(self._links(), "Stores", store["chain_id"], None)
        return parse_stores_xml(self.download(link)) if link else []
