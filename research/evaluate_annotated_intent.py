"""M11: evaluate frozen intent margins on separately annotated intent labels.

This is intent-classification auditing, NOT disease retrieval evaluation.
Only symptom_information vs nonclinical_task form the predefined binary slice.
Other health/general/mixed/out-of-catalog labels are counted separately.
No threshold optimization, trained model, or test access by default.

 python -m research.evaluate_annotated_intent \
   --gold research/outputs/m11-intent-dev/intent_gold.jsonl \
   --queries research/outputs/m11-intent-dev/queries.jsonl \
   --margins research/outputs/m11-intent-margins/intent_margins.jsonl
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path

from research.evaluate_retrieval import indexed, load_jsonl
from research.export_predictions import sha256_file
from research.validate_intent_cohort import INTENT_LABELS


def evaluate(gold: list[dict], margins: list[dict], *,
             threshold: float = 0.0, allow_test: bool = False) -> dict:
    if not isinstance(threshold, (int, float)) or not math.isfinite(threshold) or not -2 <= threshold <= 2:
        raise ValueError("Invalid intent threshold")
    annotations = indexed(gold, "annotations")
    scores = indexed(margins, "margins")
    if annotations.keys() != scores.keys():
        raise ValueError("Intent gold/margins query IDs must match")
    splits = {row.get("split") for row in annotations.values()}
    if len(splits) != 1 or next(iter(splits)) not in {"development", "test"}:
        raise ValueError("Single annotated split required")
    split = next(iter(splits))
    if split == "test" and not allow_test:
        raise ValueError("Official task-intent test annotations are locked")
    counts = Counter()
    accepted = Counter()
    groups = set()
    for qid, row in annotations.items():
        label = row.get("intent_label")
        if label not in INTENT_LABELS:
            raise ValueError("Unknown intent label")
        group = row.get("source_id")
        template = row.get("template_family")
        if not isinstance(group, str) or not group.strip() or not isinstance(template, str) or not template.strip():
            raise ValueError("Missing source/template provenance")
        groups.add(group)
        margin = scores[qid].get("intent_margin")
        a = scores[qid].get("max_symptom_similarity")
        b = scores[qid].get("max_other_task_similarity")
        if any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in (margin, a, b)):
            raise ValueError("Missing or nonfinite frozen similarities")
        if abs((a - b) - margin) > 1e-7 or not -2 <= margin <= 2:
            raise ValueError("Inconsistent intent margin")
        counts[label] += 1
        if margin > threshold:
            accepted[label] += 1
    if not counts["symptom_information"] or not counts["nonclinical_task"]:
        raise ValueError("Prospective binary analysis needs both symptom and nonclinical examples")
    by_label = {
        label: {"count": counts[label], "accepted": accepted[label],
                "acceptance_rate": accepted[label] / counts[label] if counts[label] else None}
        for label in sorted(INTENT_LABELS)
    }
    return {
        "protocol": "medipower-m11-prospective-task-intent-development-evaluation-v1",
        "split": split, "threshold": threshold,
        "total_queries": len(annotations),
        "source_group_count": len(groups),
        "binary_slice_count": counts["symptom_information"] + counts["nonclinical_task"],
        "positive_symptom_retention": accepted["symptom_information"] / counts["symptom_information"],
        "positive_symptom_false_abstention": (counts["symptom_information"] - accepted["symptom_information"]) / counts["symptom_information"],
        "nonclinical_false_acceptance": accepted["nonclinical_task"] / counts["nonclinical_task"],
        "excluded_from_binary_slice": sum(counts[lbl] for lbl in (
            "general_health_information", "clinical_out_of_catalog", "ambiguous_or_mixed")),
        "by_label": by_label,
        "warnings": [
            "Annotation and rights provenance require independent review, irrespective of local validation.",
            "Clinical_out_of_catalog intent is NOT nonclinical; general health and ambiguous queries are reported separately.",
            "Intent acceptance and condition-ranking correctness are different measurements.",
            "This is NOT a medical safety, clinical diagnostic, or patient-risk evaluation.",
        ],
    }


def check_query_manifest(queries: Path, margins: Path, gold: Path) -> dict:
    manifest_file = margins.parent / "manifest.json"
    cohort_manifest = gold.parent / "manifest.json"
    if not manifest_file.is_file() or not cohort_manifest.is_file():
        raise ValueError("Both M10 margin and M11 cohort manifests are required")
    m = json.loads(manifest_file.read_text(encoding="utf-8"))
    c = json.loads(cohort_manifest.read_text(encoding="utf-8"))
    if m.get("protocol") != "medipower-m10-frozen-intent-margins-v1" or c.get("protocol") != "medipower-m11-intent-development-export-v1":
        raise ValueError("Wrong frozen margin/cohort manifest protocol")
    if m.get("split") != c.get("split") or m.get("queries_sha256") != sha256_file(queries):
        raise ValueError("Cohort query file and margin hashes/split disagree")
    return {
        "queries_sha256": m["queries_sha256"],
        "annotated_source_sha256": c["annotation_sha256"],
        "intent_prototypes_sha256": m.get("intents_prototype_sha256"),
        "model_name": m.get("model_name"),
        "model_revision": m.get("model_revision"),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--queries", type=Path, required=True)
    p.add_argument("--gold", type=Path, required=True)
    p.add_argument("--margins", type=Path, required=True)
    p.add_argument("--threshold", type=float, default=0.0)
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    output = evaluate(load_jsonl(a.gold), load_jsonl(a.margins), threshold=a.threshold)
    output["provenance"] = check_query_manifest(a.queries, a.margins, a.gold)
    serialized = json.dumps(output, indent=2, sort_keys=True)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)


if __name__ == "__main__":
    main()
