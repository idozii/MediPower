"""R3: audit manual DDXPlus-to-catalog review decisions without approving mappings.

This validates only locally supplied DEVELOPMENT candidate/reviewer metadata.
It does not fetch source releases, inspect official test data, verify clinician
credentials, certify licenses, or establish clinical equivalence.

Input candidate CSV: source_pathology (plus optional descriptive suggestions)
Input reviewed CSV:
 source_pathology,target_disease_id,review_status,primary_reviewer,
 independent_reviewer,review_evidence,equivalence_type

This gate NEVER emits a "clinical validated" status, even when structurally
complete; external provenance, clinical review and independent test access
remain manual blockers.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
from pathlib import Path

from research.audit_ddxplus_coverage import file_hash

REVIEW_FIELDS = (
    "source_pathology", "target_disease_id", "review_status",
    "primary_reviewer", "independent_reviewer",
    "review_evidence", "equivalence_type",
)
ALLOWED_STATUSES = {"pending", "approved", "rejected", "unmappable"}
ALLOWED_EQUIVALENCE = {"exact_clinical_equivalence", "broader", "narrower", "not_equivalent"}


def read_rows(path: Path, required: set[str]) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or not required.issubset(fields):
            raise ValueError("Missing or duplicate CSV fields")
        rows = list(reader)
    if not rows:
        raise ValueError("No rows available for ontology review")
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError("Malformed review CSV")
    return rows


def audit(candidates: Path, reviewed: Path | None, catalog: Path,
          *, provenance: Path | None = None) -> dict:
    possible = read_rows(candidates, {"source_pathology"})
    catalog_rows = read_rows(catalog, {"disease_id", "disease_name"})
    ids = [row["disease_id"].strip() for row in catalog_rows]
    if not all(ids) or len(set(ids)) != len(ids):
        raise ValueError("Target catalog IDs missing or repeated")
    catalog_ids = set(ids)

    labels = [row["source_pathology"].strip() for row in possible]
    if not all(labels) or len(set(labels)) != len(labels):
        raise ValueError("Source candidate pathology IDs missing or repeated")
    candidate_set = set(labels)
    counts = Counter()
    evaluated = set()
    if reviewed is not None and reviewed.exists():
        rows = read_rows(reviewed, set(REVIEW_FIELDS))
        for row in rows:
            label = row["source_pathology"].strip()
            status = row["review_status"].strip().lower()
            target = row["target_disease_id"].strip()
            primary = row["primary_reviewer"].strip()
            independent = row["independent_reviewer"].strip()
            evidence = row["review_evidence"].strip()
            equivalence = row["equivalence_type"].strip().lower()
            if label not in candidate_set or label in evaluated:
                raise ValueError("Unknown or duplicate reviewed source pathology")
            if status not in ALLOWED_STATUSES:
                raise ValueError("Unrecognized review status")
            evaluated.add(label)
            if status == "approved":
                if target not in catalog_ids:
                    raise ValueError("Approved review has no valid target catalog disease ID")
                if not primary or not independent or primary == independent:
                    raise ValueError("Approved mapping requires two distinct reviewer IDs")
                if not evidence or equivalence != "exact_clinical_equivalence":
                    raise ValueError("Approved mapping requires an explicit equivalence rationale")
            else:
                if target:
                    raise ValueError("Non-approved mapping must not specify an active catalog target")
                if status in {"rejected", "unmappable"} and not evidence:
                    raise ValueError("Rejected/unmappable reviews require explanatory evidence")
            counts[status] += 1

    counts["pending"] += len(candidate_set - evaluated)

    release_claim = "NO_VERIFIED_OFFICIAL_PROVENANCE"
    if provenance is not None and provenance.exists():
        payload = json.loads(provenance.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Invalid provenance review manifest")
        required_fields = ("publisher_release_identifier", "release_sha256",
                           "license_reviewed_by", "publisher_verified_by")
        if all(isinstance(payload.get(k), str) and payload[k].strip() for k in required_fields):
            release_claim = "DECLARED_ORIGIN_METADATA_ONLY_INDEPENDENT_VERIFICATION_REQUIRED"

    total = len(candidate_set)
    return {
        "protocol": "medipower-r3-development-ontology-review-readiness-v1",
        "status": "BLOCKED_EXTERNAL_CLINICAL_EQUIVALENCE_AND_PUBLISHER_VERIFICATION",
        "candidate_source_labels": total,
        "target_catalog_conditions": len(catalog_ids),
        "mapping_review_counts": {status: counts[status] for status in sorted(ALLOWED_STATUSES)},
        "structurally_reviewed_labels": total - counts["pending"],
        "approved_mapping_metadata_only": counts["approved"],
        "reviewed_mapping_coverage_fraction": counts["approved"] / total,
        "provenance_review": release_claim,
        "source_sha256": {
            "candidates": file_hash(candidates),
            "reviewed": file_hash(reviewed) if reviewed and reviewed.is_file() else None,
            "catalog": file_hash(catalog),
            "provenance": file_hash(provenance) if provenance and provenance.is_file() else None,
        },
        "warnings": [
            "Clinical equivalence is NOT verified by two names in a CSV. Requires qualified external review.",
            "Declaring publisher metadata does NOT independently verify provenance, licensing, or test authorization.",
            "Unmappable or unapproved disease names must not be silently treated as negative examples.",
            "Only development review metadata was inspected; no official test records were accessed.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--reviewed", type=Path)
    parser.add_argument("--catalog", type=Path, default=Path("app/data/diseases.csv"))
    parser.add_argument("--provenance", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = audit(args.candidates, args.reviewed, args.catalog, provenance=args.provenance)
    serialized = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)


if __name__ == "__main__":
    main()
