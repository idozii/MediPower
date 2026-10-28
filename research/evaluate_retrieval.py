"""Dependency-free, label-based information-retrieval evaluation.

This tool measures ranking against independently annotated disease *identifiers*.
It does not estimate diagnostic accuracy, calibration, or clinical safety.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import mean


def load_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path.name}:{number}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"Expected JSON object at {path.name}:{number}")
            records.append(record)
    if not records:
        raise ValueError(f"No records in {path.name}")
    return records


def identifiers(record: dict, key: str) -> list[str]:
    values = record.get(key)
    if not isinstance(values, list):
        raise ValueError(f"{key} must be a list for query_id={record.get('query_id')}")
    output = []
    for value in values:
        if not isinstance(value, (int, str)) or isinstance(value, bool):
            raise ValueError(f"Invalid {key} identifier for query_id={record.get('query_id')}")
        ident = str(value).strip()
        if not ident:
            raise ValueError(f"Blank {key} identifier for query_id={record.get('query_id')}")
        output.append(ident)
    if len(output) != len(set(output)):
        raise ValueError(f"Duplicate {key} identifiers for query_id={record.get('query_id')}")
    return output


def indexed(records: list[dict], source: str) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for item in records:
        query_id = item.get("query_id")
        if not isinstance(query_id, str) or not query_id.strip():
            raise ValueError(f"Each {source} record needs a nonempty string query_id")
        if query_id in result:
            raise ValueError(f"Duplicate query_id={query_id} in {source}")
        result[query_id] = item
    return result


def ranking_metrics(predicted: list[str], relevant: list[str], k: int) -> dict[str, float]:
    relevant_set = set(relevant)
    top = predicted[:k]
    hit_positions = [i for i, value in enumerate(top, 1) if value in relevant_set]
    ideal_count = min(len(relevant_set), k)
    ideal_dcg = sum(1 / math.log2(i + 1) for i in range(1, ideal_count + 1))
    dcg = sum(1 / math.log2(i + 1) for i in hit_positions)
    return {
        f"recall@{k}": len(hit_positions) / len(relevant_set),
        f"mrr@{k}": 1 / hit_positions[0] if hit_positions else 0.0,
        f"ndcg@{k}": dcg / ideal_dcg if ideal_dcg else 0.0,
        f"hit@{k}": float(bool(hit_positions)),
    }


def evaluate(gold: list[dict], predicted: list[dict], ks: tuple[int, ...], allow_test: bool = False) -> dict:
    truth = indexed(gold, "gold")
    outputs = indexed(predicted, "predictions")
    if set(truth) != set(outputs):
        raise ValueError("Gold and predictions query_id sets must match exactly")

    splits = {item.get("split") for item in gold}
    if len(splits) != 1 or not splits.issubset({"development", "test"}):
        raise ValueError("Gold labels must have a consistent split: development or test")
    split = next(iter(splits))
    if split == "test" and not allow_test:
        raise ValueError("Test split is locked; pass --allow-test only after preregistration and authorization")

    scores: list[dict[str, float]] = []
    negatives = 0
    negative_false_positives = 0
    positives_abstained = 0
    for query_id, item in truth.items():
        relevant = identifiers(item, "relevant_disease_ids")
        ranked = identifiers(outputs[query_id], "predicted_disease_ids")
        if not relevant:
            if item.get("expected_abstain") is not True:
                raise ValueError(f"No relevant labels for {query_id}; mark explicit expected_abstain=true")
            negatives += 1
            negative_false_positives += bool(ranked)
            continue
        if item.get("expected_abstain") is True:
            raise ValueError(f"Conflicting labels and expected_abstain for {query_id}")
        positives_abstained += not ranked
        metrics = {}
        for k in ks:
            metrics.update(ranking_metrics(ranked, relevant, k))
        scores.append(metrics)

    if not scores:
        raise ValueError("At least one positive-query gold label is required")
    result = {
        "split": split,
        "positive_queries": len(scores),
        "negative_controls": negatives,
        "positive_abstention_rate": positives_abstained / len(scores),
        "negative_false_positive_rate": negative_false_positives / negatives if negatives else None,
        "metrics": {key: mean(row[key] for row in scores) for key in scores[0]},
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", required=True, type=Path)
    parser.add_argument("--prediction", required=True, action="append", metavar="NAME=PATH")
    parser.add_argument("--k", type=int, nargs="+", default=[1, 3, 5])
    parser.add_argument("--allow-test", action="store_true", help="Only after written approval and evaluation freeze")
    args = parser.parse_args()
    if not args.k or any(k < 1 for k in args.k):
        parser.error("--k must contain positive integers")
    ks = tuple(sorted(set(args.k)))
    gold = load_jsonl(args.gold)
    reports = {}
    for setting in args.prediction:
        name, sep, location = setting.partition("=")
        if not sep or not name or not location or name in reports:
            parser.error("--prediction must be unique NAME=PATH")
        reports[name] = evaluate(gold, load_jsonl(Path(location)), ks, allow_test=args.allow_test)
    print(json.dumps({"protocol": "medipower-ir-evaluation-v1", "models": reports}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
