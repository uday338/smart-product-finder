"""Four ways to search the catalog, all with the same interface:

    searcher.search(query, k) -> list[Hit]

* KeywordSearcher  - the "naive keyword lookup": count how many query words
                     appear in the product text. What a basic SQL LIKE does.
* BM25Searcher     - proper lexical search (what Elasticsearch uses by default).
* SemanticSearcher - embed the query, nearest neighbours in Chroma.
* HybridSearcher   - BM25 + semantic merged with Reciprocal Rank Fusion.

Having all four lets `scripts/evaluate.py` prove (with numbers) that the
vector search beats keyword lookups.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from .query_parser import parse_query

_STOP = set(
    "a an the and or for to of in on at my i me is it with without that this be can can't cannot "
    "want need some something all from when by so too very are am do does your you get after".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP]


@dataclass
class Hit:
    id: str
    name: str
    score: float
    metadata: dict
    text: str

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "score": round(self.score, 4),
                "price": self.metadata.get("price"), "rating": self.metadata.get("rating"),
                "brand": self.metadata.get("brand"), "category": self.metadata.get("category"),
                "text": self.text}


def _dedupe(hits: list[Hit], k: int) -> list[Hit]:
    """Several chunks of one product may match; keep the best per product."""
    seen, out = set(), []
    for h in hits:
        if h.id not in seen:
            seen.add(h.id)
            out.append(h)
        if len(out) == k:
            break
    return out


class KeywordSearcher:
    name = "keyword"

    def __init__(self, docs: list[Document]):
        self.docs = docs
        self.tokens = [set(tokenize(d.page_content)) for d in docs]

    def search(self, query: str, k: int = 5) -> list[Hit]:
        pq = parse_query(query)
        q = set(tokenize(pq.text))
        scored = []
        for d, toks in zip(self.docs, self.tokens):
            overlap = len(q & toks)
            if overlap and pq.matches(d.metadata):
                scored.append(Hit(d.metadata["id"], d.metadata["name"], overlap / len(q), d.metadata, d.page_content))
        scored.sort(key=lambda h: -h.score)
        return _dedupe(scored, k)


class BM25Searcher:
    name = "bm25"

    def __init__(self, docs: list[Document]):
        self.docs = docs
        self.bm25 = BM25Okapi([tokenize(d.page_content) for d in docs])

    def search(self, query: str, k: int = 5) -> list[Hit]:
        pq = parse_query(query)
        scores = self.bm25.get_scores(tokenize(pq.text))
        order = sorted(range(len(self.docs)), key=lambda i: -scores[i])
        hits = [
            Hit(self.docs[i].metadata["id"], self.docs[i].metadata["name"], float(scores[i]),
                self.docs[i].metadata, self.docs[i].page_content)
            for i in order if scores[i] > 0 and pq.matches(self.docs[i].metadata)
        ]
        return _dedupe(hits, k)


class SemanticSearcher:
    name = "semantic"

    def __init__(self, store, min_score: float = 0.0):
        self.store = store  # a LangChain Chroma vector store
        self.min_score = min_score  # drop weak matches (used by the RAG chain)

    def search(self, query: str, k: int = 5) -> list[Hit]:
        pq = parse_query(query)
        # fetch extra because several chunks may belong to the same product
        results = self.store.similarity_search_with_score(pq.text, k=k * 3, filter=pq.where)
        hits = [
            # Chroma returns cosine *distance*; 1 - distance = cosine similarity
            Hit(d.metadata["id"], d.metadata["name"], 1.0 - float(dist), d.metadata, d.page_content)
            for d, dist in results
        ]
        hits = [h for h in hits if h.score >= self.min_score]
        return _dedupe(hits, k)


class HybridSearcher:
    """Reciprocal Rank Fusion: score = sum over searchers of 1 / (60 + rank).
    Doesn't care that BM25 scores and cosine scores are on different scales."""

    name = "hybrid"

    def __init__(self, *searchers, rrf_k: int = 60):
        self.searchers = searchers
        self.rrf_k = rrf_k

    def search(self, query: str, k: int = 5) -> list[Hit]:
        fused: dict[str, float] = {}
        best: dict[str, Hit] = {}
        for s in self.searchers:
            for rank, h in enumerate(s.search(query, k=k * 4)):
                fused[h.id] = fused.get(h.id, 0.0) + 1.0 / (self.rrf_k + rank + 1)
                best.setdefault(h.id, h)
        ranked = sorted(fused, key=lambda pid: -fused[pid])[:k]
        return [Hit(pid, best[pid].name, fused[pid], best[pid].metadata, best[pid].text) for pid in ranked]
