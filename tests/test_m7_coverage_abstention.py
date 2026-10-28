"""Data governance and experimental abstention tests on synthetic fixtures only."""
from __future__ import annotations

import csv
from pathlib import Path
import tempfile
import unittest

import numpy as np

from research.audit_ddxplus_coverage import audit
from research.export_abstention_ablations import gated_rankings


class OntologyCoverageTests(unittest.TestCase):
    def test_pending_only_aggregate_coverage_and_review_worksheet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            validation = root / "validate.csv"
            with validation.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["PATHOLOGY", "EVIDENCES"])
                writer.writerow(["Condition A", "['E1']"])
                writer.writerow(["Condition B", "['E2']"])
                writer.writerow(["Condition A", "['E1']"])
            candidates = root / "candidate.csv"
            with candidates.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["source_pathology", "review_status", "candidate_ids", "candidate_names"])
                writer.writerow(["Condition A", "pending", "1", "Similar A"])
                writer.writerow(["Condition B", "pending", "2", "Similar B"])
            catalog = root / "catalog.csv"
            catalog.write_text("disease_id,disease_name\n1,Similar A\n2,Similar B\n")
            report = audit(validation, candidates, catalog, root / "out")
            self.assertEqual(report["validation_rows_sampled"], 3)
            self.assertEqual(report["source_pathologies_observed"], 2)
            self.assertIsNone(report["mapping_coverage"])
            with (root / "out/ontology_review_worksheet.csv").open() as f:
                worksheet = list(csv.DictReader(f))
            self.assertEqual(worksheet[0]["validation_count"], "2")
            self.assertEqual(worksheet[0]["review_status"], "pending")
            self.assertEqual(worksheet[0]["proposed_target_disease_id"], "")

    def test_reject_approved_suggestions_or_test_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "catalog.csv").write_text("disease_id,disease_name\n1,A\n")
            (root / "candidates.csv").write_text("source_pathology,review_status\nA,approved\n")
            (root / "validate.csv").write_text("PATHOLOGY,EVIDENCES\nA,E1\n")
            with self.assertRaisesRegex(ValueError, "PENDING"):
                audit(root / "validate.csv", root / "candidates.csv",
                      root / "catalog.csv", root / "out")
            with self.assertRaisesRegex(ValueError, "Only the development"):
                audit(root / "release_test_patients.csv", root / "candidates.csv",
                      root / "catalog.csv", root / "out")


class AbstentionAblationTests(unittest.TestCase):
    def test_nonclinical_zero_overlap_gate_but_positive_kept(self):
        sparse = np.array([[0, 0], [.4, 0.]])
        dense = np.array([[.8, .6], [.2, .5]])
        predictions = gated_rankings(sparse, dense, ["1", "2"])
        for name in ("dense_lexical_gate", "hybrid_lexical_gate"):
            self.assertEqual(predictions[name][0], [])
            self.assertNotEqual(predictions[name][1], [])

    def test_gate_rejects_legitimate_zero_lexical_paraphrase(self):
        # Failure mode: a truly relevant paraphrase can have no catalog token overlap.
        sparse = np.array([[0., 0.]])
        dense = np.array([[.9, .1]])
        out = gated_rankings(sparse, dense, ["1", "2"])
        self.assertEqual(out["dense_lexical_gate"][0], [])
        self.assertEqual(out["hybrid_lexical_gate"][0], [])

    def test_invalid_gate_inputs_are_rejected(self):
        sparse = np.array([[.1, .2]])
        dense = np.array([[.1, .2]])
        with self.assertRaises(ValueError):
            gated_rankings(sparse, dense, ["1"], min_lexical=.5)
        with self.assertRaises(ValueError):
            gated_rankings(sparse, dense, ["1", "2"], min_lexical=-.1)


if __name__ == "__main__":
    unittest.main()
