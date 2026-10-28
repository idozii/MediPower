"""Check labeled IR data and cross-split text overlap without training a model.

Test data must not be inspected without explicit approved access:
 python -m research.check_split_integrity --queries path/queries.jsonl \
   --gold path/gold.jsonl --catalog app/data/diseases.csv
 """

from __future__ import annotations

import argparse
import csv
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from research.evaluate_retrieval import indexed, identifiers, load_jsonl


def normalized_hash(value: str) -> str:
    text = " ".join(re.findall(r"[a-z0-9]+", value.lower()))
    return hashlib.sha256(text.encode()).hexdigest()


def validate(queries: Path, gold: Path, catalog: Path) -> dict:
    with catalog.open(encoding="utf-8", newline="") as file:
        allowed = {str(row["disease_id"]).strip() for row in csv.DictReader(file)}
    if not allowed:
        raise ValueError("Catalog cannot be empty")
    inputs = indexed(load_jsonl(queries), "queries")
    labels = indexed(load_jsonl(gold), "gold")
    if inputs.keys() != labels.keys():
        raise ValueError("Query and gold IDs must match")

    seen_text = set()
    dup_rows = 0
    counts = Counter()
    for query_id, item in inputs.items():
        text = item.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"Missing text for {query_id}")
        if "relevant_disease_ids" in item or "expected_abstain" in item:
            raise ValueError(f"Query file contains truth labels for {query_id}")
        gold_item = labels[query_id]
        if gold_item.get("text") is not None:
            raise ValueError(f"Gold file contains query text for {query_id}")
        if item.get("split") != gold_item.get("split"):
            raise ValueError(f"Split mismatch for {query_id}")
        if item.get("split") not in ("development", "test"):
            raise ValueError(f"Invalid split on {query_id}")
        relevant = identifiers(gold_item, "relevant_disease_ids")
        if set(relevant) - allowed:
            raise ValueError(f"Out-of-catalog disease id for {query_id}")
        if not relevant and gold_item.get("expected_abstain") is not True:
            raise ValueError(f"Empty gold label list cannot silently represent out-of-catalog disease: {query_id}")
        if relevant and gold_item.get("expected_abstain") is True:
            raise ValueError(f"Conflicting positive/negative labels for {query_id}")
        h = normalized_hash(text)
        dup_rows += h in seen_text
        seen_text.add(h)
        counts[item["split"]] += 1
    if len(counts) != 1:
        raise ValueError("Mixed dataset splits")
    return {"protocol": "medipower-m3-split-integrity-v1", "split": next(iter(counts)),
            "rows": len(inputs), "duplicate_normalized_text_rows": dup_rows,
            "unique_text_hashes": sorted(seen_text)}


def compare(dev: dict, test: dict) -> dict:
    if dev["split"] != "development" or test["split"] != "test":
        raise ValueError("Requires development and test manifests")
    overlap = set(dev["unique_text_hashes"]) & set(test["unique_text_hashes"])
    return {"development_rows": dev["rows"], "test_rows": test["rows"],
            "exact_normalized_text_overlap_count": len(overlap), "split_disjoint": not bool(overlap)}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--queries", required=True, type=Path)
    p.add_argument("--gold", required=True, type=Path)
    p.add_argument("--catalog", type=Path, default=Path("app/data/diseases.csv"))
    p.add_argument("--test-queries", type=Path)
    p.add_argument("--test-gold", type=Path)
    p.add_argument("--allow-test", action="store_true")
    args = p.parse_args()
    dev = validate(args.queries, args.gold, args.catalog)
    report = {k: v for k, v in dev.items() if k != "unique_text_hashes"}
    if args.test_queries or args.test_gold:
        if not (args.test_queries and args.test_gold and args.allow_test):
            p.error("Both test files and --allow-test are required after authorization")
        test = validate(args.test_queries, args.test_gold, args.catalog)
        report["between_splits"] = compare(dev, test)
        if not report["between_splits"]["split_disjoint"]:
            raise ValueError("Development/test text contamination detected")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
