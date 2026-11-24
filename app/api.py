"""FastAPI server + a tiny web UI.

    uvicorn app.api:app --reload      ->  http://127.0.0.1:8000

Endpoints
  GET  /api/search?q=...&mode=semantic&k=5   retrieval only (keyword|bm25|semantic|hybrid)
  GET  /api/compare?q=...                    all four methods side by side
  POST /api/ask   {"question": "..."}         full RAG: retrieve + LLM answer
  GET  /api/health
"""
from __future__ import annotations

import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from spf import config
from spf.engine import Engine
from spf.query_parser import parse_query

app = FastAPI(title="Smart Product Finder", version="1.0.0")
_engine: Engine | None = None
STATIC = Path(__file__).parent / "static"


def engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = Engine()
        _ = _engine.searchers  # load index + warm up the embedding model once
        _engine.search("warm up")
    return _engine


class AskRequest(BaseModel):
    question: str


@app.on_event("startup")
def _startup():
    engine()


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health():
    e = engine()
    return {"status": "ok", "products": len(e.docs), "chunks": e.store._collection.count(),
            "embeddings": config.EMBEDDINGS, "llm": config.LLM_PROVIDER}


@app.get("/api/search")
def search(q: str = Query(..., min_length=1), mode: str = "semantic", k: int = Query(5, ge=1, le=20)):
    try:
        t = time.perf_counter()
        hits = engine().search(q, mode=mode, k=k)
    except ValueError as err:
        raise HTTPException(400, str(err))
    pq = parse_query(q)
    return {"query": q, "semantic_text": pq.text, "filters": pq.where, "mode": mode,
            "ms": round((time.perf_counter() - t) * 1000, 1), "results": [h.to_dict() for h in hits]}


@app.get("/api/compare")
def compare(q: str = Query(..., min_length=1), k: int = Query(5, ge=1, le=10)):
    return {m: [h.to_dict() for h in engine().search(q, mode=m, k=k)]
            for m in ["keyword", "bm25", "semantic", "hybrid"]}


@app.post("/api/ask")
def ask(req: AskRequest):
    if not req.question.strip():
        raise HTTPException(400, "question is empty")
    t = time.perf_counter()
    out = engine().ask(req.question)
    return {"question": req.question, "answer": out["answer"], "llm": config.LLM_PROVIDER,
            "ms": round((time.perf_counter() - t) * 1000, 1), "sources": [h.to_dict() for h in out["hits"]]}
