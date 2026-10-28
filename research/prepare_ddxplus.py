"""Convert locally obtained English DDXPlus synthetic patient rows to separated IR files.

The conversion NEVER downloads data, NEVER auto-maps pathologies, and NEVER
treats out-of-catalog diagnoses as negative controls.
Official DDXPlus test data are locked pending a frozen and approved protocol.
Usage:
 python -m research.prepare_ddxplus --patients /private/release_validate_patients.csv \
  --evidences /private/release_evidences.json \
  --mapping /private/ddxplus_reviewed_mapping.csv --catalog app/data/diseases.csv \
  --split development --out-dir research/outputs/ddxplus-dev
"""

from __future__ import annotations

import argparse
import ast
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_evidences(value: str) -> list[str]:
    if len(value) > 20000:
        raise ValueError("Overlong EVIDENCES field")
    try:
        values = json.loads(value)
    except json.JSONDecodeError:
        try:
            values = ast.literal_eval(value)
        except (ValueError, SyntaxError) as exc:
            raise ValueError("Unparseable EVIDENCES field") from exc
    if not isinstance(values, list) or len(values) > 150:
        raise ValueError("EVIDENCES must be a list of at most 150 values")
    if any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError("Invalid evidence identifier")
    return values


def load_metadata(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        result = {str(row["name"]): row for row in data}
    elif isinstance(data, dict):
        result = {str(key): value for key, value in data.items()}
    else:
        raise ValueError("Expected JSON object or array of evidence definitions")
    if not result or not all(isinstance(v, dict) for v in result.values()):
        raise ValueError("No usable evidence descriptions")
    return result


def evidence_phrase(token: str, metadata: dict[str, dict]) -> str | None:
    key, separator, val = token.partition("_@_")
    item = metadata.get(key)
    if item is None:
        raise ValueError(f"Unknown DDXPlus evidence code: {key}")
    if item.get("is_antecedent") is True:
        return None  # Our project only evaluates symptom evidence
    question = str(item.get("question_en", "")).strip()
    if not question:
        raise ValueError(f"Missing English symptom wording for {key}")
    if separator:
        options = item.get("value_meaning", {})
        meaning = options.get(val, {}).get("en") if isinstance(options, dict) else None
        if not meaning:
            raise ValueError(f"Missing English value meaning for {token}")
        if val == item.get("default_value") or str(meaning).strip().lower() in {"na", "n/a", "none"}:
            return None
        return f"Reported symptom: {question} Response: {str(meaning).strip()}."
    if item.get("data_type") != "B":
        raise ValueError(f"Non-binary evidence {key} missing value")
    return f"Reported symptom (yes): {question}"


def load_catalog_ids(path: Path) -> set[str]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    ids = [row.get("disease_id", "").strip() for row in rows]
    if not ids or any(not item for item in ids) or len(set(ids)) != len(ids):
        raise ValueError("Invalid disease catalog IDs")
    return set(ids)


def load_reviewed_mapping(path: Path, catalog_ids: set[str]) -> dict[str, str]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    mapping: dict[str, str] = {}
    for row in rows:
        name = str(row.get("source_pathology", "")).strip()
        disease_id = str(row.get("target_disease_id", "")).strip()
        status = str(row.get("review_status", "")).strip().lower()
        if status != "approved":
            continue
        if not name or disease_id not in catalog_ids:
            raise ValueError(f"Invalid reviewed mapping: {name!r} -> {disease_id!r}")
        if name in mapping:
            raise ValueError(f"Duplicate approved mapping for {name}")
        mapping[name] = disease_id
    if not mapping:
        raise ValueError("No approved mapping entries; manual review required")
    return mapping


def convert(
    patients: Path, evidences: Path, mapping_path: Path, catalog: Path,
    out_dir: Path, *, split: str = "development", max_rows: int = 0,
    allow_test: bool = False, approved_protocol: Path | None = None,
) -> dict:
    if split not in {"development", "test"}:
        raise ValueError("split must be development or test")
    if split == "test":
        if not allow_test or approved_protocol is None or not approved_protocol.is_file():
            raise ValueError("Official test data locked: require --allow-test and --approved-protocol")
        protocol = json.loads(approved_protocol.read_text(encoding="utf-8"))
        if protocol.get("status") != "approved_and_frozen" or not protocol.get("authorizer"):
            raise ValueError("Protocol must be explicitly approved and frozen")
    if max_rows < 0:
        raise ValueError("max_rows cannot be negative")

    mapping = load_reviewed_mapping(mapping_path, load_catalog_ids(catalog))
    metadata = load_metadata(evidences)
    with patients.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"PATHOLOGY", "EVIDENCES"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Patients CSV missing {sorted(required)}")
        rows = list(reader)
    if max_rows:
        # Stable selection independent of the pathology label (NOT a label-stratified sample).
        rows = sorted(rows, key=lambda r: hashlib.sha256(str(r.get("EVIDENCES", "")).encode()).hexdigest())[:max_rows]

    items = []
    unavailable = Counter()
    no_symptoms = 0
    for i, row in enumerate(rows):
        pathology = row["PATHOLOGY"].strip()
        if pathology not in mapping:
            unavailable[pathology] += 1
            continue
        phrases = []
        for token in parse_evidences(row["EVIDENCES"]):
            phrase = evidence_phrase(token, metadata)
            if phrase and phrase not in phrases:
                phrases.append(phrase)
        if not phrases:
            no_symptoms += 1
            continue
        text = " ".join(phrases)
        stable_id = hashlib.sha256((str(i) + "|" + row["EVIDENCES"]).encode()).hexdigest()[:20]
        items.append((stable_id, text, mapping[pathology]))

    if not items:
        raise ValueError("No mapped usable rows; review mapping, evidence vocabulary and catalog coverage")
    query_ids = [item[0] for item in items]
    if len(set(query_ids)) != len(query_ids):
        raise ValueError("Duplicate generated query identifiers")
    out_dir.mkdir(parents=True, exist_ok=True)
    queries = out_dir / "queries.jsonl"
    gold = out_dir / "gold.jsonl"
    with queries.open("w", encoding="utf-8") as q, gold.open("w", encoding="utf-8") as g:
        for query_id, text, target in items:
            q.write(json.dumps({"query_id": query_id, "text": text, "split": split}) + "\n")
            g.write(json.dumps({"query_id": query_id, "split": split, "relevant_disease_ids": [target]}) + "\n")

    report = {
        "protocol": "medipower-m3-ddxplus-adapter-v1",
        "source": "DDXPlus English — Fansi Tchango et al. NeurIPS 2022; CC BY 4.0",
        "note": "Synthetic structured evidence rendered into text, NOT natural-language patient narratives; pathology-to-catalog mapping is manually approved, not clinically validated.",
        "split": split,
        "source_files_sha256": {
            "patients": digest(patients), "evidences": digest(evidences),
            "mapping": digest(mapping_path), "catalog": digest(catalog),
        },
        "selected_rows": len(rows),
        "mapped_exported_rows": len(items),
        "mapped_without_symptoms": no_symptoms,
        "unmapped_rows": sum(unavailable.values()),
        "unmapped_pathology_counts": dict(sorted(unavailable.items())),
        "mapped_coverage_fraction": len(items) / len(rows) if rows else 0,
        "max_rows": max_rows,
        "query_text_hashes": sorted({hashlib.sha256(item[1].encode()).hexdigest() for item in items}),
    }
    (out_dir / "manifest.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    for option in ("patients", "evidences", "mapping", "catalog", "out-dir"):
        p.add_argument("--" + option, required=True, type=Path)
    p.add_argument("--split", default="development", choices=("development", "test"))
    p.add_argument("--max-rows", type=int, default=0)
    p.add_argument("--allow-test", action="store_true")
    p.add_argument("--approved-protocol", type=Path, default=None)
    args = p.parse_args()
    manifest = convert(args.patients, args.evidences, args.mapping, args.catalog,
                       args.out_dir, split=args.split, max_rows=args.max_rows,
                       allow_test=args.allow_test, approved_protocol=args.approved_protocol)
    # Avoid printing potentially sensitive symptom text or query-level records.
    print(json.dumps({k: v for k, v in manifest.items() if k != "query_text_hashes"}, indent=2))


if __name__ == "__main__":
    main()
