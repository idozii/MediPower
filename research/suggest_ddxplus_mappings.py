"""Generate PENDING ontology mapping candidates (never auto-approved).

Usage:
 python -m research.suggest_ddxplus_mappings \
  --conditions research/private_data/ddxplus/release_conditions.json \
  --catalog app/data/diseases.csv \
  --out research/private_data/ddxplus_mapping_candidates.csv
A qualified reviewer must decide which (if any) target label is equivalent.
"""

from __future__ import annotations

import argparse
import csv
from difflib import SequenceMatcher
import json
from pathlib import Path
import re


def normalize(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def candidates(conditions: dict | list, catalog_rows: list[dict], n: int = 3) -> list[dict]:
    if isinstance(conditions, dict):
        source_names = [
            str(value.get("condition_name") or key)
            for key, value in conditions.items()
            if isinstance(value, dict)
        ]
    elif isinstance(conditions, list):
        source_names = [str(item["condition_name"]) for item in conditions]
    else:
        raise ValueError("Conditions must be JSON object or array")
    if not source_names or len(set(source_names)) != len(source_names):
        raise ValueError("Source names missing or duplicated")
    if not catalog_rows:
        raise ValueError("Empty target disease catalog")
    output = []
    for source in sorted(source_names):
        top = sorted((
            (SequenceMatcher(None, normalize(source), normalize(str(row["disease_name"]))).ratio(),
             str(row["disease_id"]), str(row["disease_name"]))
            for row in catalog_rows
        ), key=lambda x: (-x[0], x[1]))[:n]
        output.append({
            "source_pathology": source,
            "target_disease_id": "",  # Never accept a candidate without review
            "review_status": "pending",
            "candidate_ids": " | ".join(v[1] for v in top),
            "candidate_names": " | ".join(v[2] for v in top),
            "similarity_scores": " | ".join(f"{v[0]:.3f}" for v in top),
        })
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--conditions", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, default=Path("app/data/diseases.csv"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    conditions = json.loads(args.conditions.read_text(encoding="utf-8"))
    with args.catalog.open(encoding="utf-8", newline="") as f:
        catalog = list(csv.DictReader(f))
    suggested = candidates(conditions, catalog)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(suggested[0]))
        writer.writeheader()
        writer.writerows(suggested)
    print(json.dumps({"candidate_pathologies": len(suggested), "approved": 0,
                      "out": str(args.out), "status": "REQUIRES_QUALIFIED_MANUAL_REVIEW"}, indent=2))


if __name__ == "__main__":
    main()
