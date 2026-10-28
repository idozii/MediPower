"""Export frozen M9 zero-shot intent margins BEFORE reading any labels.

Output contains query IDs and model similarities but NO query text, gold labels,
patient data, or suggested 'best' threshold. Threshold selection from M8 is
post-hoc exploratory, never independent scientific validation.

  python -m research.export_intent_margins \
    --queries research/examples/abstention_stress_v1_queries.jsonl \
    --out-dir research/outputs/m10-intent-margins
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from research.export_predictions import load_queries, sha256_file
from research.export_intent_ablations import (
    OTHER_TASK_PROTOTYPES,
    SYMPTOM_INTENT_PROTOTYPES,
    compute_intent_similarities,
)


def margin_rows(query_ids: list[str], similarities: np.ndarray, *,
                n_positive: int = len(SYMPTOM_INTENT_PROTOTYPES)) -> list[dict]:
    sims = np.asarray(similarities, dtype=np.float64)
    if sims.ndim != 2 or sims.shape[0] != len(query_ids) or not 0 < n_positive < sims.shape[1]:
        raise ValueError("Invalid query/prototype similarity matrix")
    if len(set(query_ids)) != len(query_ids) or not query_ids:
        raise ValueError("Nonempty unique query IDs required")
    if not np.isfinite(sims).all() or np.max(np.abs(sims)) > 1.0001:
        raise ValueError("Nonfinite or out-of-range cosine similarity")
    pos = np.max(sims[:, :n_positive], axis=1)
    other = np.max(sims[:, n_positive:], axis=1)
    return [
        {"query_id": qid, "max_symptom_similarity": float(a),
         "max_other_task_similarity": float(b),
         "intent_margin": float(a - b), "intent_accepted_at_zero": bool(a > b)}
        for qid, a, b in zip(query_ids, pos, other)
    ]


def run(queries: Path, out_dir: Path, *,
        model_name: str = "all-MiniLM-L6-v2",
        allow_download: bool = False, allow_test: bool = False,
        similarities: np.ndarray | None = None) -> dict:
    query_ids, texts, split = load_queries(queries, allow_test=allow_test)
    if similarities is None:
        similarities = compute_intent_similarities(
            texts, model_name=model_name, allow_download=allow_download)
    rows = margin_rows(query_ids, similarities)
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / "intent_margins.jsonl"
    with output.open("w", encoding="utf-8") as stream:
        for item in rows:
            stream.write(json.dumps(item, sort_keys=True) + "\n")
    prototype_sha = hashlib.sha256(json.dumps(
        [*SYMPTOM_INTENT_PROTOTYPES, *OTHER_TASK_PROTOTYPES], ensure_ascii=False
    ).encode("utf-8")).hexdigest()
    manifest = {
        "protocol": "medipower-m10-frozen-intent-margins-v1",
        "split": split,
        "queries_sha256": sha256_file(queries),
        "model_name": model_name,
        "model_revision": "NOT_PINNED_CHECK_LOCAL_MODEL_CACHE",
        "intents_prototype_sha256": prototype_sha,
        "margin_definition": "max cosine query-symptom prototypes minus max cosine query-other-task prototypes",
        "query_count": len(rows),
        "margin_min": min(row["intent_margin"] for row in rows),
        "margin_max": max(row["intent_margin"] for row in rows),
        "accepted_at_zero": sum(row["intent_accepted_at_zero"] for row in rows),
        "rejected_at_zero": sum(not row["intent_accepted_at_zero"] for row in rows),
        "disclosure": "Frozen M9 post-hoc diagnostic margins only. These values do not calibrate clinical relevance or prove correctness.",
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--queries", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--model-name", default="all-MiniLM-L6-v2")
    p.add_argument("--allow-model-download", action="store_true")
    p.add_argument("--allow-test", action="store_true",
                   help="Only after separate written authorization and preregistration")
    args = p.parse_args()
    result = run(args.queries, args.out_dir, model_name=args.model_name,
                 allow_download=args.allow_model_download, allow_test=args.allow_test)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
