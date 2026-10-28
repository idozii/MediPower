"""M10: threshold-free intent error diagnostics and a *descriptive* risk–coverage grid.

This inspects M9 frozen margins and ORIGINAL Hybrid predictions on identical
queries, against local development annotations. It never tunes a threshold
or fits a classifier and never treats the M8 toy set as independent validation.
Do NOT choose a threshold from M8 curves and publish performance on M8 as a
confirmatory test. Official test split remains locked.

  python -m research.audit_intent_risk_coverage \
    --gold research/examples/abstention_stress_v1_gold.jsonl \
    --margins research/outputs/m10-intent-margins/intent_margins.jsonl \
    --predictions research/outputs/m8-stress-original/hybrid.jsonl \
    --out research/outputs/m10-risk-coverage.json
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path

from research.evaluate_retrieval import identifiers, indexed, load_jsonl, ranking_metrics

DEFAULT_THRESHOLDS = (-.25, -.15, -.10, -.05, 0., .05, .10, .15, .25)


def evaluate_curve(gold: list[dict], margins: list[dict], predictions: list[dict], *,
                   thresholds: tuple[float, ...] = DEFAULT_THRESHOLDS,
                   k: int = 3, allow_test: bool = False,
                   include_error_ids: bool = False) -> dict:
    truth = indexed(gold, "gold")
    scores = indexed(margins, "intent margins")
    ranked = indexed(predictions, "original retrieval predictions")
    if not truth.keys() == scores.keys() == ranked.keys():
        raise ValueError("Gold, frozen margins and ungated predictions must have identical query IDs")
    if k < 1:
        raise ValueError("k must be positive")
    splits = {v.get("split") for v in truth.values()}
    if len(splits) != 1 or next(iter(splits)) not in {"development", "test"}:
        raise ValueError("Consistent split development or test required")
    split = next(iter(splits))
    if split == "test" and not allow_test:
        raise ValueError("Official test split locked pending authorization and preregistration")

    if not thresholds or len(thresholds) != len(set(thresholds)):
        raise ValueError("Threshold grid must be nonempty and contain no duplicates")
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) or not -2 <= v <= 2
           for v in thresholds):
        raise ValueError("Invalid intent margin threshold")

    pos_ids, neg_ids = [], []
    groups: dict[str, list[str]] = defaultdict(list)
    for qid, row in truth.items():
        subgroup = row.get("subgroup")
        if not isinstance(subgroup, str) or not subgroup:
            raise ValueError(f"Missing subgroup annotation on {qid}")
        groups[subgroup].append(qid)
        relevant = identifiers(row, "relevant_disease_ids")
        identifiers(ranked[qid], "predicted_disease_ids")
        mr = scores[qid].get("intent_margin")
        if not isinstance(mr, (int, float)) or not math.isfinite(mr) or not -2 <= mr <= 2:
            raise ValueError(f"Missing or nonfinite intent margin on {qid}")
        a, b = scores[qid].get("max_symptom_similarity"), scores[qid].get("max_other_task_similarity")
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            raise ValueError(f"Missing component similarities on {qid}")
        if not math.isfinite(a) or not math.isfinite(b) or abs(float(mr) - (float(a) - float(b))) > 1e-7:
            raise ValueError(f"Intent margin inconsistency on {qid}")
        if scores[qid].get("intent_accepted_at_zero") is not (mr > 0):
            raise ValueError(f"Invalid frozen zero-margin decision on {qid}")
        if relevant:
            if row.get("expected_abstain") is True:
                raise ValueError(f"Contradictory positive annotation on {qid}")
            pos_ids.append(qid)
        else:
            if row.get("expected_abstain") is not True:
                raise ValueError(f"Empty relevant labels cannot imply an off-topic negative on {qid}")
            neg_ids.append(qid)
    if not pos_ids or not neg_ids:
        raise ValueError("Both independently annotated positive and negative examples required")

    def score_subset(qids: list[str], threshold: float) -> dict:
        positives = [qid for qid in qids if qid in positive_set]
        negatives = [qid for qid in qids if qid in negative_set]
        intent_accepted = [qid for qid in qids if scores[qid]["intent_margin"] > threshold]
        accepted_pos = sum(qid in positive_set for qid in intent_accepted)
        accepted_neg = sum(qid in negative_set for qid in intent_accepted)
        failed_neg = sum(
            bool(identifiers(ranked[qid], "predicted_disease_ids"))
            for qid in negatives if scores[qid]["intent_margin"] > threshold
        )
        false_abstain = sum(
            not (scores[qid]["intent_margin"] > threshold
                 and bool(identifiers(ranked[qid], "predicted_disease_ids")))
            for qid in positives
        )
        sum_recall = sum(
            ranking_metrics(identifiers(ranked[qid], "predicted_disease_ids"),
                            identifiers(truth[qid], "relevant_disease_ids"), k)[f"recall@{k}"]
            for qid in positives if scores[qid]["intent_margin"] > threshold
        )
        return {
            "queries": len(qids), "positives": len(positives), "negatives": len(negatives),
            "accepted_queries": len(intent_accepted),
            "intent_accepted_positives": accepted_pos,
            "intent_accepted_negatives": accepted_neg,
            "positive_false_abstentions": false_abstain,
            "negative_false_positives": failed_neg,
            "coverage": len(intent_accepted) / len(qids) if qids else None,
            "positive_retention_rate": accepted_pos / len(positives) if positives else None,
            "positive_false_abstention_rate": false_abstain / len(positives) if positives else None,
            "negative_false_positive_rate": failed_neg / len(negatives) if negatives else None,
            f"positive_recall@{k}": sum_recall / len(positives) if positives else None,
        }

    positive_set, negative_set = set(pos_ids), set(neg_ids)
    curve = [
        {"intent_threshold": t, **score_subset(list(truth), t)}
        for t in sorted(thresholds)
    ]
    zero = score_subset(list(truth), 0.)
    grouped = {name: score_subset(ids, 0.) for name, ids in sorted(groups.items())}
    report = {
        "protocol": "medipower-m10-development-intent-risk-coverage-v1",
        "split": split,
        "sample_count": len(truth),
        "positive_count": len(pos_ids),
        "negative_count": len(neg_ids),
        "k": k,
        "threshold_selection": "DESCRIPTIVE_GRID_ONLY_NO_SELECTION",
        "at_frozen_zero_margin": zero,
        "subgroups_at_zero_margin": grouped,
        "threshold_grid": curve,
        "warnings": [
            "All metrics conditional on developer-authored post-hoc M8 stress prompts; NOT independent validation.",
            "Lower false-positive counts achieved by rejecting positive symptom narratives are unacceptable as a standalone success measure.",
            "Margins are not calibrated probabilities; the threshold grid must not be optimized on this known set.",
            "Nonclinical task intent and symptomatic out-of-catalog disease are different problems.",
        ],
    }
    if include_error_ids:
        # Explicitly opt-in: query IDs might themselves expose identifiers in
        # future private datasets. Never output raw text here.
        report["query_ids_at_zero_margin"] = {
            "positive_false_abstention": sorted(qid for qid in pos_ids if
                scores[qid]["intent_margin"] <= 0 or
                not identifiers(ranked[qid], "predicted_disease_ids")),
            "nonclinical_false_positive": sorted(qid for qid in neg_ids if
                scores[qid]["intent_margin"] > 0 and
                identifiers(ranked[qid], "predicted_disease_ids")),
        }
    return report


def check_manifest_compatibility(margins_path: Path, predictions_path: Path,
                                 *, split: str) -> dict:
    margin_manifest_path = margins_path.parent / "manifest.json"
    prediction_manifest_path = predictions_path.parent / "manifest.json"
    if not margin_manifest_path.is_file() or not prediction_manifest_path.is_file():
        raise ValueError("Both prediction and intent-margin manifest.json are required")
    m = json.loads(margin_manifest_path.read_text(encoding="utf-8"))
    p = json.loads(prediction_manifest_path.read_text(encoding="utf-8"))
    if m.get("protocol") != "medipower-m10-frozen-intent-margins-v1":
        raise ValueError("Wrong margin exporter protocol")
    if not p.get("protocol", "").startswith("medipower-m2-retrieval-predictions"):
        raise ValueError("Expected original M2 ungated retrieval predictions")
    if m.get("queries_sha256") != p.get("queries_sha256") or m.get("split") != p.get("split") or m.get("split") != split:
        raise ValueError("Source query hashes/splits disagree — refusing unpaired comparison")
    return {"queries_sha256": m["queries_sha256"],
            "margins_model_name": m.get("model_name"),
            "predictions_model_name": p.get("dense_model"),
            "margins_model_revision": m.get("model_revision")}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gold", type=Path, required=True)
    p.add_argument("--margins", type=Path, required=True)
    p.add_argument("--predictions", type=Path, required=True)
    p.add_argument("--k", type=int, default=3)
    p.add_argument("--thresholds", type=float, nargs="+", default=DEFAULT_THRESHOLDS)
    p.add_argument("--out", type=Path)
    p.add_argument("--include-error-ids", action="store_true")
    p.add_argument("--allow-test", action="store_true",
                   help="Only after separate written test protocol authorization")
    args = p.parse_args()
    gold = load_jsonl(args.gold)
    report = evaluate_curve(gold, load_jsonl(args.margins), load_jsonl(args.predictions),
                            thresholds=tuple(args.thresholds), k=args.k,
                            allow_test=args.allow_test, include_error_ids=args.include_error_ids)
    report["source_provenance"] = check_manifest_compatibility(
        args.margins, args.predictions, split=report["split"])
    printed = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(printed + "\n", encoding="utf-8")
    print(printed)


if __name__ == "__main__":
    main()
