"""M8 grouping, subgroup audit and fixture integrity with invented non-patient data."""

import csv
import json
from pathlib import Path
import tempfile
import unittest

from research.compare_models import compare
from research.audit_prediction_subgroups import summarize
from research.prepare_ddxplus import convert


ROOT = Path(__file__).resolve().parents[1]


def toy(n=40, *, grouped=False):
    gold = [{"query_id": f"q{i}", "split": "development",
             "relevant_disease_ids": ["1"],
             **({"group_id": "same-source"} if grouped else {})}
            for i in range(n)]
    pred = [{"query_id": f"q{i}", "predicted_disease_ids": ["1"]}
            for i in range(n)]
    return gold, {"ref": pred, "alternative": pred}


class ClusterEvaluationTests(unittest.TestCase):
    def test_repeated_group_suppresses_spurious_n40_interval(self):
        gold, pred = toy(grouped=True)
        result = compare(gold, pred, baseline="ref", samples=100, min_ci_queries=30)
        self.assertEqual(result["positive_queries"], 40)
        self.assertEqual(result["bootstrap_unit"], "group_id")
        self.assertEqual(result["independent_resampling_units"], 1)
        self.assertFalse(result["intervals_available"])

    def test_independent_groups_enable_deterministic_group_bootstrap(self):
        gold, pred = toy()
        for i, row in enumerate(gold):
            row["group_id"] = f"source-{i}"
        a = compare(gold, pred, baseline="ref", samples=100, seed=44)
        b = compare(gold, pred, baseline="ref", samples=100, seed=44)
        self.assertTrue(a["intervals_available"])
        self.assertEqual(a["independent_resampling_units"], 40)
        self.assertEqual(a["models"], b["models"])

    def test_partial_grouping_refused(self):
        gold, pred = toy()
        gold[0]["group_id"] = "x"
        with self.assertRaisesRegex(ValueError, "Every positive query"):
            compare(gold, pred, baseline="ref", samples=100)


class SubgroupAuditTests(unittest.TestCase):
    def test_challenge_gold_is_safe_separate_and_complete(self):
        queries = [json.loads(s) for s in (ROOT / "research/examples/abstention_stress_v1_queries.jsonl").read_text().splitlines()]
        gold = [json.loads(s) for s in (ROOT / "research/examples/abstention_stress_v1_gold.jsonl").read_text().splitlines()]
        self.assertEqual(len(queries), 30)
        self.assertEqual({r["query_id"] for r in queries}, {r["query_id"] for r in gold})
        self.assertFalse(any("relevant_disease_ids" in r for r in queries))
        self.assertFalse(any("text" in r for r in gold))
        self.assertEqual(sum(bool(r["relevant_disease_ids"]) for r in gold), 10)
        self.assertEqual(sum(r.get("expected_abstain") is True for r in gold), 20)
        self.assertTrue(all(r.get("annotation_type") == "developer_authored_illustrative_not_clinical"
                            for r in gold))

    def test_subgroup_errors_are_counted_separately(self):
        gold = [
            {"query_id": "p", "split": "development", "subgroup": "symptoms",
             "relevant_disease_ids": ["1"]},
            {"query_id": "n", "split": "development", "subgroup": "nonclinical",
             "relevant_disease_ids": [], "expected_abstain": True}
        ]
        model = [{"query_id": "p", "predicted_disease_ids": []},
                 {"query_id": "n", "predicted_disease_ids": ["1"]}]
        result = summarize(gold, {"model": model}, k=1)
        rows = result["models"]["model"]
        self.assertEqual(rows["symptoms"]["positive_abstention_rate"], 1.0)
        self.assertIsNone(rows["symptoms"]["negative_false_positive_rate"])
        self.assertEqual(rows["nonclinical"]["negative_false_positive_rate"], 1.0)
        self.assertIsNone(rows["nonclinical"]["positive_abstention_rate"])

    def test_test_split_rejected(self):
        gold = [{"query_id": "p", "split": "test", "subgroup": "positive",
                 "relevant_disease_ids": ["1"]}]
        model = [{"query_id": "p", "predicted_disease_ids": ["1"]}]
        with self.assertRaisesRegex(ValueError, "locked"):
            summarize(gold, {"model": model})


class ExternalQueryClusterTests(unittest.TestCase):
    def test_duplicate_evidence_text_has_same_group_id(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root)
            (p / "catalog.csv").write_text("disease_id,disease_name\n21,Asthma\n")
            (p / "mapping.csv").write_text("source_pathology,target_disease_id,review_status\nAsthma,21,approved\n")
            (p / "evidence.json").write_text(json.dumps({"E_A": {
                "question_en": "Do you wheeze?", "is_antecedent": False, "data_type": "B"}}))
            with (p / "validate.csv").open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["PATHOLOGY", "EVIDENCES"])
                writer.writerow(["Asthma", "['E_A']"])
                writer.writerow(["Asthma", "['E_A']"])
            convert(p / "validate.csv", p / "evidence.json", p / "mapping.csv",
                    p / "catalog.csv", p / "out")
            gold = [json.loads(s) for s in (p / "out/gold.jsonl").read_text().splitlines()]
            self.assertEqual(len(gold), 2)
            self.assertNotEqual(gold[0]["query_id"], gold[1]["query_id"])
            self.assertEqual(gold[0]["group_id"], gold[1]["group_id"])


if __name__ == "__main__":
    unittest.main()
