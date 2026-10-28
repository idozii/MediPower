"""M3 local preflight: verify development-only DDXPlus files without showing records.

This utility does not download, read official test data or grant usage rights.
Example:
 python -m research.m3_source_preflight \
   --patients research/private_data/ddxplus/validate.csv \
   --evidences research/private_data/ddxplus/release_evidences.json \
   --conditions research/private_data/ddxplus/release_conditions.json \
   --expected-patients-sha256 b84733533bff01daa1d47d27a0cd4d684bb54a0fc20d80aaee1250ff8ff989ed
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

from research.prepare_ddxplus import parse_evidences


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect(patients: Path, evidences: Path, conditions: Path, *,
            expected_patients_sha256: str | None = None) -> dict:
    for path in (patients, evidences, conditions):
        if not path.is_file():
            raise FileNotFoundError(f"Missing required input: {path}")

    patient_sha = sha256(patients)
    if expected_patients_sha256 is not None and patient_sha.lower() != expected_patients_sha256.lower():
        raise ValueError(f"Validation CSV checksum mismatch: expected {expected_patients_sha256}, got {patient_sha}")

    evidence_items = json.loads(evidences.read_text(encoding="utf-8"))
    condition_items = json.loads(conditions.read_text(encoding="utf-8"))
    if not isinstance(evidence_items, dict) or not isinstance(condition_items, dict):
        raise ValueError("Expected DDXPlus evidence and condition dictionaries")
    if not evidence_items or not condition_items:
        raise ValueError("Empty evidence/condition metadata")

    total = 0
    pathologies = Counter()
    unknown_evidence_codes = Counter()
    missing_required = 0
    with patients.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"PATHOLOGY", "EVIDENCES"}.issubset(reader.fieldnames or []):
            raise ValueError("CSV missing PATHOLOGY or EVIDENCES column")
        for row in reader:
            total += 1
            pathology = str(row.get("PATHOLOGY", "")).strip()
            if not pathology or not row.get("EVIDENCES", ""):
                missing_required += 1
                continue
            pathologies[pathology] += 1
            # Only sample evidence encoding for a light preflight, no patient-level outputs.
            if total <= 250:
                for token in parse_evidences(row["EVIDENCES"]):
                    code = token.split("_@_", 1)[0]
                    if code not in evidence_items:
                        unknown_evidence_codes[code] += 1
    if total == 0:
        raise ValueError("No validation patient rows")
    return {
        "protocol": "medipower-m3-source-preflight-v1",
        "status": "FILE_INTEGRITY_CHECK_ONLY_NOT_OFFICIAL_PROVENANCE_AUTHORIZATION",
        "patients_sha256": patient_sha,
        "evidences_sha256": sha256(evidences),
        "conditions_sha256": sha256(conditions),
        "validation_rows": total,
        "unique_pathology_labels": len(pathologies),
        "metadata_evidence_types": len(evidence_items),
        "metadata_condition_types": len(condition_items),
        "missing_required_rows": missing_required,
        "unknown_evidence_code_count_first_250": sum(unknown_evidence_codes.values()),
        "pathology_counts": dict(sorted(pathologies.items())),
        "note": "Community mirror or Figshare source must be cited accurately; hash verification does not prove equivalent official release, licensing or clinical validity.",
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--patients", type=Path, required=True)
    p.add_argument("--evidences", type=Path, required=True)
    p.add_argument("--conditions", type=Path, required=True)
    p.add_argument("--expected-patients-sha256", type=str)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    result = inspect(args.patients, args.evidences, args.conditions,
                     expected_patients_sha256=args.expected_patients_sha256)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
