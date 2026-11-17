"""Hebrew product-name normalization and package-size parsing.

All sizes are converted to a base unit:
    g   – grams (ק"ג -> 1000 g)
    ml  – milliliters (ליטר -> 1000 ml)
    unit – count of units (יח', יחידות, rolls, eggs ...)
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_PUNCT = re.compile(r"[\"'`׳״,.\-_/\\()\[\]*+:;!?|]")
_SPACES = re.compile(r"\s+")


def norm_text(s: str | None) -> str:
    """Lowercase, strip punctuation/quotes, collapse spaces. Keeps % and digits."""
    if not s:
        return ""
    s = s.replace("‏", "").replace("‎", "").replace("﻿", "")
    s = _PUNCT.sub(" ", s.lower())
    return _SPACES.sub(" ", s).strip()


def tokens(s: str | None) -> list[str]:
    return norm_text(s).split()


@dataclass(frozen=True)
class Size:
    qty: float
    unit: str  # g | ml | unit

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        if self.unit == "g" and self.qty >= 1000:
            return f"{self.qty / 1000:g} ק\"ג"
        if self.unit == "ml" and self.qty >= 1000:
            return f"{self.qty / 1000:g} ליטר"
        names = {"g": "גרם", "ml": "מ\"ל", "unit": "יח'"}
        return f"{self.qty:g} {names[self.unit]}"


# unit word -> (base unit, multiplier)
_UNIT_WORDS: list[tuple[str, str, float]] = [
    (r"ק\"?ג|קג|קילו(?:גרם)?|kg", "g", 1000.0),
    (r"גר(?:ם|'|׳)?|ג'|ג׳|ג|gr|g", "g", 1.0),
    (r"מ\"?ל|מל|מיליליטר|ml", "ml", 1.0),
    (r"ליטר|ל'|ל׳|ל|lit|l", "ml", 1000.0),
    (r"יח(?:ידות|ידה|'|׳)?|יחי|גלילים|זוגות|ביצים|שקיות|pcs|units?", "unit", 1.0),
]

_NUM = r"(\d+(?:\.\d+)?)"


def parse_size(text: str | None) -> Size | None:
    """Best-effort extraction of a package size from free text.

    Handles: "500 גרם", "1.5 ליטר", "1 ק\"ג", "750מ\"ל", "6*1 ליטר", "12 יח'".
    For multipacks "6*1 ליטר" / "6 X 200 מ\"ל" returns the total.
    """
    if not text:
        return None
    t = text.replace("״", '"').replace("׳", "'").lower()
    for pattern, base, mult in _UNIT_WORDS:
        # multipack: 6*200 מ"ל  |  6 x 200 מל
        m = re.search(rf"(\d+)\s*[x\*×]\s*{_NUM}\s*(?:{pattern})(?![א-תa-z])", t)
        if m:
            return Size(float(m.group(1)) * float(m.group(2)) * mult, base)
        m = re.search(rf"{_NUM}\s*(?:{pattern})(?![א-תa-z])", t)
        if m:
            return Size(float(m.group(1)) * mult, base)
    return None


_XML_UNITS = {
    "גרם": ("g", 1.0), "גר": ("g", 1.0), "100 גרם": ("g", 1.0),
    "קילוגרם": ("g", 1000.0), "קילו": ("g", 1000.0), "ק\"ג": ("g", 1000.0), "קג": ("g", 1000.0),
    "מיליליטר": ("ml", 1.0), "מ\"ל": ("ml", 1.0), "מל": ("ml", 1.0), "100 מ\"ל": ("ml", 1.0),
    "ליטר": ("ml", 1000.0), "ליטרים": ("ml", 1000.0),
    "יחידה": ("unit", 1.0), "יחידות": ("unit", 1.0), "יח'": ("unit", 1.0),
}


def size_from_feed(quantity: str | None, unit_of_measure: str | None, name: str | None) -> Size | None:
    """Size from the price-transparency XML fields, falling back to the item name."""
    try:
        q = float(quantity) if quantity not in (None, "") else None
    except ValueError:
        q = None
    u = norm_unit(unit_of_measure)
    if q and q > 0 and u in _XML_UNITS:
        base, mult = _XML_UNITS[u]
        return Size(q * mult, base)
    return parse_size(name)


def norm_unit(u: str | None) -> str:
    if not u:
        return ""
    return u.replace("״", '"').replace("׳", "'").strip()


def unit_price(price: float, size: Size | None) -> float | None:
    """Price per 1 kg / 1 liter / 1 unit."""
    if not size or size.qty <= 0:
        return None
    if size.unit in ("g", "ml"):
        return price / size.qty * 1000.0
    return price / size.qty
