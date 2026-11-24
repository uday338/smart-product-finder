"""Build the vector index:  CSV -> clean -> chunk -> embed -> Chroma.

    python scripts/build_index.py [--csv path/to/products.csv]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from spf import config  # noqa: E402
from spf.ingest import chunk_documents, clean_dataframe, load_raw, to_documents  # noqa: E402
from spf.vectorstore import build_vectorstore  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(config.DATA_CSV))
    args = ap.parse_args()

    raw = load_raw(args.csv)
    df = clean_dataframe(raw)
    print(f"Loaded {len(raw)} raw rows -> {len(df)} clean products "
          f"({len(raw) - len(df)} duplicates / broken rows dropped)")
    print(f"Prices parsed: {df['price'].notna().sum()}/{len(df)}")

    docs = to_documents(df)
    chunks = chunk_documents(docs)
    print(f"{len(docs)} documents -> {len(chunks)} chunks (chunk_size={config.CHUNK_SIZE})")

    t = time.time()
    store = build_vectorstore(chunks)
    print(f"Embedded + indexed {store._collection.count()} chunks in {time.time() - t:.1f}s "
          f"-> {config.CHROMA_DIR}")


if __name__ == "__main__":
    main()
