"""Run with: python -m unittest discover -s tests -v"""

import unittest

from research.evaluate_retrieval import evaluate, identifiers, ranking_metrics


class RetrievalEvaluationTests(unittest.TestCase):
    def test_perfect_ranking(self):
        result = ranking_metrics(["a", "b", "c"], ["a", "b"], 2)
        self.assertEqual(result["recall@2"], 1.0)
        self.assertEqual(result["mrr@2"], 1.0)
        self.assertEqual(result["ndcg@2"], 1.0)

    def test_partial_ranking_and_abstention(self):
        result = ranking_metrics(["x", "b", "a"], ["a", "b"], 2)
        self.assertEqual(result["recall@2"], 0.5)
        self.assertEqual(result["mrr@2"], 0.5)
        self.assertGreater(result["ndcg@2"], 0.0)
        self.assertLess(result["ndcg@2"], 1.0)
        self.assertEqual(ranking_metrics([], ["a"], 3)["recall@3"], 0.0)

    def test_positive_and_negative_controls(self):
        gold = [
            {"query_id": "p1", "split": "development", "relevant_disease_ids": ["21"]},
            {"query_id": "n1", "split": "development", "relevant_disease_ids": [], "expected_abstain": True},
        ]
        predictions = [
            {"query_id": "p1", "predicted_disease_ids": ["21"]},
            {"query_id": "n1", "predicted_disease_ids": ["1"]},
        ]
        report = evaluate(gold, predictions, (1, 3))
        self.assertEqual(report["metrics"]["recall@1"], 1)
        self.assertEqual(report["negative_false_positive_rate"], 1)

    def test_test_split_requires_explicit_unlock(self):
        gold = [{"query_id": "p", "split": "test", "relevant_disease_ids": ["1"]}]
        predictions = [{"query_id": "p", "predicted_disease_ids": ["1"]}]
        with self.assertRaisesRegex(ValueError, "Test split is locked"):
            evaluate(gold, predictions, (1,))
        self.assertEqual(evaluate(gold, predictions, (1,), allow_test=True)["positive_queries"], 1)

    def test_duplicates_and_mismatched_query_sets_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            identifiers({"query_id": "p", "predicted_disease_ids": ["1", "1"]}, "predicted_disease_ids")
        with self.assertRaisesRegex(ValueError, "query_id sets"):
            evaluate(
                [{"query_id": "p", "split": "development", "relevant_disease_ids": ["1"]}],
                [{"query_id": "wrong", "predicted_disease_ids": ["1"]}],
                (1,),
            )


if __name__ == "__main__":
    unittest.main()
