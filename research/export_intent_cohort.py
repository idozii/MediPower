"""M11: export reviewed DEVELOPMENT intent annotations into separate query and gold files.

Output lives under gitignored research/outputs; query text can still be
sensitive, so inspect source rights before use. Never commit outputs.
No test access or automatic adjudication is supported by this exporter.

  python -m research.export_intent_cohort \
    --development research/private_data/intent_cohort/development.csv \
    --out-dir research/outputs/m11-intent-dev
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from research.validate_intent_cohort import audit


def export(development: Path, out_dir: Path) -> dict:
    summary, _ = audit(development, required_split="development")
    with development.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    out_dir.mkdir(parents=True, exist_ok=True)
    query_path = out_dir / "queries.jsonl"
    gold_path = out_dir / "intent_gold.jsonl"
    with query_path.open("w", encoding="utf-8") as q, gold_path.open("w", encoding="utf-8") as g:
        for row in rows:
            q.write(json.dumps({
                "query_id": row["query_id"].strip(),
                "text": row["text"].strip(), "split": "development"
            }, sort_keys=True) + "\n")
            g.write(json.dumps({
                "query_id": row["query_id"].strip(),
                "intent_label": row["final_label"].strip(),
                "split": "development",
                "source_id": row["source_id"].strip(),
                "template_family": row["template_family"].strip(),
            }, sort_keys=True) + "\n")
    report = {
        "protocol": "medipower-m11-intent-development-export-v1",
        "annotation_sha256": summary["source_file_sha256"],
        "rows": summary["rows"],
        "split": "development",
        "label_counts": summary["adjudicated_label_counts"],
        "query_path": str(query_path),
        "gold_path": str(gold_path),
        "warning": "Two-reviewer identity and source permissions were checked structurally, not independently verified. No validation of medical diagnosis performed.",
    }
    (out_dir / "manifest.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--development", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(export(a.development, a.out_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
