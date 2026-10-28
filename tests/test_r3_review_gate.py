"""R3 source and ontology review structural tests; synthetic names only."""
import csv
from pathlib import Path
import tempfile
import unittest

from research.r3_review_gate import REVIEW_FIELDS, audit


def write(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


class R3OntologyReviewGateTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        self.catalog = self.root / "catalog.csv"
        self.candidates = self.root / "candidates.csv"
        self.reviewed = self.root / "reviewed.csv"
        write(self.catalog, ["disease_id", "disease_name"],
              [{"disease_id": "D01", "disease_name": "Fictional condition"}])
        write(self.candidates, ["source_pathology", "candidate_ids"],
              [{"source_pathology": "Synthetic A", "candidate_ids": "D01"},
               {"source_pathology": "Synthetic B", "candidate_ids": ""}])

    def test_missing_reviews_never_becomes_clinical_validation(self):
        report = audit(self.candidates, None, self.catalog)
        self.assertEqual(report["approved_mapping_metadata_only"], 0)
        self.assertEqual(report["mapping_review_counts"]["pending"], 2)
        self.assertTrue(report["status"].startswith("BLOCKED_"))

    def test_valid_double_review_is_metadata_only(self):
        write(self.reviewed, REVIEW_FIELDS, [{
            "source_pathology": "Synthetic A",
            "target_disease_id": "D01",
            "review_status": "approved",
            "primary_reviewer": "expertA",
            "independent_reviewer": "expertB",
            "review_evidence": "Independent comparison in source materials",
            "equivalence_type": "exact_clinical_equivalence",
        }])
        report = audit(self.candidates, self.reviewed, self.catalog)
        self.assertEqual(report["approved_mapping_metadata_only"], 1)
        self.assertEqual(report["mapping_review_counts"]["pending"], 1)
        self.assertIn("BLOCKED", report["status"])
        self.assertNotIn("Synthetic A", str(report))

    def test_one_reviewer_cannot_approve(self):
        write(self.reviewed, REVIEW_FIELDS, [{
            "source_pathology": "Synthetic A",
            "target_disease_id": "D01",
            "review_status": "approved",
            "primary_reviewer": "reviewerX",
            "independent_reviewer": "reviewerX",
            "review_evidence": "demo",
            "equivalence_type": "exact_clinical_equivalence",
        }])
        with self.assertRaisesRegex(ValueError, "two distinct"):
            audit(self.candidates, self.reviewed, self.catalog)

    def test_approximate_mapping_cannot_be_marked_approved(self):
        write(self.reviewed, REVIEW_FIELDS, [{
            "source_pathology": "Synthetic A",
            "target_disease_id": "D01",
            "review_status": "approved",
            "primary_reviewer": "R1",
            "independent_reviewer": "R2",
            "review_evidence": "Approximate string similarity",
            "equivalence_type": "broader",
        }])
        with self.assertRaisesRegex(ValueError, "equivalence rationale"):
            audit(self.candidates, self.reviewed, self.catalog)

    def test_nonapproved_mapping_must_not_point_to_target(self):
        write(self.reviewed, REVIEW_FIELDS, [{
            "source_pathology": "Synthetic A",
            "target_disease_id": "D01",
            "review_status": "pending",
            "primary_reviewer": "",
            "independent_reviewer": "",
            "review_evidence": "",
            "equivalence_type": "",
        }])
        with self.assertRaisesRegex(ValueError, "Non-approved"):
            audit(self.candidates, self.reviewed, self.catalog)


if __name__ == "__main__":
    unittest.main()
