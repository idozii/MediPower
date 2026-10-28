"""M6 report generator tests, using explicitly fabricated toy evaluation numbers."""

import unittest

from research.build_research_report import render


def fake_comparison(split="development"):
    metrics = {
        "recall@3": {"mean": 0.5, "ci95": None},
        "mrr@3": {"mean": 0.4, "ci95": None},
        "ndcg@3": {"mean": 0.6, "ci95": None},
    }
    return {
        "protocol": "medipower-m4-paired-bootstrap-v1",
        "split": split, "positive_queries": 3, "negative_controls": 0,
        "baseline": "tfidf", "k": 3, "bootstrap_samples": 100,
        "models": {"tfidf": {"positive_metrics": metrics, "difference_vs_baseline": {
            key: {"mean": 0.0, "ci95": None} for key in metrics
        }, "negative_false_positive_rate": None, "negative_control_n": 0}},
    }


class ResearchPaperDraftTests(unittest.TestCase):
    def test_no_development_results_claim_submission_readiness(self):
        text = render(fake_comparison())
        self.assertIn("DEVELOPMENT-ONLY — NOT SUBMISSION-READY", text)
        self.assertIn("NOT diagnosis accuracy", text)
        self.assertIn("CI unavailable", text)

    def test_test_results_still_need_provenance_audit(self):
        text = render(fake_comparison(split="test"))
        self.assertIn("UNVERIFIED TEST RESULTS", text)

    def test_refuse_unsupported_input(self):
        bad = fake_comparison()
        bad["protocol"] = "unrecognized"
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            render(bad)


if __name__ == "__main__":
    unittest.main()
