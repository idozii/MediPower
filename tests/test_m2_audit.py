"""Auditing tests with generated non-patient text data."""

import csv
from pathlib import Path
import tempfile
import unittest

from research.audit_dataset import (
    PREFIXES, audit, duplicate_summary, overlap_stats, template_group,
)


class AuditTests(unittest.TestCase):
    def test_duplicate_counts_and_conflicting_labels(self):
        out = duplicate_summary(["x", "x", "y"], ["A", "B", "A"])
        self.assertEqual(out["extra_rows_with_duplicate_key"], 1)
        self.assertEqual(out["keys_with_conflicting_labels"], 1)

    def test_cross_split_exact_overlap(self):
        self.assertEqual(
            overlap_stats(["a", "b", "a", "c"], [0, 1], [2, 3])["test_rows_with_identical_train_input"],
            1,
        )

    def test_template_detection(self):
        self.assertEqual(template_group("I have a headache"), "I have")
        self.assertEqual(template_group("Something unexpected"), "OTHER")

    def test_audit_all_three_splits_without_model_fit(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "synthetic.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["text", "disease"])
                for label, symptom in (("A", "wheezing cough"), ("B", "tooth pain")):
                    for prefix in PREFIXES:
                        for _ in range(4):
                            writer.writerow([prefix + symptom, label])
            result = audit(path, rerun=False)
            self.assertEqual(result["rows"], 40)
            self.assertGreater(result["duplicates_model_input"]["extra_rows_with_duplicate_key"], 0)
            self.assertEqual(result["splits"]["exact_input_grouped"]["test_rows_with_identical_train_input"], 0)
            self.assertEqual(result["splits"]["held_out_sentence_prefix"]["test_rows"], 8)


if __name__ == "__main__":
    unittest.main()
