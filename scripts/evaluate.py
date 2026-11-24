"""Compare keyword vs BM25 vs semantic vs hybrid retrieval on labelled queries.

Each query in data/eval_queries.json lists the product *types* that are a
correct answer. A retrieved product counts as relevant if its type is in that list.

Metrics (all averaged over queries, higher is better):
  Hit@k    did at least one relevant product show up in the top k?
  MRR      1 / rank of the first relevant product (0 if none in top k)
  nDCG@k   rewards putting relevant products near the top
  P@k      fraction of the top k that is relevant

    python scripts/evaluate.py [--k 5]
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from spf import config  # noqa: E402
from spf.engine import Engine  # noqa: E402


def metrics(ranked_types: list[str], relevant: set[str], k: int) -> dict:
    rel = [1 if t in relevant else 0 for t in ranked_types[:k]]
    first = next((i for i, r in enumerate(rel) if r), None)
    dcg = sum(r / math.log2(i + 2) for i, r in enumerate(rel))
    # ideal: every slot relevant (each type has 2-4 products, so k<=5 is reachable for most)
    idcg = sum(1 / math.log2(i + 2) for i in range(k))
    return {
        "hit": 1.0 if first is not None else 0.0,
        "mrr": 1.0 / (first + 1) if first is not None else 0.0,
        "ndcg": dcg / idcg,
        "precision": sum(rel) / k,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args()
    k = args.k

    engine = Engine()
    queries = json.loads(config.EVAL_QUERIES.read_text())
    modes = ["keyword", "bm25", "semantic", "hybrid"]
    groups = {"all": queries,
              "keyword-style": [q for q in queries if q["style"] == "keyword"],
              "natural-language": [q for q in queries if q["style"] == "natural"]}

    per_query = {m: [] for m in modes}
    latency = {}
    for m in modes:
        t = time.perf_counter()
        for q in queries:
            hits = engine.search(q["query"], mode=m, k=k)
            types = [h.metadata.get("type_id") for h in hits]
            per_query[m].append(metrics(types, set(q["relevant"]), k))
        latency[m] = (time.perf_counter() - t) / len(queries) * 1000

    lines = [f"# Retrieval evaluation (k={k}, {len(queries)} queries, {len(engine.docs)} products)", ""]
    for gname, gq in groups.items():
        idx = [queries.index(q) for q in gq]
        lines += [f"## {gname} ({len(gq)} queries)", "",
                  f"| method | Hit@{k} | MRR | nDCG@{k} | P@{k} |", "|---|---|---|---|---|"]
        for m in modes:
            avg = {key: sum(per_query[m][i][key] for i in idx) / len(idx) for key in ["hit", "mrr", "ndcg", "precision"]}
            lines.append(f"| {m} | {avg['hit']:.2f} | {avg['mrr']:.2f} | {avg['ndcg']:.2f} | {avg['precision']:.2f} |")
        lines.append("")
    lines += ["## Average latency per query (ms, this machine)", "",
              "| method | ms |", "|---|---|"] + [f"| {m} | {latency[m]:.1f} |" for m in modes] + [""]

    # show where keyword lookup fails and semantic succeeds
    lines += ["## Examples where keyword lookup missed but semantic search found it", ""]
    for i, q in enumerate(queries):
        if per_query["keyword"][i]["hit"] == 0 and per_query["semantic"][i]["hit"] == 1:
            top = engine.search(q["query"], mode="semantic", k=1)[0].name
            lines.append(f"- \"{q['query']}\" -> {top}")
    lines.append("")
    lines += ["## Queries semantic search still misses (top 5)", ""]
    for i, q in enumerate(queries):
        if per_query["semantic"][i]["hit"] == 0:
            got = [h.name for h in engine.search(q['query'], mode='semantic', k=3)]
            lines.append(f"- \"{q['query']}\" wanted {q['relevant']}, got {got}")

    report = "\n".join(lines)
    print(report)
    out = config.ROOT / "results" / "eval_results.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(report + "\n")
    print(f"\nSaved -> {out}")


if __name__ == "__main__":
    main()
