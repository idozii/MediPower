"""Export the actual MediPower DiseaseService retrieval results (no hospital ranking).

Requires local ML dependencies; default startup may fall back to TF-IDF.
Always inspect retrieval_mode. Never present semantic fallback as dense results.
Example:
  FORCE_OFFLINE_RETRIEVER=1 python -m research.export_production_predictions \
    --queries research/outputs/ddxplus-dev/queries.jsonl \
    --out research/outputs/ddxplus-dev/production_offline.jsonl \
    --require-mode offline_tfidf_forced
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.export_predictions import load_catalog, load_queries, sha256_file


def export(service, queries: Path, catalog: Path, destination: Path,
           *, top_k: int = 5, require_mode: str = "semantic_faiss",
           allow_test: bool = False) -> dict:
    if top_k < 1:
        raise ValueError("top_k must be positive")
    ids, _ = load_catalog(catalog)
    allowed = set(ids)
    qids, texts, split = load_queries(queries, allow_test=allow_test)
    mode = service.get_mode()
    if mode != require_mode:
        raise RuntimeError(f"Refusing mislabeled mode: expected {require_mode}, got {mode}")
    predictions = []
    for query_id, text in zip(qids, texts):
        disease_rows = service.get_diseases(text=text, top_k=top_k)
        retrieved = [str(x["disease_id"]) for x in disease_rows]
        if len(set(retrieved)) != len(retrieved) or not set(retrieved).issubset(allowed):
            raise ValueError(f"Invalid production retrieval IDs on {query_id}")
        predictions.append({"query_id": query_id, "predicted_disease_ids": retrieved})
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        for row in predictions:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    manifest = {
        "protocol": "medipower-m4-production-retrieval-export-v1",
        "retrieval_mode": mode,
        "split": split,
        "queries_sha256": sha256_file(queries),
        "catalog_sha256": sha256_file(catalog),
        "query_count": len(predictions),
        "top_k": top_k,
        "warning": "Ranking scores are uncalibrated. Export is for retrieval research, NOT clinical diagnosis.",
    }
    (destination.parent / (destination.stem + ".manifest.json")).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--queries", required=True, type=Path)
    p.add_argument("--catalog", type=Path, default=Path("app/data/diseases.csv"))
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--require-mode", required=True, choices=("semantic_faiss", "offline_tfidf_forced", "offline_tfidf"))
    p.add_argument("--allow-test", action="store_true")
    args = p.parse_args()
    # Import heavy dependencies only after argument validation.
    from app.services.disease_service import DiseaseService
    report = export(DiseaseService(), args.queries, args.catalog, args.out,
                    top_k=args.top_k, require_mode=args.require_mode, allow_test=args.allow_test)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
