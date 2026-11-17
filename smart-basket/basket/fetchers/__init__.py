"""Fetchers download the official price-transparency files of each chain.

Each fetcher implements:
    fetch(store: dict) -> FetchResult      (latest PriceFull + PromoFull for one branch)
    list_stores(store: dict) -> list[dict] (branch directory, used to find store IDs)

`store` is one entry of data/stores.json.
"""
from __future__ import annotations

from .base import FetchResult, Fetcher
from .cerberus import CerberusFetcher
from .laib import LaibFetcher
from .shufersal import ShufersalFetcher

FETCHERS: dict[str, type[Fetcher]] = {
    "shufersal": ShufersalFetcher,
    "cerberus": CerberusFetcher,  # url.publishedprices.co.il: Rami Levy, Yochananof, Osher Ad, Tiv Taam...
    "laib": LaibFetcher,          # laibcatalog.co.il: Victory, Mega Market...
}


def get_fetcher(store: dict) -> Fetcher:
    kind = store.get("source")
    if kind not in FETCHERS:
        raise ValueError(f"Unknown source '{kind}' for store {store.get('key')}. Known: {list(FETCHERS)}")
    return FETCHERS[kind]()


__all__ = ["FetchResult", "Fetcher", "get_fetcher", "FETCHERS"]
