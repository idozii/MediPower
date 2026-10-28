"""R4 DEVELOPMENT-ONLY exploratory selective task-intent diagnostics.

Consumes prospective M11 intent gold labels and *frozen* M10 intent margins.
This is NOT disease relevance, diagnosis, triage, calibrated probability, or
proof of safe abstention. Previously seen M8/M9 examples cannot constitute an
independent cohort. The threshold grid is an illustration of the already-seen
M10 trade-off, NOT a threshold-selection procedure.

No official test access or model scoring is permitted by this script.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import random

from research.evaluate_annotated_intent import check_query_manifest
from research.evaluate_retrieval import load_jsonl
from research.validate_intent_cohort import INTENT_LABELS

# Known from earlier M10 work; exploratory only, not newly preregistered.
EXPLORATORY_THRESHOLDS = (-0.05, 0.0, 0.05)
PRIMARY_POSITIVE = "symptom_information"
PRIMARY_NEGATIVE = "nonclinical_task"
OTHERS = ("clinical_out_of_catalog", "general_health_information", "ambiguous_or_mixed")
CI_FIELDS = ("positive_retention", "positive_false_abstention",
             "nonclinical_false_acceptance", "binary_coverage", "binary_error_fraction")


def prepare_records(gold: list[dict], margins: list[dict]) -> list[dict]:
    if not gold or not margins:
        raise ValueError("Nonempty annotated development and margin rows required")
    g, m = {}, {}
    for row in gold:
        qid = row.get("query_id")
        if not isinstance(qid, str) or not qid.strip() or qid in g:
            raise ValueError("Unique nonempty annotated query_id required")
        g[qid] = row
    for row in margins:
        qid = row.get("query_id")
        if not isinstance(qid, str) or not qid.strip() or qid in m:
            raise ValueError("Unique nonempty margin query_id required")
        m[qid] = row
    if g.keys() != m.keys():
        raise ValueError("Annotated and margin query IDs must match exactly")
    records = []
    for qid in sorted(g):
        row, score = g[qid], m[qid]
        if row.get("split") != "development":
            raise ValueError("Official or prospective TEST split is LOCKED")
        label = row.get("intent_label")
        if label not in INTENT_LABELS:
            raise ValueError("Unsupported intent label")
        group = row.get("source_id")
        template = row.get("template_family")
        if not isinstance(group, str) or not group.strip() or not isinstance(template, str) or not template.strip():
            raise ValueError("Source and template provenance required for group bootstrap")
        margin = score.get("intent_margin")
        a = score.get("max_symptom_similarity")
        b = score.get("max_other_task_similarity")
        if any(isinstance(v, bool) or not isinstance(v, (int, float))
               or not math.isfinite(v) for v in (margin, a, b)):
            raise ValueError("Invalid frozen similarity values")
        if not (-2 <= margin <= 2) or abs((a - b) - margin) > 1e-7:
            raise ValueError("Intent margin must match frozen source scores")
        records.append({"label": label, "margin": float(margin), "source_id": group})
    if not any(r["label"] == PRIMARY_POSITIVE for r in records) or not any(r["label"] == PRIMARY_NEGATIVE for r in records):
        raise ValueError("Both symptom-information and nonclinical-task groups are required")
    return records


def measure(records: list[dict], threshold: float) -> dict:
    by_label, accepted = Counter(), Counter()
    for row in records:
        label = row["label"]
        by_label[label] += 1
        if row["margin"] > threshold:
            accepted[label] += 1
    pos, neg = by_label[PRIMARY_POSITIVE], by_label[PRIMARY_NEGATIVE]
    if not pos or not neg:
        raise ValueError("Both primary classes required to calculate selective task-intent metrics")
    pos_yes, neg_yes = accepted[PRIMARY_POSITIVE], accepted[PRIMARY_NEGATIVE]
    total_binary = pos + neg
    accepted_binary = pos_yes + neg_yes
    return {
        "threshold": threshold,
        "binary_count": total_binary,
        "binary_accepted": accepted_binary,
        "binary_coverage": accepted_binary / total_binary,
        "positive_retention": pos_yes / pos,
        "positive_false_abstention": (pos - pos_yes) / pos,
        "nonclinical_false_acceptance": neg_yes / neg,
        "binary_error_fraction": ((pos - pos_yes) + neg_yes) / total_binary,
        "accepted_binary_positive_fraction": pos_yes / accepted_binary if accepted_binary else None,
        "other_labels": {
            label: {
                "count": by_label[label],
                "accepted": accepted[label],
                "acceptance_fraction": accepted[label] / by_label[label] if by_label[label] else None,
            } for label in OTHERS
        },
    }


def percentile(values: list[float], fraction: float) -> float:
    data = sorted(values)
    if not data:
        raise ValueError("No bootstrap observations")
    point = (len(data) - 1) * fraction
    lo = int(math.floor(point))
    hi = int(math.ceil(point))
    return data[lo] + (point - lo) * (data[hi] - data[lo])


def group_bootstrap(records: list[dict], thresholds: tuple[float, ...],
                    *, repeats: int = 1000, seed: int = 20261028) -> dict:
    if not 10 <= repeats <= 10000:
        raise ValueError("Bootstrap repeats must be 10–10000")
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in records:
        grouped[row["source_id"]].append(row)
    groups = sorted(grouped)
    generator = random.Random(seed)
    samples = {t: {field: [] for field in CI_FIELDS} for t in thresholds}
    for _ in range(repeats):
        selected = [generator.choice(groups) for _ in groups]
        sampled_rows = [r for group in selected for r in grouped[group]]
        if not all(any(row["label"] == lbl for row in sampled_rows)
                   for lbl in (PRIMARY_POSITIVE, PRIMARY_NEGATIVE)):
            continue
        for threshold in thresholds:
            out = measure(sampled_rows, threshold)
            for field in CI_FIELDS:
                samples[threshold][field].append(out[field])
    report = {}
    for t in thresholds:
        n = len(samples[t][CI_FIELDS[0]])
        report[str(t)] = {
            "valid_resamples": n,
            "invalid_resamples": repeats - n,
            "intervals_95_percent": {
                field: [
                    percentile(samples[t][field], 0.025),
                    percentile(samples[t][field], 0.975),
                ] if n else None
                for field in CI_FIELDS
            },
        }
    return {"resampling_unit": "source_id", "seed": seed, "requested_resamples": repeats,
            "distinct_source_groups": len(groups), "thresholds": report}


def analyse(gold: list[dict], margins: list[dict],
            *, bootstrap_repeats: int = 1000, seed: int = 20261028) -> dict:
    records = prepare_records(gold, margins)
    return {
        "protocol": "medipower-r4-development-task-intent-risk-coverage-v1",
        "status": "EXPLORATORY_DEVELOPMENT_ONLY_NOT_EXTERNAL_EVIDENCE",
        "split": "development",
        "total_queries": len(records),
        "thresholds": [measure(records, threshold) for threshold in EXPLORATORY_THRESHOLDS],
        "cluster_bootstrap": group_bootstrap(records, EXPLORATORY_THRESHOLDS,
                                             repeats=bootstrap_repeats, seed=seed),
        "warnings": [
            "Thresholds (-0.05, 0, +0.05) were previously inspected in M10 and are not independent or preregistered.",
            "A nonclinical false acceptance is NOT a measured clinical harm; symptom false abstention must be reported alongside it.",
            "Positive symptom intent does NOT establish disease retrieval correctness; clinical_out_of_catalog must remain separate.",
            "Source-group bootstrap intervals cannot fix biased, reused, small, or non-independent sources.",
            "Do not promote the M9 gate into the app without independent prospective study and safety review.",
            "All source rights, two-annotator independence, official provenance and held-out access remain externally blocked.",
        ],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--queries", type=Path, required=True)
    p.add_argument("--gold", type=Path, required=True)
    p.add_argument("--margins", type=Path, required=True)
    p.add_argument("--out", type=Path)
    p.add_argument("--bootstrap-repeats", type=int, default=1000)
    p.add_argument("--seed", type=int, default=20261028)
    args = p.parse_args()
    # Verify frozen model/query and annotation manifests, without reading test.
    provenance = check_query_manifest(args.queries, args.margins, args.gold)
    report = analyse(load_jsonl(args.gold), load_jsonl(args.margins),
                     bootstrap_repeats=args.bootstrap_repeats, seed=args.seed)
    report["provenance"] = provenance
    output = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
