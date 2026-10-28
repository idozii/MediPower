"""Export reproducible TF-IDF, BM25, dense and hybrid IR predictions.

Input: queries-only JSONL with query_id, text and split. No gold labels permitted.
No downloads occur unless --allow-model-download is provided explicitly.

Examples:
  python -m research.export_predictions --queries research/examples/dev_queries.jsonl --out-dir research/outputs/dev --models tfidf bm25
  python -m research.export_predictions --queries /private/queries.jsonl --out-dir research/outputs/dev --models tfidf bm25 dense hybrid --allow-model-download
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import sklearn

TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_catalog(path: Path) -> tuple[list[str], list[str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("Empty disease catalog")
    ids: list[str] = []
    documents: list[str] = []
    for row in rows:
        disease_id = str(row.get("disease_id", "")).strip()
        name = str(row.get("disease_name", "")).strip()
        if not disease_id or not name:
            raise ValueError("Catalog needs disease_id and disease_name in every row")
        ids.append(disease_id)
        documents.append(" ".join([
            name, str(row.get("description", "")), str(row.get("mapped_departments", "")),
        ]))
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate disease IDs in catalog")
    return ids, documents


def load_queries(path: Path, *, allow_test: bool = False) -> tuple[list[str], list[str], str]:
    query_ids, texts, splits = [], [], set()
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at query line {line_no}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"Query line {line_no} must be an object")
            if "relevant_disease_ids" in row or "expected_abstain" in row:
                raise ValueError("Ground-truth fields are forbidden in prediction query files")
            query_id, text = row.get("query_id"), row.get("text")
            split = row.get("split")
            if not isinstance(query_id, str) or not query_id.strip() or not isinstance(text, str) or not text.strip():
                raise ValueError(f"Invalid query_id or text at line {line_no}")
            if split not in {"development", "test"}:
                raise ValueError(f"Query line {line_no} must declare development or test split")
            query_ids.append(query_id)
            texts.append(text)
            splits.add(split)
    if not query_ids or len(set(query_ids)) != len(query_ids):
        raise ValueError("Queries must be nonempty and query IDs unique")
    if len(splits) != 1:
        raise ValueError("A prediction run must target one split")
    split = next(iter(splits))
    if split == "test" and not allow_test:
        raise ValueError("Test split is locked; --allow-test requires prior authorization and evaluation freeze")
    return query_ids, texts, split


def bm25_scores(documents: list[str], queries: list[str], *, k1: float = 1.5, b: float = 0.75) -> np.ndarray:
    if k1 <= 0 or not 0 <= b <= 1:
        raise ValueError("Invalid BM25 parameters")
    tokenized = [tokenize(text) for text in documents]
    frequencies = [Counter(tokens) for tokens in tokenized]
    doc_freq = Counter(token for counts in frequencies for token in counts)
    n_docs = len(documents)
    avg_length = sum(map(len, tokenized)) / n_docs
    result = np.zeros((len(queries), n_docs), dtype=np.float64)
    for q, query in enumerate(queries):
        for token in set(tokenize(query)):
            count = doc_freq.get(token, 0)
            if not count:
                continue
            idf = math.log(1 + (n_docs - count + 0.5) / (count + 0.5))
            for d, freq in enumerate(frequencies):
                tf = freq.get(token, 0)
                if not tf:
                    continue
                denominator = tf + k1 * (1 - b + b * len(tokenized[d]) / avg_length)
                result[q, d] += idf * tf * (k1 + 1) / denominator
    return result


def tfidf_scores(documents: list[str], queries: list[str]) -> np.ndarray:
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, lowercase=True)
    corpus_matrix = vectorizer.fit_transform(documents)
    query_matrix = vectorizer.transform(queries)
    return cosine_similarity(query_matrix, corpus_matrix)


def dense_scores(documents: list[str], queries: list[str], model_name: str, allow_download: bool) -> np.ndarray:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError("Dense baseline needs sentence-transformers installed") from exc
    try:
        encoder = SentenceTransformer(model_name, local_files_only=not allow_download)
    except Exception as exc:
        raise RuntimeError(
            "Could not load the embedding model from local cache. "
            "Obtain and pin an approved model or explicitly pass --allow-model-download."
        ) from exc
    corpus_embeddings = np.asarray(encoder.encode(documents, normalize_embeddings=True), dtype=np.float32)
    query_embeddings = np.asarray(encoder.encode(queries, normalize_embeddings=True), dtype=np.float32)
    # Normalized dot product is cosine similarity in [-1, 1].
    return query_embeddings @ corpus_embeddings.T


def rank_ids(scores: np.ndarray, catalog_ids: list[str], top_k: int, minimum_score: float = 0) -> list[str]:
    if len(scores) != len(catalog_ids):
        raise ValueError("Score length does not match catalog")
    if not np.all(np.isfinite(scores)):
        raise ValueError("Non-finite retrieval scores")
    if len(scores) == 0 or float(np.max(scores)) <= minimum_score:
        return []
    return [catalog_ids[i] for i in sorted(range(len(catalog_ids)), key=lambda i: (-float(scores[i]), catalog_ids[i]))[:top_k]]


def run(
    queries: Path,
    catalog: Path,
    out_dir: Path,
    models: list[str],
    *,
    top_k: int = 5,
    dense_model: str = "all-MiniLM-L6-v2",
    dense_weight: float = 0.65,
    allow_model_download: bool = False,
    allow_test: bool = False,
) -> dict:
    allowed = {"tfidf", "bm25", "dense", "hybrid"}
    if not models or len(set(models)) != len(models) or set(models) - allowed:
        raise ValueError("Choose unique models from tfidf, bm25, dense, hybrid")
    if top_k < 1 or not 0 <= dense_weight <= 1:
        raise ValueError("Invalid top_k or dense_weight")

    ids, documents = load_catalog(catalog)
    query_ids, texts, split = load_queries(queries, allow_test=allow_test)
    scores: dict[str, np.ndarray] = {}
    if "tfidf" in models or "hybrid" in models:
        scores["tfidf"] = tfidf_scores(documents, texts)
    if "bm25" in models:
        scores["bm25"] = bm25_scores(documents, texts)
    if "dense" in models or "hybrid" in models:
        scores["dense"] = dense_scores(documents, texts, dense_model, allow_model_download)
    if "hybrid" in models:
        # Research baseline only; NOT the heuristic/clinical-boost production score.
        scores["hybrid"] = dense_weight * np.clip((scores["dense"] + 1) / 2, 0, 1) + (1 - dense_weight) * scores["tfidf"]

    out_dir.mkdir(parents=True, exist_ok=True)
    for model in models:
        destination = out_dir / f"{model}.jsonl"
        with destination.open("w", encoding="utf-8") as handle:
            for q, query_id in enumerate(query_ids):
                s = scores[model][q]
                if model == "dense":
                    s = np.clip((s + 1) / 2, 0, 1)
                record = {
                    "query_id": query_id,
                    "predicted_disease_ids": rank_ids(s, ids, top_k),
                }
                handle.write(json.dumps(record, sort_keys=True) + "\n")

    manifest = {
        "protocol": "medipower-m2-retrieval-predictions-v1",
        "split": split,
        "query_count": len(query_ids),
        "catalog_size": len(ids),
        "queries_sha256": sha256_file(queries),
        "catalog_sha256": sha256_file(catalog),
        "models": models,
        "top_k": top_k,
        "dense_weight": dense_weight if "hybrid" in models else None,
        "dense_model": dense_model if any(m in models for m in ("dense", "hybrid")) else None,
        "sklearn_version": sklearn.__version__,
        "notes": "Development prototype; scores uncalibrated. Hybrid is an experimental linear fusion, not production inference.",
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, default=Path("app/data/diseases.csv"))
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--models", nargs="+", choices=("tfidf", "bm25", "dense", "hybrid"), default=["tfidf", "bm25"])
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--dense-model", default="all-MiniLM-L6-v2")
    parser.add_argument("--dense-weight", type=float, default=0.65)
    parser.add_argument("--allow-model-download", action="store_true")
    parser.add_argument("--allow-test", action="store_true", help="Only after evaluation protocol freeze and authorization")
    args = parser.parse_args()
    print(json.dumps(run(
        args.queries, args.catalog, args.out_dir, args.models,
        top_k=args.top_k, dense_model=args.dense_model,
        dense_weight=args.dense_weight, allow_model_download=args.allow_model_download,
        allow_test=args.allow_test,
    ), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
