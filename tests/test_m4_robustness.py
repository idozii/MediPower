"""M4 statistical and inference-mode sanity tests with non-clinical toy labels."""

import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from research.compare_models import compare
from research.export_alpha_ablations import blend
from research.export_production_predictions import export


def gold_for(n):
    return [{"query_id": f"q{i}", "split": "development", "relevant_disease_ids": ["1"]}
            for i in range(n)]


class ComparisonTests(unittest.TestCase):
    def test_paired_difference_and_no_interval_on_small_examples(self):
        reference = [{"query_id": f"q{i}", "predicted_disease_ids": ["2", "1"]} for i in range(3)]
        challenger = [{"query_id": f"q{i}", "predicted_disease_ids": ["1", "2"]} for i in range(3)]
        result = compare(gold_for(3), {"ref": reference, "better": challenger},
                         baseline="ref", k=1, samples=100)
        self.assertFalse(result["intervals_available"])
        self.assertEqual(result["models"]["better"]["difference_vs_baseline"]["mrr@1"]["mean"], 1)
        self.assertIsNone(result["models"]["better"]["positive_metrics"]["mrr@1"]["ci95"])

    def test_repeatable_bootstrap_pairing(self):
        n = 35
        ref = [{"query_id": f"q{i}", "predicted_disease_ids": ["1" if i % 2 else "2"]} for i in range(n)]
        other = [{"query_id": f"q{i}", "predicted_disease_ids": ["1" if i % 3 else "2"]} for i in range(n)]
        args = (gold_for(n), {"ref": ref, "other": other})
        a = compare(*args, baseline="ref", k=1, samples=100, seed=4)
        b = compare(*args, baseline="ref", k=1, samples=100, seed=4)
        self.assertTrue(a["intervals_available"])
        self.assertEqual(a, b)

    def test_official_test_locked(self):
        gold = [{"query_id": "q", "split": "test", "relevant_disease_ids": ["1"]}]
        pred = [{"query_id": "q", "predicted_disease_ids": ["1"]}]
        with self.assertRaisesRegex(ValueError, "locked"):
            compare(gold, {"ref": pred, "other": pred}, baseline="ref", samples=100)


class ExportTests(unittest.TestCase):
    def test_alpha_endpoints(self):
        dense = np.array([[0., 1.]])
        sparse = np.array([[.2, .8]])
        np.testing.assert_allclose(blend(dense, sparse, 0), sparse)
        np.testing.assert_allclose(blend(dense, sparse, 1), [[.5, 1.]])
        with self.assertRaises(ValueError):
            blend(dense, sparse, 1.2)

    def test_production_mode_check_and_label_ids(self):
        class FakeService:
            def get_mode(self):
                return "offline_tfidf_forced"
            def get_diseases(self, text, top_k):
                return [{"disease_id": 1}]
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "catalog.csv").write_text("disease_id,disease_name\n1,Example condition\n")
            (root / "queries.jsonl").write_text('{"query_id":"q","text":"dummy symptom","split":"development"}\n')
            with self.assertRaisesRegex(RuntimeError, "Refusing mislabeled mode"):
                export(FakeService(), root / "queries.jsonl", root / "catalog.csv",
                       root / "out.jsonl", require_mode="semantic_faiss")
            report = export(FakeService(), root / "queries.jsonl", root / "catalog.csv",
                            root / "out.jsonl", require_mode="offline_tfidf_forced")
            self.assertEqual(report["query_count"], 1)
            record = json.loads((root / "out.jsonl").read_text())
            self.assertEqual(record["predicted_disease_ids"], ["1"])


if __name__ == "__main__":
    unittest.main()
