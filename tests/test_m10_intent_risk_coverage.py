"""M10 tests for frozen intent margins and all-query selective-risk accounting."""

import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from research.audit_intent_risk_coverage import (
    check_manifest_compatibility,
    evaluate_curve,
)
from research.export_intent_margins import margin_rows, run


def fake_fixture():
    gold = [
        {"query_id": "p1", "split": "development", "subgroup": "symptom",
         "relevant_disease_ids": ["1"]},
        {"query_id": "p2", "split": "development", "subgroup": "symptom",
         "relevant_disease_ids": ["2"]},
        {"query_id": "n1", "split": "development", "subgroup": "nonclinical",
         "relevant_disease_ids": [], "expected_abstain": True},
        {"query_id": "n2", "split": "development", "subgroup": "nonclinical",
         "relevant_disease_ids": [], "expected_abstain": True},
    ]
    # margins: +.3, -.2, +.1, -.4; at threshold 0 accept p1 and n1
    sim = np.array([[.8, .3], [.2, .4], [.6, .5], [.1, .5]])
    margins = margin_rows(["p1", "p2", "n1", "n2"], sim, n_positive=1)
    prediction = [
        {"query_id": "p1", "predicted_disease_ids": ["1", "2"]},
        {"query_id": "p2", "predicted_disease_ids": ["2", "1"]},
        {"query_id": "n1", "predicted_disease_ids": ["1"]},
        {"query_id": "n2", "predicted_disease_ids": ["2"]},
    ]
    return gold, margins, prediction


class M10RiskCoverageTests(unittest.TestCase):
    def test_margin_math_acceptance_and_finite_guard(self):
        rows = margin_rows(["p1", "n1"], np.array([[.8, .3], [.2, .4]]), n_positive=1)
        self.assertTrue(rows[0]["intent_accepted_at_zero"])
        self.assertFalse(rows[1]["intent_accepted_at_zero"])
        with self.assertRaisesRegex(ValueError, "out-of-range"):
            margin_rows(["p1"], np.array([[2., .1]]), n_positive=1)
        with self.assertRaisesRegex(ValueError, "matrix"):
            margin_rows(["p1"], np.array([[.1, .2], [.2, .3]]), n_positive=1)

    def test_zero_margin_confusion_and_ranking_on_all_positives(self):
        gold, margins, predicted = fake_fixture()
        result = evaluate_curve(gold, margins, predicted, thresholds=(-.5, 0., .6), k=1)
        row = result["at_frozen_zero_margin"]
        self.assertEqual(row["intent_accepted_positives"], 1)
        self.assertEqual(row["intent_accepted_negatives"], 1)
        self.assertEqual(row["positive_false_abstentions"], 1)
        self.assertEqual(row["negative_false_positives"], 1)
        self.assertEqual(row["positive_recall@1"], .5)
        self.assertEqual(result["threshold_grid"][0]["negative_false_positives"], 2)
        self.assertEqual(result["threshold_grid"][-1]["positive_false_abstentions"], 2)
        self.assertEqual(result["subgroups_at_zero_margin"]["symptom"]["positive_retention_rate"], .5)
        self.assertEqual(result["subgroups_at_zero_margin"]["nonclinical"]["negative_false_positive_rate"], .5)
        self.assertNotIn("query_ids_at_zero_margin", result)

    def test_optional_error_ids_are_explicit_and_no_text(self):
        gold, margins, predicted = fake_fixture()
        result = evaluate_curve(gold, margins, predicted, thresholds=(0.,),
                                include_error_ids=True)
        self.assertEqual(result["query_ids_at_zero_margin"]["positive_false_abstention"], ["p2"])
        self.assertEqual(result["query_ids_at_zero_margin"]["nonclinical_false_positive"], ["n1"])

    def test_refuse_mismatched_ids_and_unlabeled_negatives(self):
        gold, margins, predicted = fake_fixture()
        with self.assertRaisesRegex(ValueError, "identical"):
            evaluate_curve(gold, margins[:-1], predicted)
        gold[-1].pop("expected_abstain")
        with self.assertRaisesRegex(ValueError, "Empty relevant labels"):
            evaluate_curve(gold, margins, predicted)

    def test_test_split_requires_explicit_permission(self):
        gold, margins, predicted = fake_fixture()
        for row in gold:
            row["split"] = "test"
        with self.assertRaisesRegex(ValueError, "locked"):
            evaluate_curve(gold, margins, predicted)

    def test_incorrect_intent_margin_rejected(self):
        gold, margins, predicted = fake_fixture()
        margins[0]["intent_margin"] = .2
        with self.assertRaisesRegex(ValueError, "inconsistency"):
            evaluate_curve(gold, margins, predicted)

    def test_manifest_hash_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            m, p = root / "m", root / "p"
            m.mkdir()
            p.mkdir()
            (m / "manifest.json").write_text(json.dumps({
                "protocol": "medipower-m10-frozen-intent-margins-v1",
                "queries_sha256": "abc", "split": "development"}))
            (p / "manifest.json").write_text(json.dumps({
                "protocol": "medipower-m2-retrieval-predictions-v1",
                "queries_sha256": "different", "split": "development"}))
            with self.assertRaisesRegex(ValueError, "hashes"):
                check_manifest_compatibility(m / "intent_margins.jsonl",
                                              p / "hybrid.jsonl", split="development")

    def test_export_margins_with_mocked_prototypes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            queries = root / "queries.jsonl"
            queries.write_text('{"query_id":"p","text":"invented symptom","split":"development"}\n')
            similarities = np.array([[.9, .2, .1, .3, .1, .2]])
            report = run(queries, root / "out", similarities=similarities)
            self.assertEqual(report["accepted_at_zero"], 1)
            self.assertEqual(report["query_count"], 1)
            rows = [json.loads(s) for s in
                    (root / "out/intent_margins.jsonl").read_text().splitlines()]
            self.assertEqual(rows[0]["query_id"], "p")
            self.assertNotIn("invented symptom", json.dumps(rows))
            self.assertNotIn("invented symptom", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
