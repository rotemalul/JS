from __future__ import annotations

import re
import time
from dataclasses import dataclass

import requests

from ..prices import open_payload

UA = "Mozilla/5.0 (X11; Linux x86_64) smart-basket/0.1 (personal price comparison)"


@dataclass
class FetchResult:
    price_xml: bytes
    promo_xml: bytes | None
    source: str  # file name(s), for the log


class Fetcher:
    timeout = 60

    def __init__(self) -> None:
        self.s = requests.Session()
        self.s.headers["User-Agent"] = UA

    def get(self, url: str, **kw) -> requests.Response:
        last = None
        for attempt in range(3):
            try:
                r = self.s.get(url, timeout=self.timeout, **kw)
                r.raise_for_status()
                return r
            except requests.RequestException as e:  # network hiccups are common on these sites
                last = e
                time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"GET {url} failed: {last}")

    def download(self, url: str) -> bytes:
        return open_payload(self.get(url).content)

    def fetch(self, store: dict) -> FetchResult:  # pragma: no cover - interface
        raise NotImplementedError

    def list_stores(self, store: dict) -> list[dict]:  # pragma: no cover - interface
        raise NotImplementedError


def parse_stores_xml(xml: bytes) -> list[dict]:
    """Generic Stores*.xml parser -> [{store_id, name, city, address}]."""
    text = xml.decode("utf-8-sig", errors="replace")
    out = []
    for block in re.findall(r"<store>(.*?)</store>", text, flags=re.S | re.I):
        def g(tag: str) -> str:
            m = re.search(rf"<{tag}>(.*?)</{tag}>", block, flags=re.S | re.I)
            return (m.group(1).strip() if m else "")
        out.append({"store_id": g("StoreID") or g("StoreId"), "name": g("StoreName"),
                    "city": g("City"), "address": g("Address"), "type": g("StoreType")})
    return out
