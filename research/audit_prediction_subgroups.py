"""Development-only subgroup error audit for model prediction JSONL.

Each subgroup reports counts and rates separately for positive symptom queries
and explicitly labeled nonclinical negatives. Prints NO query text or patient IDs.
For constructed stress fixtures, sample sizes are too small for safety claims.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path

from research.evaluate_retrieval import indexed, identifiers, load_jsonl, ranking_metrics


def summarize(gold: list[dict], models: dict[str, list[dict]], *,
              k: int = 3, allow_test: bool = False) -> dict:
    if k < 1:
        raise ValueError("k must be >=1")
    truth = indexed(gold, "gold")
    splits = {row.get("split") for row in truth.values()}
    if len(splits) != 1 or not splits.issubset({"development", "test"}):
        raise ValueError("A consistent development or test split is required")
    split = next(iter(splits))
    if split == "test" and not allow_test:
        raise ValueError("Official test is locked pending authorization and protocol freeze")
    if not models:
        raise ValueError("At least one prediction file required")
    by_model = {name: indexed(rows, name) for name, rows in models.items()}
    for name, predictions in by_model.items():
        if predictions.keys() != truth.keys():
            raise ValueError(f"{name}: gold/prediction query IDs do not match")

    result = {"protocol": "medipower-m8-development-error-subgroups-v1",
              "split": split, "query_count": len(truth), "k": k,
              "models": {}}
    for name, predictions in by_model.items():
        groups: dict[str, dict[str, float | int]] = defaultdict(
            lambda: {"positives": 0, "negatives": 0, "positive_abstained": 0,
                     "negative_false_positives": 0, "positive_hit_at_k": 0,
                     "positive_recall_sum_at_k": 0.0}
        )
        for qid, row in truth.items():
            subgroup = row.get("subgroup")
            if not isinstance(subgroup, str) or not subgroup.strip():
                raise ValueError(f"Missing subgroup for {qid}")
            relevant = identifiers(row, "relevant_disease_ids")
            ranked = identifiers(predictions[qid], "predicted_disease_ids")
            if relevant:
                if row.get("expected_abstain") is True:
                    raise ValueError(f"Conflicting labels for {qid}")
                state = groups[subgroup]
                state["positives"] += 1
                state["positive_abstained"] += not ranked
                metrics = ranking_metrics(ranked, relevant, k)
                state["positive_hit_at_k"] += int(metrics[f"hit@{k}"])
                state["positive_recall_sum_at_k"] += metrics[f"recall@{k}"]
            else:
                if row.get("expected_abstain") is not True:
                    raise ValueError(f"Missing explicit negative annotation for {qid}")
                state = groups[subgroup]
                state["negatives"] += 1
                state["negative_false_positives"] += bool(ranked)
        final = {}
        for subgroup, values in sorted(groups.items()):
            n_pos, n_neg = values["positives"], values["negatives"]
            final[subgroup] = {
                "positive_count": n_pos, "negative_count": n_neg,
                "positive_abstained": values["positive_abstained"],
                "negative_false_positives": values["negative_false_positives"],
                f"recall@{k}": values["positive_recall_sum_at_k"] / n_pos if n_pos else None,
                f"hit@{k}": values["positive_hit_at_k"] / n_pos if n_pos else None,
                "positive_abstention_rate": values["positive_abstained"] / n_pos if n_pos else None,
                "negative_false_positive_rate": values["negative_false_positives"] / n_neg if n_neg else None,
            }
        result["models"][name] = final
    return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gold", type=Path, required=True)
    p.add_argument("--prediction", action="append", required=True, metavar="MODEL=FILE")
    p.add_argument("--k", type=int, default=3)
    p.add_argument("--allow-test", action="store_true")
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    predictions = {}
    for spec in args.prediction:
        name, eq, path = spec.partition("=")
        if not eq or not name or not path or name in predictions:
            p.error("Model predictions must have unique MODEL=FILE arguments")
        predictions[name] = load_jsonl(Path(path))
    output = summarize(load_jsonl(args.gold), predictions, k=args.k, allow_test=args.allow_test)
    serialized = json.dumps(output, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)


if __name__ == "__main__":
    main()
