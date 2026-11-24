"""Pull structured filters out of a free-text query.

"wireless earbuds under ₹2000 rated 4+"  ->
    text   = "wireless earbuds"
    filter = {"$and": [{"price": {"$lte": 2000}}, {"rating": {"$gte": 4}}]}

Embeddings are bad at numbers ("under 2000" and "over 2000" look almost the
same to them), so we handle price/rating with exact metadata filters and send
only the meaning part of the query to the vector search.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_MONEY = r"(?:₹|rs\.?|inr)?\s*(\d[\d,]*(?:\.\d+)?)\s*(?:k\b)?"
_MAX_PRICE = re.compile(rf"\b(?:under|below|less than|cheaper than|within|upto|up to|max|<)\s*{_MONEY}", re.I)
_MIN_PRICE = re.compile(rf"\b(?:over|above|more than|at least|min|>)\s*{_MONEY}", re.I)
_RANGE = re.compile(rf"\bbetween\s*{_MONEY}\s*(?:and|-|to)\s*{_MONEY}", re.I)
_RATING = re.compile(r"\b(?:rated|rating)\s*(?:above|over|at least)?\s*(\d(?:\.\d)?)\s*\+?(?:\s*stars?)?", re.I)


@dataclass
class ParsedQuery:
    text: str
    min_price: float | None = None
    max_price: float | None = None
    min_rating: float | None = None
    filters: list = field(default_factory=list)

    @property
    def where(self) -> dict | None:
        """Chroma `where` filter, or None if no filters."""
        if not self.filters:
            return None
        return self.filters[0] if len(self.filters) == 1 else {"$and": self.filters}

    def matches(self, meta: dict) -> bool:
        """Same filter in plain Python (used by the keyword/BM25 baselines)."""
        p, r = meta.get("price", -1), meta.get("rating", -1)
        if self.max_price is not None and not (0 <= p <= self.max_price):
            return False
        if self.min_price is not None and p < self.min_price:
            return False
        if self.min_rating is not None and r < self.min_rating:
            return False
        return True


def _num(s: str, whole_match: str) -> float:
    v = float(s.replace(",", ""))
    if re.search(r"\d\s*k\b", whole_match, re.I):
        v *= 1000
    return v


def parse_query(q: str) -> ParsedQuery:
    text = q
    pq = ParsedQuery(text=q)

    if m := _RANGE.search(text):
        pq.min_price, pq.max_price = _num(m.group(1), m.group(0)), _num(m.group(2), m.group(0))
        text = text.replace(m.group(0), " ")
    else:
        if m := _MAX_PRICE.search(text):
            pq.max_price = _num(m.group(1), m.group(0))
            text = text.replace(m.group(0), " ")
        if m := _MIN_PRICE.search(text):
            pq.min_price = _num(m.group(1), m.group(0))
            text = text.replace(m.group(0), " ")
    if m := _RATING.search(text):
        pq.min_rating = float(m.group(1))
        text = text.replace(m.group(0), " ")

    if pq.max_price is not None:
        pq.filters += [{"price": {"$lte": pq.max_price}}, {"price": {"$gte": 0}}]
    if pq.min_price is not None:
        pq.filters.append({"price": {"$gte": pq.min_price}})
    if pq.min_rating is not None:
        pq.filters.append({"rating": {"$gte": pq.min_rating}})

    text = re.sub(r"\s+", " ", re.sub(r"\b(rupees|rs|inr)\b", " ", text, flags=re.I)).strip(" ,.-")
    pq.text = text or q
    return pq
