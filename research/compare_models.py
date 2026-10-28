"""Evaluate paired retrieval predictions with deterministic query-level bootstrap CIs.

Only aggregate results are printed. At least 30 independently sourced positive
queries are required for intervals; smaller demos report point estimates only.
No clinical significance claims are supported by this code.
"""

from __future__ import annotations

import argparse
import json
import random
from statistics import mean
from pathlib import Path

from research.evaluate_retrieval import indexed, identifiers, load_jsonl, ranking_metrics


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    i = (len(ordered) - 1) * p
    lower = int(i)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (i - lower)


def compare(gold: list[dict], models: dict[str, list[dict]], *,
            baseline: str, k: int = 3, samples: int = 2000, seed: int = 42,
            min_ci_queries: int = 30, allow_test: bool = False) -> dict:
    truth = indexed(gold, "gold")
    if baseline not in models or len(models) < 2:
        raise ValueError("Baseline must exist among >=2 model predictions")
    splits = {v.get("split") for v in truth.values()}
    if len(splits) != 1 or next(iter(splits)) not in {"development", "test"}:
        raise ValueError("Gold must declare a single split")
    split = next(iter(splits))
    if split == "test" and not allow_test:
        raise ValueError("Official test locked pending approved protocol")
    if samples < 100 or k < 1:
        raise ValueError("Bootstrap samples must be >=100, k >= 1")

    predictions = {name: indexed(rows, name) for name, rows in models.items()}
    for name, rows in predictions.items():
        if rows.keys() != truth.keys():
            raise ValueError(f"{name}: query_id mismatch")
    positive = []
    negative = []
    for qid, row in truth.items():
        relevant = identifiers(row, "relevant_disease_ids")
        if relevant and row.get("expected_abstain") is True:
            raise ValueError("Conflicting gold annotations")
        if not relevant:
            if row.get("expected_abstain") is not True:
                raise ValueError("An out-of-catalog pathology is not a negative control")
            negative.append(qid)
        else:
            positive.append(qid)
    if not positive:
        raise ValueError("At least one positive query is required")

    per_query = {}
    negative_counts = {}
    for name, rows in predictions.items():
        per_query[name] = {}
        for qid in positive:
            ids = identifiers(rows[qid], "predicted_disease_ids")
            per_query[name][qid] = ranking_metrics(ids, identifiers(truth[qid], "relevant_disease_ids"), k)
        negative_counts[name] = sum(bool(identifiers(rows[qid], "predicted_disease_ids")) for qid in negative)

    keys = list(per_query[baseline][positive[0]])
    rng = random.Random(seed)
    # Official cohort rows can reuse identical symptom narratives. When a group_id
    # is supplied by M3, resample the entire group together, never individual rows.
    provided = [truth[qid].get("group_id") for qid in positive]
    has_groups = any(value is not None for value in provided)
    if has_groups and (
        any(not isinstance(value, str) or not value.strip() for value in provided)
    ):
        raise ValueError("Every positive query must carry a nonempty group_id when grouping is enabled")
    if has_groups:
        cluster_members: dict[str, list[str]] = {}
        for qid, group in zip(positive, provided):
            cluster_members.setdefault(group, []).append(qid)
        cluster_ids = sorted(cluster_members)
        resampling_units = len(cluster_ids)
        bootstrap_unit = "group_id"
        draws = [
            [qid for group in rng.choices(cluster_ids, k=resampling_units)
             for qid in cluster_members[group]]
            for _ in range(samples)
        ] if resampling_units >= min_ci_queries else []
    else:
        resampling_units = len(positive)
        bootstrap_unit = "query_id"
        draws = [rng.choices(positive, k=len(positive)) for _ in range(samples)] if resampling_units >= min_ci_queries else []

    report = {"protocol": "medipower-m4-paired-bootstrap-v1", "split": split,
              "positive_queries": len(positive), "negative_controls": len(negative),
              "baseline": baseline, "k": k, "bootstrap_samples": samples,
              "seed": seed, "intervals_available": bool(draws),
              "bootstrap_unit": bootstrap_unit,
              "independent_resampling_units": resampling_units,
              "independence_warning": "Identical-text clustering is a partial safeguard only; source/patient/template dependencies may remain.",
              "models": {}}
    for name in models:
        metrics = {}
        differences = {}
        for metric in keys:
            scores = [per_query[name][qid][metric] for qid in positive]
            metrics[metric] = {"mean": mean(scores), "ci95": None}
            dvalues = [
                per_query[name][qid][metric] - per_query[baseline][qid][metric]
                for qid in positive
            ]
            differences[metric] = {"mean": mean(dvalues), "ci95": None}
            if draws:
                bootstrap_mean = [mean(per_query[name][qid][metric] for qid in sample) for sample in draws]
                bootstrap_diff = [mean(
                    per_query[name][qid][metric] - per_query[baseline][qid][metric]
                    for qid in sample
                ) for sample in draws]
                metrics[metric]["ci95"] = [percentile(bootstrap_mean, .025), percentile(bootstrap_mean, .975)]
                differences[metric]["ci95"] = [percentile(bootstrap_diff, .025), percentile(bootstrap_diff, .975)]
        report["models"][name] = {
            "positive_metrics": metrics,
            "difference_vs_baseline": differences,
            "negative_false_positive_rate": negative_counts[name] / len(negative) if negative else None,
            "negative_control_n": len(negative),
        }
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gold", type=Path, required=True)
    p.add_argument("--prediction", action="append", required=True, metavar="NAME=PATH")
    p.add_argument("--baseline", required=True)
    p.add_argument("--k", type=int, default=3)
    p.add_argument("--samples", type=int, default=2000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--allow-test", action="store_true")
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    models = {}
    for spec in args.prediction:
        key, sep, path = spec.partition("=")
        if not sep or not key or not path or key in models:
            p.error("Predictions must be distinct NAME=PATH entries")
        models[key] = load_jsonl(Path(path))
    result = compare(load_jsonl(args.gold), models, baseline=args.baseline,
                     k=args.k, samples=args.samples, seed=args.seed, allow_test=args.allow_test)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
