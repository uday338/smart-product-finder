"""Step 3: store the vectors in a persistent Chroma collection.

Chroma builds an HNSW index (approximate nearest neighbour graph) over the
vectors, so a search is roughly O(log n) instead of comparing the query with
every product. We use cosine distance, the usual choice for sentence embeddings.
"""
from __future__ import annotations

import shutil

from langchain_chroma import Chroma
from langchain_core.documents import Document

from . import config
from .embeddings import get_embeddings


def build_vectorstore(chunks: list[Document], reset: bool = True) -> Chroma:
    if reset and config.CHROMA_DIR.exists():
        shutil.rmtree(config.CHROMA_DIR)
    store = Chroma(
        collection_name=config.COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=str(config.CHROMA_DIR),
        collection_metadata={"hnsw:space": "cosine"},
    )
    ids = [c.metadata["chunk_id"] for c in chunks]
    # add in batches so big catalogs don't blow memory
    for i in range(0, len(chunks), 256):
        store.add_documents(chunks[i : i + 256], ids=ids[i : i + 256])
    return store


def load_vectorstore() -> Chroma:
    if not config.CHROMA_DIR.exists():
        raise FileNotFoundError(
            f"No index at {config.CHROMA_DIR}. Run `python scripts/build_index.py` first."
        )
    return Chroma(
        collection_name=config.COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=str(config.CHROMA_DIR),
    )
