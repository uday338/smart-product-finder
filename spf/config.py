"""All settings in one place. Override any of them with environment variables
(or a .env file in the project root)."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:  # optional: load .env if python-dotenv is installed
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

DATA_CSV = Path(os.getenv("SPF_DATA_CSV", ROOT / "data" / "products_raw.csv"))
EVAL_QUERIES = ROOT / "data" / "eval_queries.json"
CHROMA_DIR = Path(os.getenv("SPF_CHROMA_DIR", ROOT / ".chroma"))
COLLECTION = os.getenv("SPF_COLLECTION", "products")

# Embeddings: "onnx" (default, MiniLM-L6-v2 via onnxruntime, no torch, no key)
#             "hf"   (any sentence-transformers model, needs langchain-huggingface)
#             "openai" (text-embedding-3-small, needs OPENAI_API_KEY)
EMBEDDINGS = os.getenv("SPF_EMBEDDINGS", "onnx")
HF_MODEL = os.getenv("SPF_HF_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# LLM for the answer step: "none" (no LLM, template answer), "anthropic",
# "openai" or "ollama". Pick the model with SPF_LLM_MODEL.
LLM_PROVIDER = os.getenv("SPF_LLM", "none")
LLM_MODEL = os.getenv("SPF_LLM_MODEL", "")

CHUNK_SIZE = int(os.getenv("SPF_CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("SPF_CHUNK_OVERLAP", "50"))
TOP_K = int(os.getenv("SPF_TOP_K", "5"))

# Which retriever feeds the LLM (semantic | hybrid | bm25 | keyword) and the
# minimum cosine similarity a semantic hit needs to be passed to the LLM.
RAG_RETRIEVER = os.getenv("SPF_RAG_RETRIEVER", "semantic")
MIN_SCORE = float(os.getenv("SPF_MIN_SCORE", "0.25"))
