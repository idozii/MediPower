"""R2: prepare separate blinded reviewer worksheets from independently sourced DEV text.

NO model outputs, gold labels or real patient records should be supplied.
Packets contain query text, so keep them in private local storage and distribute
only to reviewers authorized to read the source materials. This script cannot
certify independent authorship, annotation blindness, privacy or data rights.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import random

from research.validate_intent_cohort import RIGHTS_BASIS, normalize

SOURCE_FIELDS = ("query_id", "text", "split", "source_id", "template_family",
                 "source_origin", "rights_basis")
PACKET_FIELDS = ("query_id", "text", "annotator_id", "intent_label")


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_development_sources(path: Path, *,
                             known_queries: Path | None = None) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or set(SOURCE_FIELDS) - set(reader.fieldnames):
            raise ValueError("Missing required source metadata columns")
        if set(reader.fieldnames) - set(SOURCE_FIELDS):
            raise ValueError("Unexpected columns in source CSV: do not include model output or annotations")
        rows = list(reader)
    if not rows:
        raise ValueError("No development source records")
    known_hashes = set()
    if known_queries and known_queries.is_file():
        with known_queries.open(encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    row = json.loads(line)
                    known_hashes.add(hashlib.sha256(normalize(row["text"]).encode()).hexdigest())
    ids, text_hashes = set(), set()
    for row in rows:
        if None in row or not all(isinstance(row[k], str) and row[k].strip() for k in SOURCE_FIELDS):
            raise ValueError("Missing or malformed provenance fields")
        if row["split"] != "development":
            raise ValueError("R2 packet preparation accepts development split only")
        if row["rights_basis"] not in RIGHTS_BASIS:
            raise ValueError("Unsupported data-rights assertion; review permissions manually")
        qid = row["query_id"].strip()
        text = normalize(row["text"])
        if not text:
            raise ValueError("Empty normalized text")
        if qid in ids:
            raise ValueError("Duplicate query_id")
        ids.add(qid)
        digest = hashlib.sha256(text.encode()).hexdigest()
        if digest in text_hashes:
            raise ValueError("Duplicate source text; collect unique queries with independent provenance")
        if digest in known_hashes:
            raise ValueError("Reused a previously viewed M8 development query; source disjointness violated")
        text_hashes.add(digest)
    return rows


def prepare(source: Path, out_dir: Path, *,
            seed: int = 20261028, known_queries: Path | None = None) -> dict:
    if not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if known_queries is None:
        known_queries = Path("research/examples/abstention_stress_v1_queries.jsonl")
    rows = read_development_sources(source, known_queries=known_queries)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, offset in (("reviewer_A", 0), ("reviewer_B", 871)):
        ordered = sorted(rows, key=lambda r: r["query_id"])
        random.Random(seed + offset).shuffle(ordered)
        dest = out_dir / f"{name}_packet.csv"
        with dest.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=PACKET_FIELDS)
            writer.writeheader()
            for row in ordered:
                writer.writerow({"query_id": row["query_id"],
                                 "text": row["text"],
                                 "annotator_id": "",
                                 "intent_label": ""})
    count_sources = Counter(row["source_id"] for row in rows)
    manifest = {
        "protocol": "medipower-r2-development-reviewer-packets-v1",
        "development_only": True,
        "source_sha256": hash_file(source),
        "known_queries_sha256": hash_file(known_queries) if known_queries and known_queries.is_file() else None,
        "rows": len(rows), "distinct_source_groups": len(count_sources),
        "distinct_template_families": len({row["template_family"] for row in rows}),
        "reviewer_packet_files": ["reviewer_A_packet.csv", "reviewer_B_packet.csv"],
        "status": "AWAITING_INDEPENDENT_REVIEWERS_AND_PERMISSIONS",
        "warning": "Programmatic separation does not establish independence of authors, annotators or source data. Never upload raw text to public GitHub.",
    }
    (out_dir / "packet_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=Path("research/private_data/intent_cohort/packets"))
    parser.add_argument("--seed", type=int, default=20261028)
    parser.add_argument("--known-queries", type=Path,
                        default=Path("research/examples/abstention_stress_v1_queries.jsonl"))
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.out_dir,
                             seed=args.seed, known_queries=args.known_queries),
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
