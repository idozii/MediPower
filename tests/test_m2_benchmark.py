"""Unit and integration tests for M2 retrieval baselines on toy data only."""

import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from research.export_predictions import (
    bm25_scores, load_catalog, load_queries, rank_ids, run, tfidf_scores,
)
from research.evaluate_retrieval import evaluate, load_jsonl


class BenchmarkTests(unittest.TestCase):
    def test_bm25_relevance(self):
        scores = bm25_scores(["dental tooth cavity", "asthma wheezing cough"], ["tooth cavity"])
        self.assertGreater(scores[0, 0], scores[0, 1])

    def test_tfidf_relevance(self):
        scores = tfidf_scores(["dental tooth cavity", "asthma wheezing cough"], ["tooth cavity"])
        self.assertGreater(scores[0, 0], scores[0, 1])

    def test_rank_tie_and_zero_abstention(self):
        self.assertEqual(rank_ids(np.array([0.5, 0.5]), ["2", "1"], 2), ["1", "2"])
        self.assertEqual(rank_ids(np.zeros(2), ["1", "2"], 2), [])

    def test_guard_labels_and_test_split(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "queries.jsonl"
            path.write_text('{"query_id":"a","text":"headache","split":"test"}\n')
            with self.assertRaisesRegex(ValueError, "Test split is locked"):
                load_queries(path)
            self.assertEqual(load_queries(path, allow_test=True)[2], "test")
            path.write_text('{"query_id":"a","text":"headache","split":"development","relevant_disease_ids":["1"]}\n')
            with self.assertRaisesRegex(ValueError, "Ground-truth fields"):
                load_queries(path)

    def test_end_to_end_lexical_predictions(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            catalog = root / "catalog.csv"
            catalog.write_text("disease_id,disease_name,description,mapped_departments\n1,Dental cavity,tooth pain bite,Dentistry\n2,Asthma,wheezing cough,Pulmonology\n")
            queries = root / "queries.jsonl"
            queries.write_text('{"query_id":"q1","text":"tooth pain bite","split":"development"}\n')
            gold = root / "gold.jsonl"
            gold.write_text('{"query_id":"q1","split":"development","relevant_disease_ids":["1"]}\n')
            report = run(queries, catalog, root / "out", ["tfidf", "bm25"], top_k=2)
            self.assertEqual(report["query_count"], 1)
            self.assertEqual(report["catalog_size"], 2)
            for model in ("tfidf", "bm25"):
                predictions = load_jsonl(root / "out" / f"{model}.jsonl")
                result = evaluate(load_jsonl(gold), predictions, (1, 2))
                self.assertEqual(result["metrics"]["recall@1"], 1.0)


if __name__ == "__main__":
    unittest.main()
