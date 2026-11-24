"""Step 2: text -> vectors.

Default is all-MiniLM-L6-v2 (384-dim sentence embeddings) run through
onnxruntime. Same model as sentence-transformers' MiniLM, but no PyTorch, so
it installs fast and runs on any laptop CPU. First run downloads ~80 MB.
"""
from __future__ import annotations

from functools import lru_cache

from langchain_core.embeddings import Embeddings

from . import config


class OnnxMiniLMEmbeddings(Embeddings):
    """LangChain wrapper around Chroma's bundled ONNX MiniLM model."""

    def __init__(self) -> None:
        from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

        self._fn = ONNXMiniLM_L6_V2()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [list(map(float, v)) for v in self._fn(texts)]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


@lru_cache(maxsize=1)
def get_embeddings() -> Embeddings:
    kind = config.EMBEDDINGS.lower()
    if kind == "onnx":
        return OnnxMiniLMEmbeddings()
    if kind == "hf":
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(model_name=config.HF_MODEL, encode_kwargs={"normalize_embeddings": True})
    if kind == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model="text-embedding-3-small")
    raise ValueError(f"Unknown SPF_EMBEDDINGS={kind!r} (use onnx, hf or openai)")
