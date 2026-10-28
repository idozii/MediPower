"""M4 abstention ablation: require lexical evidence for dense/hybrid retrieval.

An uncalibrated zero-overlap lexical gate is NOT a clinical safety system.
This intentionally retains the ungated baselines elsewhere for comparisons.
Use DEVELOPMENT only; do not tune on test or the tiny illustrative negatives.

python -m research.export_abstention_ablations --queries research/examples/dev_queries.jsonl \
  --out-dir research/outputs/abstention-dev
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from research.export_predictions import (
    dense_scores, load_catalog, load_queries, rank_ids, sha256_file, tfidf_scores,
)


def gated_rankings(sparse: np.ndarray, dense: np.ndarray, catalog_ids: list[str],
                   *, dense_weight: float = 0.65, min_lexical: float = 0.0,
                   top_k: int = 5) -> dict[str, list[list[str]]]:
    if sparse.shape != dense.shape or sparse.ndim != 2:
        raise ValueError("Expected matching two-dimensional sparse and dense matrices")
    if sparse.shape[1] != len(catalog_ids):
        raise ValueError("Catalog IDs mismatch")
    if not 0 <= dense_weight <= 1 or not 0 <= min_lexical <= 1 or top_k < 1:
        raise ValueError("Invalid alpha, lexical threshold or top_k")
    if not np.isfinite(sparse).all() or not np.isfinite(dense).all():
        raise ValueError("Non-finite retrieval values")
    scaled_dense = np.clip((dense + 1) / 2, 0, 1)
    hybrid = dense_weight * scaled_dense + (1 - dense_weight) * sparse
    result = {"dense_lexical_gate": [], "hybrid_lexical_gate": []}
    for i in range(sparse.shape[0]):
        # An explicit lexical signal, independent of the shifted dense score.
        matches_evidence = bool(float(np.max(sparse[i])) > min_lexical)
        result["dense_lexical_gate"].append(
            rank_ids(scaled_dense[i], catalog_ids, top_k) if matches_evidence else [])
        result["hybrid_lexical_gate"].append(
            rank_ids(hybrid[i], catalog_ids, top_k) if matches_evidence else [])
    return result


def run(queries: Path, catalog: Path, out_dir: Path, *,
        dense_model: str = "all-MiniLM-L6-v2", dense_weight: float = .65,
        min_lexical: float = 0, top_k: int = 5,
        allow_download: bool = False, allow_test: bool = False) -> dict:
    ids, documents = load_catalog(catalog)
    query_ids, texts, split = load_queries(queries, allow_test=allow_test)
    sparse = tfidf_scores(documents, texts)
    dense = dense_scores(documents, texts, dense_model, allow_download)
    values = gated_rankings(sparse, dense, ids, dense_weight=dense_weight,
                            min_lexical=min_lexical, top_k=top_k)
    out_dir.mkdir(parents=True, exist_ok=True)
    gated_counts = {}
    for name, ranks in values.items():
        with (out_dir / f"{name}.jsonl").open("w", encoding="utf-8") as f:
            for qid, predicted in zip(query_ids, ranks):
                f.write(json.dumps({"query_id": qid, "predicted_disease_ids": predicted},
                                   sort_keys=True) + "\n")
        gated_counts[name] = sum(not p for p in ranks)
    manifest = {
        "protocol": "medipower-m4-development-lexical-gate-ablation-v1",
        "split": split, "query_count": len(query_ids),
        "queries_sha256": sha256_file(queries),
        "catalog_sha256": sha256_file(catalog),
        "models": list(values), "top_k": top_k,
        "dense_model": dense_model, "dense_weight": dense_weight,
        "min_lexical": min_lexical,
        "abstained_queries_per_model": gated_counts,
        "warning": "Experimental lexical-overlap gate; NOT calibrated OOD detection or clinical abstention. It can reject legitimate paraphrases, so evaluate positive abstention and source shift.",
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--queries", type=Path, required=True)
    p.add_argument("--catalog", type=Path, default=Path("app/data/diseases.csv"))
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--dense-model", default="all-MiniLM-L6-v2")
    p.add_argument("--dense-weight", type=float, default=.65)
    p.add_argument("--min-lexical", type=float, default=0)
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--allow-model-download", action="store_true")
    p.add_argument("--allow-test", action="store_true")
    a = p.parse_args()
    print(json.dumps(run(a.queries, a.catalog, a.out_dir,
                         dense_model=a.dense_model, dense_weight=a.dense_weight,
                         min_lexical=a.min_lexical, top_k=a.top_k,
                         allow_download=a.allow_model_download,
                         allow_test=a.allow_test), indent=2))


if __name__ == "__main__":
    main()
