"""One object that loads everything once and is shared by the API, CLI and evaluation."""
from __future__ import annotations

from functools import cached_property

from . import config
from .ingest import chunk_documents, load_products
from .search import BM25Searcher, HybridSearcher, KeywordSearcher, SemanticSearcher
from .vectorstore import load_vectorstore


class Engine:
    def __init__(self, csv_path=config.DATA_CSV):
        self.df, self.docs = load_products(csv_path)
        self.chunks = chunk_documents(self.docs)

    @cached_property
    def store(self):
        return load_vectorstore()

    @cached_property
    def searchers(self) -> dict:
        kw = KeywordSearcher(self.chunks)
        bm25 = BM25Searcher(self.chunks)
        sem = SemanticSearcher(self.store)
        return {"keyword": kw, "bm25": bm25, "semantic": sem, "hybrid": HybridSearcher(sem, bm25)}

    def search(self, query: str, mode: str = "semantic", k: int = config.TOP_K):
        if mode not in self.searchers:
            raise ValueError(f"mode must be one of {list(self.searchers)}")
        return self.searchers[mode].search(query, k=k)

    @cached_property
    def rag_chain(self):
        from .rag import build_rag_chain

        # Semantic search had the best MRR/nDCG in results/eval_results.md, so the
        # RAG chain uses it, dropping weak matches so the LLM isn't fed junk.
        name = config.RAG_RETRIEVER
        if name == "semantic":
            retriever = SemanticSearcher(self.store, min_score=config.MIN_SCORE)
        else:
            retriever = self.searchers[name]
        return build_rag_chain(retriever)

    def ask(self, question: str) -> dict:
        return self.rag_chain.invoke({"question": question})
