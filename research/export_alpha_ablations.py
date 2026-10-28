"""Controlled dense/lexical alpha ablations on a single query/catalog set.

Do NOT tune alpha or abstention thresholds on official test labels.
Requires cached/pinned SentenceTransformer (or explicit authorized download).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from research.export_predictions import (
    dense_scores, load_catalog, load_queries, rank_ids, sha256_file, tfidf_scores,
)


def blend(dense: np.ndarray, sparse: np.ndarray, alpha: float) -> np.ndarray:
    if dense.shape != sparse.shape or not 0 <= alpha <= 1:
        raise ValueError("Invalid fusion dimensions or alpha")
    return alpha * np.clip((dense + 1) / 2, 0, 1) + (1 - alpha) * sparse


def run(queries: Path, catalog: Path, out_dir: Path, *,
        weights: list[float], model_name: str = "all-MiniLM-L6-v2",
        top_k: int = 5, threshold: float = 0.0,
        allow_download: bool = False, allow_test: bool = False) -> dict:
    if not weights or len(set(weights)) != len(weights) or any(not 0 <= w <= 1 for w in weights):
        raise ValueError("Weights must be unique and in [0,1]")
    if top_k < 1 or not 0 <= threshold <= 1:
        raise ValueError("Invalid top_k or threshold")
    ids, documents = load_catalog(catalog)
    qids, texts, split = load_queries(queries, allow_test=allow_test)
    sparse = tfidf_scores(documents, texts)
    dense = dense_scores(documents, texts, model_name, allow_download)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_paths = {}
    for alpha in weights:
        name = f"alpha_{int(round(alpha * 1000)):04d}"
        scores = blend(dense, sparse, alpha)
        output = out_dir / f"{name}.jsonl"
        with output.open("w", encoding="utf-8") as f:
            for qid, row in zip(qids, scores):
                f.write(json.dumps({"query_id": qid,
                     "predicted_disease_ids": rank_ids(row, ids, top_k, minimum_score=threshold)},
                     sort_keys=True) + "\n")
        output_paths[name] = output.name
    manifest = {
        "protocol": "medipower-m4-dense-sparse-ablation-v1",
        "split": split, "query_count": len(qids),
        "queries_sha256": sha256_file(queries), "catalog_sha256": sha256_file(catalog),
        "alpha_weights": weights, "model_name": model_name,
        "top_k": top_k, "threshold": threshold, "predictions": output_paths,
        "note": "Fusion alpha sweep is for development selection. Test results must not drive additional tuning.",
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--queries", type=Path, required=True)
    p.add_argument("--catalog", type=Path, default=Path("app/data/diseases.csv"))
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--weights", type=float, nargs="+", default=[0, .25, .5, .65, .75, 1])
    p.add_argument("--model-name", default="all-MiniLM-L6-v2")
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--threshold", type=float, default=0)
    p.add_argument("--allow-model-download", action="store_true")
    p.add_argument("--allow-test", action="store_true")
    a = p.parse_args()
    print(json.dumps(run(a.queries, a.catalog, a.out_dir, weights=a.weights, model_name=a.model_name,
          top_k=a.top_k, threshold=a.threshold, allow_download=a.allow_model_download,
          allow_test=a.allow_test), indent=2))


if __name__ == "__main__":
    main()
