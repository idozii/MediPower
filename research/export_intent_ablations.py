"""M9: prototype-similarity *research ablation* for query-task intent.

Zero-shot SentenceTransformer prompt comparison is an unvalidated heuristic,
NOT an intent classifier trained on independently annotated patient data.
The prompts were designed AFTER examining M8 stress results; M8 is therefore
development-only debugging evidence, never a holdout or safety assessment.

Local example (no gold labels ever read here):
  python -m research.export_intent_ablations \
    --queries research/examples/abstention_stress_v1_queries.jsonl \
    --out-dir research/outputs/m9-intent-dev
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from research.export_predictions import (
    dense_scores, load_catalog, load_queries, rank_ids, sha256_file, tfidf_scores,
)

# General-task prototypes rather than per-disease trigger-word rules.
# This prompt set is FROZEN for M9 diagnosis of known development failures.
# The outcome of M8 must not be used to claim independent evaluation.
SYMPTOM_INTENT_PROTOTYPES = (
    "I am describing physical symptoms that a person is currently experiencing and asking what conditions could be related.",
    "I am experiencing a health concern with symptoms and want to find information about possible illnesses.",
    "A person reports a new bodily symptom or health problem and is asking for symptom-related condition information.",
)
OTHER_TASK_PROTOTYPES = (
    "I am asking for assistance with a task, not reporting symptoms experienced by a person.",
    "I want help with writing, software, studying, business or another everyday task rather than understanding a health problem.",
    "This request discusses a subject or term without seeking medical information about experienced symptoms.",
)


def intent_decision(intent_similarities: np.ndarray, *,
                    positive_prototype_count: int = len(SYMPTOM_INTENT_PROTOTYPES),
                    margin: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """Return acceptance and semantic margin, without model or label dependence."""
    scores = np.asarray(intent_similarities, dtype=np.float64)
    if scores.ndim != 2 or positive_prototype_count < 1 or positive_prototype_count >= scores.shape[1]:
        raise ValueError("Expected rows of similarities with both positive and negative prototypes")
    if not np.isfinite(scores).all() or not 0 <= margin <= 1:
        raise ValueError("Invalid cosine similarities or intent margin")
    positive = scores[:, :positive_prototype_count].max(axis=1)
    other = scores[:, positive_prototype_count:].max(axis=1)
    differences = positive - other
    return differences > margin, differences


def apply_gates(
    ids: list[str],
    sparse: np.ndarray,
    dense: np.ndarray,
    accept: np.ndarray,
    *,
    dense_weight: float = .65,
    top_k: int = 5,
    min_lexical: float = 0.0,
) -> dict[str, list[list[str]]]:
    """Rank only task-accepted inputs, without tuning on reference labels."""
    sparse = np.asarray(sparse, dtype=np.float64)
    dense = np.asarray(dense, dtype=np.float64)
    accept = np.asarray(accept, dtype=np.bool_)
    if sparse.ndim != 2 or dense.shape != sparse.shape or sparse.shape[1] != len(ids):
        raise ValueError("Incompatible score or catalog dimensions")
    if accept.shape != (sparse.shape[0],):
        raise ValueError("Expected one intent decision per query")
    if not np.isfinite(sparse).all() or not np.isfinite(dense).all():
        raise ValueError("Nonfinite retrieval score")
    if top_k < 1 or not 0 <= dense_weight <= 1 or not 0 <= min_lexical <= 1:
        raise ValueError("Invalid top-k, weight or lexical threshold")
    dense_scaled = np.clip((dense + 1) / 2, 0, 1)
    hybrid = dense_weight * dense_scaled + (1 - dense_weight) * sparse
    result: dict[str, list[list[str]]] = {
        "dense_intent_gate": [], "hybrid_intent_gate": [],
        "hybrid_intent_and_lexical_gate": [],
    }
    for i, accepted in enumerate(accept):
        result["dense_intent_gate"].append(rank_ids(dense_scaled[i], ids, top_k) if accepted else [])
        result["hybrid_intent_gate"].append(rank_ids(hybrid[i], ids, top_k) if accepted else [])
        result["hybrid_intent_and_lexical_gate"].append(
            rank_ids(hybrid[i], ids, top_k)
            if accepted and float(sparse[i].max()) > min_lexical else []
        )
    return result


def compute_intent_similarities(queries: list[str], *,
                                model_name: str, allow_download: bool) -> np.ndarray:
    prototypes = list(SYMPTOM_INTENT_PROTOTYPES + OTHER_TASK_PROTOTYPES)
    # Shape query x prototype; uses the same encoder as retrieval, but NOT
    # disease catalog text; no supervised labels or gold files are consumed.
    return dense_scores(prototypes, queries, model_name, allow_download)


def run(queries: Path, catalog: Path, out_dir: Path, *,
        model_name: str = "all-MiniLM-L6-v2", dense_weight: float = .65,
        margin: float = 0, top_k: int = 5, min_lexical: float = 0.,
        allow_download: bool = False, allow_test: bool = False) -> dict:
    if not 0 <= margin <= 1:
        raise ValueError("Invalid margin; choose on development before independent test")
    ids, documents = load_catalog(catalog)
    query_ids, texts, split = load_queries(queries, allow_test=allow_test)
    intent_sim = compute_intent_similarities(texts, model_name=model_name,
                                             allow_download=allow_download)
    accept, differences = intent_decision(intent_sim, margin=margin)
    sparse = tfidf_scores(documents, texts)
    dense = dense_scores(documents, texts, model_name, allow_download)
    rankings = apply_gates(ids, sparse, dense, accept, dense_weight=dense_weight,
                           top_k=top_k, min_lexical=min_lexical)
    out_dir.mkdir(parents=True, exist_ok=True)
    for model, ranked in rankings.items():
        with (out_dir / f"{model}.jsonl").open("w", encoding="utf-8") as stream:
            for qid, disease_ids in zip(query_ids, ranked):
                stream.write(json.dumps({"query_id": qid, "predicted_disease_ids": disease_ids},
                                        sort_keys=True) + "\n")
    prompt_hash = hashlib.sha256(
        json.dumps([*SYMPTOM_INTENT_PROTOTYPES, *OTHER_TASK_PROTOTYPES],
                   ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    report = {
        "protocol": "medipower-m9-zero-shot-query-intent-ablation-v1",
        "split": split, "query_count": len(query_ids), "model_name": model_name,
        "model_revision": "NOT_PINNED_USE_LOCAL_CACHE_RECORD_REVISION_FOR_PUBLICATION",
        "catalog_sha256": sha256_file(catalog), "queries_sha256": sha256_file(queries),
        "intent_prototypes_sha256": prompt_hash,
        "positive_prototype_count": len(SYMPTOM_INTENT_PROTOTYPES),
        "negative_prototype_count": len(OTHER_TASK_PROTOTYPES),
        "intent_margin": margin, "min_lexical": min_lexical,
        "dense_weight": dense_weight, "top_k": top_k,
        "intent_accepted": int(accept.sum()),
        "intent_rejected": len(accept) - int(accept.sum()),
        "models": list(rankings),
        "abstained_per_model": {name: sum(not ids for ids in ranked)
                               for name, ranked in rankings.items()},
        "warning": "Unvalidated post-hoc prototype classifier. NEVER claim M8 is independent validation or clinical intent/safety reliability. Compare positive false-abstention and off-topic false positives together.",
    }
    (out_dir / "manifest.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    # No query text, model confidence, patient information, or gold labels logged.
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--queries", type=Path, required=True)
    p.add_argument("--catalog", type=Path, default=Path("app/data/diseases.csv"))
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--model-name", default="all-MiniLM-L6-v2")
    p.add_argument("--dense-weight", type=float, default=.65)
    p.add_argument("--intent-margin", type=float, default=0.)
    p.add_argument("--min-lexical", type=float, default=0.)
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--allow-model-download", action="store_true")
    p.add_argument("--allow-test", action="store_true")
    args = p.parse_args()
    print(json.dumps(run(args.queries, args.catalog, args.out_dir,
                         model_name=args.model_name, dense_weight=args.dense_weight,
                         margin=args.intent_margin, min_lexical=args.min_lexical,
                         top_k=args.top_k, allow_download=args.allow_model_download,
                         allow_test=args.allow_test), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
