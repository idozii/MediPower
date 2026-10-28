"""Audit the legacy classifier dataset, repeatable splits and template leakage.

Usage:
  python -m research.audit_dataset --data diagnosis_dataset.csv --out research/outputs/m2_dataset_audit.json

This audits a *development* dataset. It cannot establish independent clinical validity.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re

from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.utils.symptom_matching import enrich_sparse_query, normalize_symptom_text

PREFIXES = (
    "I have ",
    "I feel ",
    "I am experiencing ",
    "Symptoms include ",
    "Lately I have been having ",
)


def clean_text(raw: str) -> str:
    return enrich_sparse_query(normalize_symptom_text(raw))


def normalized_raw(raw: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", raw.lower()))


def template_group(raw: str) -> str:
    return next((prefix.strip() for prefix in PREFIXES if raw.startswith(prefix)), "OTHER")


def duplicate_summary(keys: list[str], labels: list[str]) -> dict:
    label_sets: dict[str, set[str]] = defaultdict(set)
    for key, label in zip(keys, labels):
        label_sets[key].add(label)
    return {
        "unique_keys": len(label_sets),
        "extra_rows_with_duplicate_key": len(keys) - len(label_sets),
        "keys_with_conflicting_labels": sum(len(v) > 1 for v in label_sets.values()),
    }


def overlap_stats(texts: list[str], train_ids: list[int], test_ids: list[int]) -> dict:
    train_set = {texts[i] for i in train_ids}
    return {
        "train_rows": len(train_ids),
        "test_rows": len(test_ids),
        "test_rows_with_identical_train_input": sum(texts[i] in train_set for i in test_ids),
        "distinct_test_inputs_also_in_train": len({texts[i] for i in test_ids} & train_set),
    }


def build_pipeline() -> Pipeline:
    # Keep identical configuration to scripts/train_diagnosis_classifier.py.
    return Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, lowercase=True, sublinear_tf=True)),
        ("clf", LogisticRegression(max_iter=3000, class_weight="balanced", solver="lbfgs")),
    ])


def evaluate_split(texts: list[str], labels: list[str], train_ids: list[int], test_ids: list[int]) -> dict:
    train_labels = {labels[i] for i in train_ids}
    missing = sorted(set(labels) - train_labels)
    if missing:
        return {"status": "not_evaluable", "classes_absent_from_train": missing}
    estimator = build_pipeline()
    estimator.fit([texts[i] for i in train_ids], [labels[i] for i in train_ids])
    prediction = estimator.predict([texts[i] for i in test_ids])
    truth = [labels[i] for i in test_ids]
    return {
        "status": "ok",
        "accuracy": float(accuracy_score(truth, prediction)),
        "macro_f1": float(f1_score(truth, prediction, average="macro", zero_division=0)),
    }


def audit(path: Path, *, seed: int = 42, rerun: bool = True) -> dict:
    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    if not rows or any("text" not in r or "disease" not in r for r in rows):
        raise ValueError("Expected non-empty CSV with text,disease columns")

    rows = [(r["text"], r["disease"].strip()) for r in rows if r["text"].strip() and r["disease"].strip()]
    raw, labels = map(list, zip(*rows))
    texts = [clean_text(s) for s in raw]
    ids = list(range(len(texts)))
    templates = [template_group(q) for q in raw]
    random_train, random_test = train_test_split(ids, test_size=0.2, random_state=seed, stratify=labels)
    group_train, group_test = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed).split(ids, labels, groups=texts))
    template_train, template_test = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed).split(ids, labels, groups=templates))

    split_ids = {
        "random_stratified": (list(random_train), list(random_test)),
        "exact_input_grouped": (list(group_train), list(group_test)),
        "held_out_sentence_prefix": (list(template_train), list(template_test)),
    }
    comparisons = {}
    for name, (train, test) in split_ids.items():
        detail = overlap_stats(texts, train, test)
        detail["train_class_counts"] = dict(sorted(Counter(labels[i] for i in train).items()))
        detail["test_class_counts"] = dict(sorted(Counter(labels[i] for i in test).items()))
        if name == "held_out_sentence_prefix":
            detail["held_out_prefixes"] = sorted({templates[i] for i in test})
        if rerun:
            detail["classifier"] = evaluate_split(texts, labels, train, test)
        comparisons[name] = detail

    return {
        "protocol": "medipower-m2-classifier-data-audit-v1",
        "warning": "Development-data checks only; no external clinical validity or patient-level evidence.",
        "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "rows": len(rows),
        "class_counts": dict(sorted(Counter(labels).items())),
        "sentence_prefix_counts": dict(sorted(Counter(templates).items())),
        "duplicates_raw_normalized": duplicate_summary([normalized_raw(q) for q in raw], labels),
        "duplicates_model_input": duplicate_summary(texts, labels),
        "seed": seed,
        "splits": comparisons,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("diagnosis_dataset.csv"))
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--audit-only", action="store_true", help="Skip model fitting, but still audit all splits")
    args = parser.parse_args()
    report = audit(args.data, seed=args.seed, rerun=not args.audit_only)
    serialized = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)


if __name__ == "__main__":
    main()
