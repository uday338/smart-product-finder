"""Ask the RAG pipeline from the terminal.

    python scripts/ask.py "something to keep my coffee hot under 1000"
    python scripts/ask.py --mode bm25 "yoga mat"        # just search, no LLM
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from spf.engine import Engine  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--mode", choices=["keyword", "bm25", "semantic", "hybrid"],
                    help="only run retrieval with this method (skip the LLM)")
    ap.add_argument("-k", type=int, default=5)
    args = ap.parse_args()

    engine = Engine()
    if args.mode:
        for i, h in enumerate(engine.search(args.question, mode=args.mode, k=args.k), 1):
            print(f"{i}. {h.name:45s} ₹{h.metadata['price']:<8.0f} score={h.score:.3f}")
        return
    out = engine.ask(args.question)
    print("Retrieved:")
    for h in out["hits"]:
        print(f"  - {h.name} (₹{h.metadata['price']:.0f}, score {h.score:.3f})")
    print("\nAnswer:\n" + out["answer"])


if __name__ == "__main__":
    main()
