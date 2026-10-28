"""M11: audit a prospectively annotated query-intent cohort WITHOUT training models.

This audits only locally supplied, rights-reviewed annotations. It NEVER
downloads text or auto-generates claims of clinical/independent labels.

Required columns:
 query_id,text,split,source_id,template_family,source_origin,rights_basis,
 annotator_1_id,annotator_1_label,annotator_2_id,annotator_2_label,
 final_label,adjudicator_id

The two annotators must be distinct. Disagreement requires a THIRD reviewer.
Test files cannot be opened until explicit --allow-test AND --approved-protocol;
these flags are procedural safeguards, not legal or clinical authorization.

Usage:
 python -m research.validate_intent_cohort \
    --development research/private_data/intent_cohort/development.csv \
    --out research/outputs/m11-development-audit.json
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re

INTENT_LABELS = {
    "symptom_information",
    "nonclinical_task",
    "general_health_information",
    "clinical_out_of_catalog",
    "ambiguous_or_mixed",
}
RIGHTS_BASIS = {
    "original_synthetic_with_permission",
    "licensed_public_with_attribution",
    "explicit_consent_documented",
}

REQUIRED = (
    "query_id", "text", "split", "source_id", "template_family",
    "source_origin", "rights_basis",
    "annotator_1_id", "annotator_1_label",
    "annotator_2_id", "annotator_2_label",
    "final_label", "adjudicator_id",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def load_approved_protocol(path: Path | None) -> dict:
    if path is None or not path.is_file():
        raise ValueError("Official test requires explicit --approved-protocol JSON after independent written authorization")
    protocol = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(protocol, dict):
        raise ValueError("Malformed authorization metadata")
    if protocol.get("status") != "approved_and_frozen":
        raise ValueError("Test protocol is not approved_and_frozen")
    for field in ("authorizer", "protocol_id", "approval_date"):
        if not isinstance(protocol.get(field), str) or not protocol[field].strip():
            raise ValueError(f"Missing manual test approval field: {field}")
    return {field: protocol[field] for field in ("authorizer", "protocol_id", "approval_date")}


def audit(path: Path, *, required_split: str = "development",
          allow_test: bool = False, approved_protocol: Path | None = None) -> tuple[dict, dict]:
    if required_split not in {"development", "test"}:
        raise ValueError("Unrecognized split")
    if required_split == "test":
        if not allow_test:
            raise ValueError("Test annotations locked, --allow-test and approved protocol required")
        approval = load_approved_protocol(approved_protocol)
    else:
        approval = None
    # All test access gates are checked BEFORE opening the file.
    if not path.is_file():
        raise FileNotFoundError(path)
    source_sha = sha256(path)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or set(REQUIRED) - set(reader.fieldnames):
            raise ValueError("Annotation CSV missing required columns")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("Annotation CSV contains duplicate column names")
        rows = list(reader)
    if not rows:
        raise ValueError("No annotated queries")
    labels, rights, agreement, adjudications = Counter(), Counter(), 0, 0
    source_ids, templates, texts = set(), set(), set()
    seen_ids = set()
    for index, row in enumerate(rows, 1):
        if None in row:
            raise ValueError(f"Extra unexpected CSV fields at row {index}")
        for field in REQUIRED:
            if row.get(field) is None:
                raise ValueError(f"Missing {field} in row {index}")
        qid = row["query_id"].strip()
        text = row["text"].strip()
        source_id = row["source_id"].strip()
        template = row["template_family"].strip()
        origin = row["source_origin"].strip()
        if not all((qid, text, source_id, template, origin)):
            raise ValueError(f"Missing text/ID/provenance at row {index}")
        if qid in seen_ids:
            raise ValueError("Duplicate query ID")
        seen_ids.add(qid)
        if row["split"].strip() != required_split:
            raise ValueError("CSV contains a different split than requested")
        if row["rights_basis"].strip() not in RIGHTS_BASIS:
            raise ValueError("Missing or unsupported documented rights basis")
        rights[row["rights_basis"].strip()] += 1

        a1 = row["annotator_1_id"].strip()
        a2 = row["annotator_2_id"].strip()
        a = row["annotator_1_label"].strip()
        b = row["annotator_2_label"].strip()
        final = row["final_label"].strip()
        adjudicator = row["adjudicator_id"].strip()
        if not a1 or not a2 or a1 == a2:
            raise ValueError("Two distinct human annotators required for each record")
        if {a, b, final} - INTENT_LABELS:
            raise ValueError("Invalid or unsupported annotation label")
        if a == b:
            agreement += 1
            if final != a:
                raise ValueError("Consensus label must match agreement")
        else:
            if not adjudicator or adjudicator in {a1, a2}:
                raise ValueError("Disagreement requires a distinct third adjudicator")
            adjudications += 1

        text_hash = hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()
        if not normalize(text):
            raise ValueError("No meaningful text after normalization")
        texts.add(text_hash)
        labels[final] += 1
        source_ids.add(source_id)
        templates.add(template)

    detail = {"query_ids": seen_ids, "source_ids": source_ids,
              "template_families": templates, "text_hashes": texts}
    report = {
        "protocol": "medipower-m11-prospective-intent-cohort-audit-v1",
        "status": "STRUCTURAL_AUDIT_ONLY_NO_ANNOTATOR_INDEPENDENCE_VERIFICATION",
        "split": required_split,
        "source_file_sha256": source_sha,
        "rows": len(rows),
        "distinct_query_ids": len(seen_ids),
        "distinct_source_ids": len(source_ids),
        "distinct_template_families": len(templates),
        "unique_normalized_texts": len(texts),
        "duplicate_normalized_text_rows": len(rows) - len(texts),
        "raw_agreement_count": agreement,
        "raw_agreement_fraction": agreement / len(rows),
        "adjudicated_disagreement_count": adjudications,
        "rights_basis_counts": dict(sorted(rights.items())),
        "adjudicated_label_counts": dict(sorted(labels.items())),
        "clinical_scope_warning": "Task-intent labels are NOT clinical ground truth and do NOT validate diagnoses. Reviewer identities and permissions require independent verification.",
    }
    if approval:
        report["approval_metadata_claim_only"] = approval
    return report, detail


def compare_splits(dev: dict, test: dict) -> dict:
    if not dev or not test:
        raise ValueError("Both audited split details required")
    fields = ("query_ids", "source_ids", "template_families", "text_hashes")
    intersections = {field: len(dev[field] & test[field]) for field in fields}
    if any(intersections.values()):
        raise ValueError(f"Cross-split leakage detected: {intersections}")
    return {"split_disjoint": True, "intersection_counts": intersections,
            "note": "Exact-text/source/template separation only. Semantic near-duplicates and repeated authors must still be reviewed."}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--development", type=Path, required=True)
    p.add_argument("--test", type=Path)
    p.add_argument("--allow-test", action="store_true",
                   help="Procedural gate only: not medical/data-use authorization")
    p.add_argument("--approved-protocol", type=Path,
                   help="Manually approved, independently frozen test metadata")
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    if args.test and (not args.allow_test or not args.approved_protocol):
        p.error("Test access requires --allow-test and --approved-protocol")
    # Validate development first; never inspect test without authorized flags.
    dev_report, dev_detail = audit(args.development)
    report = {"development": dev_report}
    if args.test:
        test_report, test_detail = audit(
            args.test, required_split="test", allow_test=args.allow_test,
            approved_protocol=args.approved_protocol)
        report["test"] = test_report
        report["between_splits"] = compare_splits(dev_detail, test_detail)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
