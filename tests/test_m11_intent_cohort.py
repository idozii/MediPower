"""M11 structural preflight tests with invented, non-patient annotation fixtures."""

import csv
import json
from pathlib import Path
import tempfile
import unittest

from research.validate_intent_cohort import audit, compare_splits, REQUIRED


def annotated(**overrides):
    row = {
        "query_id": "example-1",
        "text": "I am describing a fictional fever and cough",
        "split": "development",
        "source_id": "author-1",
        "template_family": "freeform-A",
        "source_origin": "fictional local sample",
        "rights_basis": "original_synthetic_with_permission",
        "annotator_1_id": "reviewer-A",
        "annotator_1_label": "symptom_information",
        "annotator_2_id": "reviewer-B",
        "annotator_2_label": "symptom_information",
        "final_label": "symptom_information",
        "adjudicator_id": "",
    }
    row.update(overrides)
    return row


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=REQUIRED)
        writer.writeheader()
        writer.writerows(rows)


class ProspectiveAnnotationTests(unittest.TestCase):
    def test_valid_development_cohort_aggregate_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "development.csv"
            write_csv(path, [
                annotated(),
                annotated(query_id="other-2", text="How to rename a column in Python?",
                          source_id="author-2", template_family="freeform-B",
                          annotator_1_label="nonclinical_task",
                          annotator_2_label="nonclinical_task",
                          final_label="nonclinical_task"),
            ])
            result, detail = audit(path)
            self.assertEqual(result["rows"], 2)
            self.assertEqual(result["raw_agreement_fraction"], 1)
            self.assertEqual(result["adjudicated_disagreement_count"], 0)
            self.assertEqual(result["duplicate_normalized_text_rows"], 0)
            self.assertEqual(result["adjudicated_label_counts"]["symptom_information"], 1)
            self.assertEqual(len(detail["text_hashes"]), 2)
            self.assertNotIn("fictional fever", json.dumps(result))

    def test_disagreement_requires_separate_third_adjudicator(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "dev.csv"
            row = annotated(
                annotator_2_label="ambiguous_or_mixed",
                final_label="ambiguous_or_mixed")
            write_csv(path, [row])
            with self.assertRaisesRegex(ValueError, "distinct third"):
                audit(path)
            row["adjudicator_id"] = "reviewer-C"
            write_csv(path, [row])
            result, _ = audit(path)
            self.assertEqual(result["raw_agreement_fraction"], 0)
            self.assertEqual(result["adjudicated_disagreement_count"], 1)

    def test_bad_rights_and_duplicate_ids_and_reviewer_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "development.csv"
            write_csv(path, [annotated(rights_basis="unknown")])
            with self.assertRaisesRegex(ValueError, "rights"):
                audit(path)
            write_csv(path, [annotated(annotator_2_id="reviewer-A")])
            with self.assertRaisesRegex(ValueError, "distinct"):
                audit(path)
            write_csv(path, [annotated(), annotated()])
            with self.assertRaisesRegex(ValueError, "Duplicate query ID"):
                audit(path)

    def test_undefined_labels_rejected_without_auto_converting_to_negative(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "development.csv"
            write_csv(path, [annotated(final_label="unknown_disease")])
            with self.assertRaisesRegex(ValueError, "Invalid"):
                audit(path)

    def test_official_test_gate_before_file_read(self):
        path = Path("/nonexistent/private/official_test.csv")
        with self.assertRaisesRegex(ValueError, "locked"):
            audit(path, required_split="test")
        with self.assertRaisesRegex(ValueError, "approved-protocol"):
            audit(path, required_split="test", allow_test=True)

    def test_test_audit_requires_frozen_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            test = root / "test.csv"
            write_csv(test, [annotated(
                query_id="test-1", text="How can I rename a worksheet?",
                split="test", source_id="author-T", template_family="style-T",
                annotator_1_label="nonclinical_task",
                annotator_2_label="nonclinical_task",
                final_label="nonclinical_task")])
            protocol = root / "approval.json"
            protocol.write_text(json.dumps({
                "status": "pending",
                "authorizer": "qualified-reviewer",
                "protocol_id": "test-frozen-001",
                "approval_date": "2026-10-28"}))
            with self.assertRaisesRegex(ValueError, "approved_and_frozen"):
                audit(test, required_split="test", allow_test=True,
                      approved_protocol=protocol)
            json_doc = json.loads(protocol.read_text())
            json_doc["status"] = "approved_and_frozen"
            protocol.write_text(json.dumps(json_doc))
            report, _ = audit(test, required_split="test", allow_test=True,
                              approved_protocol=protocol)
            self.assertEqual(report["rows"], 1)
            self.assertEqual(report["split"], "test")

    def test_exact_duplicate_source_and_template_leakage_rejected(self):
        dev = {"query_ids": {"x"}, "source_ids": {"s1"},
               "template_families": {"T1"}, "text_hashes": {"abc"}}
        good_test = {"query_ids": {"y"}, "source_ids": {"s2"},
                     "template_families": {"T2"}, "text_hashes": {"def"}}
        self.assertTrue(compare_splits(dev, good_test)["split_disjoint"])
        for field in ("query_ids", "source_ids", "template_families", "text_hashes"):
            test = {key: set(value) for key, value in good_test.items()}
            test[field] = set(dev[field])
            with self.assertRaisesRegex(ValueError, "leakage"):
                compare_splits(dev, test)

    def test_normalized_duplicates_counted(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "dev.csv"
            write_csv(path, [
                annotated(query_id="a", text="Cough, fever!"),
                annotated(query_id="b", text="cough fever",
                          source_id="different", template_family="other"),
            ])
            report, _ = audit(path)
            self.assertEqual(report["duplicate_normalized_text_rows"], 1)


if __name__ == "__main__":
    unittest.main()
