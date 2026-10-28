"""M11 intent-evaluation tests with entirely fictional fabricated sample labels."""

import json
from pathlib import Path
import tempfile
import unittest

from research.evaluate_annotated_intent import evaluate, check_query_manifest
from research.export_intent_cohort import export
from test_m11_intent_cohort import annotated, write_csv


def mock_margin(qid: str, margin: float) -> dict:
    return {
        "query_id": qid,
        "max_symptom_similarity": margin + .4,
        "max_other_task_similarity": .4,
        "intent_margin": margin,
        "intent_accepted_at_zero": margin > 0,
    }


class ProspectiveIntentEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.gold = [
            {"query_id": "symptom", "intent_label": "symptom_information",
             "split": "development", "source_id": "a", "template_family": "ta"},
            {"query_id": "offtopic", "intent_label": "nonclinical_task",
             "split": "development", "source_id": "b", "template_family": "tb"},
            {"query_id": "uncertain", "intent_label": "ambiguous_or_mixed",
             "split": "development", "source_id": "c", "template_family": "tc"},
            {"query_id": "missing", "intent_label": "clinical_out_of_catalog",
             "split": "development", "source_id": "d", "template_family": "td"},
        ]
        self.margins = [mock_margin("symptom", -.1), mock_margin("offtopic", .2),
                        mock_margin("uncertain", -.3), mock_margin("missing", .1)]

    def test_separate_nonclinical_from_clinical_out_of_catalog(self):
        result = evaluate(self.gold, self.margins)
        self.assertEqual(result["binary_slice_count"], 2)
        self.assertEqual(result["excluded_from_binary_slice"], 2)
        self.assertEqual(result["positive_symptom_false_abstention"], 1)
        self.assertEqual(result["nonclinical_false_acceptance"], 1)
        self.assertEqual(result["by_label"]["clinical_out_of_catalog"]["acceptance_rate"], 1)
        self.assertEqual(result["by_label"]["ambiguous_or_mixed"]["accepted"], 0)

    def test_query_id_mismatch_and_test_lock(self):
        with self.assertRaisesRegex(ValueError, "must match"):
            evaluate(self.gold, self.margins[:-1])
        test = [dict(row, split="test") for row in self.gold]
        with self.assertRaisesRegex(ValueError, "locked"):
            evaluate(test, self.margins)

    def test_requires_two_binary_groups(self):
        data = [row for row in self.gold if row["intent_label"] != "nonclinical_task"]
        margins = [row for row in self.margins if row["query_id"] != "offtopic"]
        with self.assertRaisesRegex(ValueError, "both"):
            evaluate(data, margins)

    def test_development_export_separates_labels_from_queries(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "development.csv"
            write_csv(source, [
                annotated(query_id="p1"),
                annotated(query_id="n1", text="Rename a spreadsheet column",
                          source_id="b", template_family="other",
                          annotator_1_label="nonclinical_task",
                          annotator_2_label="nonclinical_task",
                          final_label="nonclinical_task"),
            ])
            result = export(source, root / "output")
            queries = [json.loads(line) for line in
                       (root / "output/queries.jsonl").read_text().splitlines()]
            labels = [json.loads(line) for line in
                      (root / "output/intent_gold.jsonl").read_text().splitlines()]
            self.assertEqual(result["rows"], 2)
            self.assertTrue(all("intent_label" not in row for row in queries))
            self.assertTrue(all("text" not in row for row in labels))
            self.assertEqual(labels[1]["intent_label"], "nonclinical_task")

    def test_manifest_mismatch_prevents_mixed_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            margin = root / "margin"
            gold = root / "gold"
            margin.mkdir()
            gold.mkdir()
            queries = root / "queries.jsonl"
            queries.write_text('{"query_id":"a","text":"fictional","split":"development"}\n')
            (margin / "manifest.json").write_text(json.dumps({
                "protocol": "medipower-m10-frozen-intent-margins-v1",
                "split": "development", "queries_sha256": "incorrect"}))
            (gold / "manifest.json").write_text(json.dumps({
                "protocol": "medipower-m11-intent-development-export-v1",
                "split": "development", "annotation_sha256": "fake"}))
            with self.assertRaisesRegex(ValueError, "hashes"):
                check_query_manifest(queries, margin / "intent_margins.jsonl",
                                     gold / "intent_gold.jsonl")


if __name__ == "__main__":
    unittest.main()
