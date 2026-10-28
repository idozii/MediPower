"""R4 nonclinical diagnostic tests from fabricated intent annotations."""
import unittest

from research.r4_selective_intent_analysis import (
    analyse, group_bootstrap, measure, prepare_records,
)


def cohort():
    gold = [
        {"query_id": "a", "split": "development", "intent_label": "symptom_information",
         "source_id": "author_a", "template_family": "symptom_a"},
        {"query_id": "b", "split": "development", "intent_label": "symptom_information",
         "source_id": "author_b", "template_family": "symptom_b"},
        {"query_id": "c", "split": "development", "intent_label": "nonclinical_task",
         "source_id": "author_c", "template_family": "coding"},
        {"query_id": "d", "split": "development", "intent_label": "nonclinical_task",
         "source_id": "author_d", "template_family": "writing"},
        {"query_id": "e", "split": "development", "intent_label": "clinical_out_of_catalog",
         "source_id": "author_e", "template_family": "open_set"},
    ]
    values = {"a": 0.03, "b": -0.02, "c": 0.01, "d": -0.07, "e": -0.06}
    margins = [
        {"query_id": qid, "intent_margin": margin,
         "max_symptom_similarity": 0.5 + margin,
         "max_other_task_similarity": 0.5}
        for qid, margin in values.items()
    ]
    return gold, margins


class R4DevelopmentSelectiveIntentTests(unittest.TestCase):
    def test_risk_coverage_explicitly_counts_positive_abstentions(self):
        gold, margins = cohort()
        data = measure(prepare_records(gold, margins), 0.0)
        self.assertEqual(data["positive_retention"], 0.5)
        self.assertEqual(data["positive_false_abstention"], 0.5)
        self.assertEqual(data["nonclinical_false_acceptance"], 0.5)
        self.assertEqual(data["binary_coverage"], 0.5)
        self.assertEqual(data["binary_error_fraction"], 0.5)

    def test_out_of_catalog_is_not_an_unrelated_negative(self):
        gold, margins = cohort()
        result = measure(prepare_records(gold, margins), -0.05)
        self.assertEqual(result["binary_count"], 4)
        self.assertEqual(result["other_labels"]["clinical_out_of_catalog"]["count"], 1)
        self.assertEqual(result["other_labels"]["clinical_out_of_catalog"]["accepted"], 0)

    def test_test_access_is_locked(self):
        gold, margins = cohort()
        gold[0]["split"] = "test"
        with self.assertRaisesRegex(ValueError, "TEST split is LOCKED"):
            analyse(gold, margins, bootstrap_repeats=15)

    def test_margin_and_id_integrity(self):
        gold, margins = cohort()
        margins[0]["intent_margin"] = 100
        with self.assertRaisesRegex(ValueError, "margin"):
            prepare_records(gold, margins)
        gold, margins = cohort()
        margins.pop()
        with self.assertRaisesRegex(ValueError, "match exactly"):
            prepare_records(gold, margins)

    def test_seeded_source_group_bootstrap_is_reproducible(self):
        gold, margins = cohort()
        rows = prepare_records(gold, margins)
        first = group_bootstrap(rows, (-0.05, 0.0), repeats=50, seed=42)
        second = group_bootstrap(rows, (-0.05, 0.0), repeats=50, seed=42)
        self.assertEqual(first, second)
        self.assertEqual(first["resampling_unit"], "source_id")
        self.assertEqual(first["distinct_source_groups"], 5)
        self.assertGreater(first["thresholds"]["0.0"]["valid_resamples"], 0)

    def test_evaluation_only_does_not_select_best_threshold(self):
        gold, margins = cohort()
        result = analyse(gold, margins, bootstrap_repeats=15)
        self.assertEqual(result["split"], "development")
        self.assertEqual(len(result["thresholds"]), 3)
        self.assertNotIn("best_threshold", result)
        self.assertTrue(result["status"].startswith("EXPLORATORY_"))
        self.assertTrue(any("not independent" in note for note in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
