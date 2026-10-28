"""R2: reconcile TWO completed independent reviewer packets into M11 dev CSV.

Never fills missing labels, never resolves disagreements automatically.
If reviewers disagree, a third distinct adjudicator CSV is REQUIRED.
No official test split access, no patient data, no external calls.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from research.r2_annotation_packets import PACKET_FIELDS, read_development_sources, hash_file
from research.validate_intent_cohort import INTENT_LABELS, REQUIRED, audit

ADJUDICATION_FIELDS = ("query_id", "adjudicator_id", "final_label")


def read_review(path: Path, expected_ids: set[str]) -> dict[str, dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or set(PACKET_FIELDS) - set(reader.fieldnames):
            raise ValueError("Reviewer packet missing required fields")
        rows = list(reader)
    result = {}
    for row in rows:
        qid = str(row.get("query_id") or "").strip()
        reviewer = str(row.get("annotator_id") or "").strip()
        label = str(row.get("intent_label") or "").strip()
        if qid in result or not qid:
            raise ValueError("Duplicate/blank reviewer query_id")
        if not reviewer or label not in INTENT_LABELS:
            raise ValueError("Missing reviewer identity or unsupported/missing label")
        result[qid] = {"annotator_id": reviewer, "intent_label": label}
    if set(result) != expected_ids:
        raise ValueError("Reviewer query IDs do not match complete source cohort")
    return result


def read_adjudications(path: Path | None, expected: set[str]) -> dict[str, dict]:
    if not expected:
        if path is not None and path.exists():
            with path.open(encoding="utf-8-sig", newline="") as f:
                if list(csv.DictReader(f)):
                    raise ValueError("Adjudications supplied for records without disagreement")
        return {}
    if path is None or not path.is_file():
        raise ValueError("Disagreements require a third-reviewer adjudication CSV")
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or set(ADJUDICATION_FIELDS) - set(reader.fieldnames):
            raise ValueError("Adjudication CSV missing required fields")
        rows = list(reader)
    seen = {}
    for row in rows:
        qid = str(row.get("query_id") or "").strip()
        if not qid or qid in seen:
            raise ValueError("Duplicate adjudication query ID")
        judge = str(row.get("adjudicator_id") or "").strip()
        label = str(row.get("final_label") or "").strip()
        if not judge or label not in INTENT_LABELS:
            raise ValueError("Unreviewed disagreement or unknown adjudicated label")
        seen[qid] = {"adjudicator_id": judge, "final_label": label}
    if set(seen) != expected:
        raise ValueError("Third-reviewer adjudications must match all disagreements exactly")
    return seen


def reconcile(source: Path, reviewer_a: Path, reviewer_b: Path,
              out: Path, *, adjudications: Path | None = None,
              known_queries: Path | None = None) -> dict:
    if out.resolve() in {source.resolve(), reviewer_a.resolve(), reviewer_b.resolve()}:
        raise ValueError("Output must not overwrite the original source or reviewer evidence")
    if reviewer_a.resolve() == reviewer_b.resolve():
        raise ValueError("Two separate reviewer packet files required")
    sources = read_development_sources(source, known_queries=known_queries)
    ids = {row["query_id"] for row in sources}
    a = read_review(reviewer_a, ids)
    b = read_review(reviewer_b, ids)
    disagreements = {qid for qid in ids if a[qid]["intent_label"] != b[qid]["intent_label"]}
    reviews = read_adjudications(adjudications, disagreements)
    results = []
    for row in sources:
        qid = row["query_id"]
        left, right = a[qid], b[qid]
        if left["annotator_id"] == right["annotator_id"]:
            raise ValueError("Two reviewers must have distinct identities per query")
        third = reviews.get(qid)
        if third and third["adjudicator_id"] in {left["annotator_id"], right["annotator_id"]}:
            raise ValueError("Third adjudicator must be separate from both annotators")
        final = third["final_label"] if third else left["intent_label"]
        results.append({
            **{name: row[name] for name in
               ("query_id", "text", "split", "source_id", "template_family",
                "source_origin", "rights_basis")},
            "annotator_1_id": left["annotator_id"],
            "annotator_1_label": left["intent_label"],
            "annotator_2_id": right["annotator_id"],
            "annotator_2_label": right["intent_label"],
            "final_label": final,
            "adjudicator_id": third["adjudicator_id"] if third else "",
        })
    out.parent.mkdir(parents=True, exist_ok=True)
    # The complete output is local private annotated text and MUST NOT be committed.
    with out.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=REQUIRED)
        writer.writeheader()
        writer.writerows(results)
    validated, _ = audit(out)
    summary = {
        "protocol": "medipower-r2-development-annotation-reconciliation-v1",
        "status": "STRUCTURALLY_RECONCILED_NOT_INDEPENDENTLY_VERIFIED",
        "development_rows": len(results),
        "disagreements": len(disagreements),
        "reviewed_label_counts": validated["adjudicated_label_counts"],
        "raw_agreement_fraction": validated["raw_agreement_fraction"],
        "source_sha256": hash_file(source),
        "reviewer_A_sha256": hash_file(reviewer_a),
        "reviewer_B_sha256": hash_file(reviewer_b),
        "adjudications_sha256": hash_file(adjudications) if adjudications and adjudications.is_file() else None,
        "development_output_sha256": hash_file(out),
        "output_path": str(out),
        "notes": "Rights and true reviewer independence require external verification. No test data accessed or model run.",
    }
    (out.parent / "reconciliation_manifest.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--reviewer-a", type=Path, required=True)
    p.add_argument("--reviewer-b", type=Path, required=True)
    p.add_argument("--adjudications", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--known-queries", type=Path,
                   default=Path("research/examples/abstention_stress_v1_queries.jsonl"))
    args = p.parse_args()
    print(json.dumps(reconcile(args.source, args.reviewer_a, args.reviewer_b,
                               args.out, adjudications=args.adjudications,
                               known_queries=args.known_queries),
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
