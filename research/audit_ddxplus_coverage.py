"""M3 development-only ontology coverage audit without auto-approval.

Reads synthetic validation labels, pending mapping candidates and local catalog.
Writes aggregate distribution and a human-review *worksheet* with empty target ID.
Does not access test split or approve approximate name matches.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit(patients: Path, candidates: Path, catalog: Path, out_dir: Path,
          *, max_rows: int = 0) -> dict:
    if max_rows < 0:
        raise ValueError("max_rows must be nonnegative")
    if "test" in patients.name.lower() or "train" in patients.name.lower():
        raise ValueError("Only the development/validation CSV may be inspected")
    with candidates.open(encoding="utf-8", newline="") as handle:
        proposed = list(csv.DictReader(handle))
    if not proposed or "source_pathology" not in proposed[0]:
        raise ValueError("Missing ontology candidate worksheet")
    if any(str(row.get("review_status", "")).strip().lower() == "approved" for row in proposed):
        raise ValueError("Candidate worksheet must contain PENDING suggestions only; use independently reviewed mapping separately")
    if len({r["source_pathology"] for r in proposed}) != len(proposed):
        raise ValueError("Duplicate source pathology in candidate worksheet")

    with catalog.open(encoding="utf-8", newline="") as handle:
        target = list(csv.DictReader(handle))
    if not target or not {"disease_id", "disease_name"}.issubset(target[0]):
        raise ValueError("Invalid target catalog")
    target_ids = {row["disease_id"] for row in target}
    if len(target_ids) != len(target):
        raise ValueError("Target ID conflicts")

    rows = 0
    counts: Counter[str] = Counter()
    with patients.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if "PATHOLOGY" not in (reader.fieldnames or []):
            raise ValueError("Validation CSV missing PATHOLOGY")
        for row in reader:
            rows += 1
            label = str(row.get("PATHOLOGY", "")).strip()
            if not label:
                raise ValueError(f"Empty pathology label in CSV row {rows}")
            counts[label] += 1
            if max_rows and rows >= max_rows:
                break

    if not rows:
        raise ValueError("No validation rows")
    worksheet_names = {row["source_pathology"] for row in proposed}
    missing = sorted(set(counts) - worksheet_names)
    extras = sorted(worksheet_names - set(counts))
    if missing:
        raise ValueError(f"Candidate worksheet missing {len(missing)} observed source pathology labels")

    suggestions = []
    for row in sorted(proposed, key=lambda r: (-counts[r["source_pathology"]], r["source_pathology"])):
        suggestions.append({
            "source_pathology": row["source_pathology"],
            "validation_count": counts[row["source_pathology"]],
            "validation_fraction": round(counts[row["source_pathology"]] / rows, 8),
            "candidate_ids": row.get("candidate_ids", ""),
            "candidate_names": row.get("candidate_names", ""),
            "proposed_target_disease_id": "",
            "review_status": "pending",
            "clinical_review_notes": "",
        })
    out_dir.mkdir(parents=True, exist_ok=True)
    review_csv = out_dir / "ontology_review_worksheet.csv"
    with review_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(suggestions[0]))
        writer.writeheader()
        writer.writerows(suggestions)

    summary = {
        "protocol": "medipower-m3-development-ontology-coverage-v1",
        "status": "MANUAL_MAPPING_REVIEW_REQUIRED",
        "source_scope": "VALIDATION_ONLY_SYNTHETIC_COMMUNITY_MIRROR",
        "validation_rows_sampled": rows,
        "source_pathologies_observed": len(counts),
        "source_pathologies_in_worksheet": len(proposed),
        "source_labels_without_candidates": len(missing),
        "candidate_labels_absent_from_validation": len(extras),
        "catalog_condition_count": len(target_ids),
        "reviewed_approved_mapping_count": 0,
        "mapping_coverage": None,
        "sha256": {"patients": file_hash(patients), "candidates": file_hash(candidates), "catalog": file_hash(catalog)},
        "note": "Candidate name similarity does NOT establish clinical equivalence. Coverage cannot be calculated until manual review is approved.",
        "pathology_counts": dict(sorted(counts.items())),
    }
    (out_dir / "ontology_coverage_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--patients", type=Path, default=Path("research/private_data/ddxplus/validate.csv"))
    p.add_argument("--candidates", type=Path, default=Path("research/private_data/ddxplus_mapping_candidates.csv"))
    p.add_argument("--catalog", type=Path, default=Path("app/data/diseases.csv"))
    p.add_argument("--out-dir", type=Path, default=Path("research/outputs/m3-coverage"))
    p.add_argument("--max-rows", type=int, default=0, help="development-only sampling for smoke tests")
    args = p.parse_args()
    result = audit(args.patients, args.candidates, args.catalog, args.out_dir, max_rows=args.max_rows)
    # Aggregate summary only. Avoid outputting raw query/patient records.
    brief = {k: v for k, v in result.items() if k != "pathology_counts"}
    print(json.dumps(brief, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
