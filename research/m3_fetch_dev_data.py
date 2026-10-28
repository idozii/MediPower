"""Opt-in download of DDXPlus VALIDATION ONLY from a COMMUNITY mirror.

This is not the author's official release. Do not claim authenticity merely
from a matching mirror checksum. Never fetch train.csv or test.csv.
Usage:
  python -m pip install huggingface_hub
  python -m research.m3_fetch_dev_data --accept-community-mirror
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from research.m3_source_preflight import inspect

COMMUNITY_REPO = "aai530-group6/ddxplus"
VALIDATION_SHA256_OBSERVED = "b84733533bff01daa1d47d27a0cd4d684bb54a0fc20d80aaee1250ff8ff989ed"
DEVELOPMENT_FILES = ("validate.csv", "release_evidences.json", "release_conditions.json")


def fetch(out_dir: Path, *, accept_community_mirror: bool = False) -> dict:
    if not accept_community_mirror:
        raise ValueError("Explicit --accept-community-mirror required; the account is not Mila/official author")
    try:
        from huggingface_hub import HfApi, snapshot_download
    except ImportError as exc:
        raise RuntimeError("Install optional dependency: python -m pip install huggingface_hub") from exc

    # Look up the current immutable commit first; snapshot_download is pinned to it.
    info = HfApi().dataset_info(COMMUNITY_REPO)
    revision = info.sha
    if not revision or len(revision) < 20:
        raise RuntimeError("Unable to resolve a full immutable dataset revision")
    out_dir.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=COMMUNITY_REPO,
        repo_type="dataset",
        revision=revision,
        allow_patterns=list(DEVELOPMENT_FILES),
        local_dir=str(out_dir),
    )
    for name in DEVELOPMENT_FILES:
        if not (out_dir / name).is_file():
            raise FileNotFoundError(f"Mirror is missing required development file: {name}")

    report = inspect(out_dir / "validate.csv", out_dir / "release_evidences.json",
                     out_dir / "release_conditions.json",
                     expected_patients_sha256=VALIDATION_SHA256_OBSERVED)
    summary = {
        "protocol": "medipower-m3-community-mirror-validation-download-v1",
        "dataset_mirror": COMMUNITY_REPO,
        "repo_revision": revision,
        "files_requested": list(DEVELOPMENT_FILES),
        "upstream_authorship": "UNVERIFIED_COMMUNITY_MIRROR",
        "official_release_equivalence": "NOT_CONFIRMED",
        "validation_sha256": report["patients_sha256"],
        "evidences_sha256": report["evidences_sha256"],
        "conditions_sha256": report["conditions_sha256"],
        "validation_rows": report["validation_rows"],
        "unique_pathology_labels": report["unique_pathology_labels"],
        "status": "DEVELOPMENT_ONLY_PENDING_PROVENANCE_AND_LABEL_REVIEW",
    }
    (out_dir / "mirror_provenance.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out-dir", type=Path, default=Path("research/private_data/ddxplus"))
    p.add_argument("--accept-community-mirror", action="store_true")
    args = p.parse_args()
    print(json.dumps(fetch(args.out_dir, accept_community_mirror=args.accept_community_mirror), indent=2))


if __name__ == "__main__":
    main()
