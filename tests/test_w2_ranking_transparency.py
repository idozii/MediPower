import unittest
from app.services.ranking_transparency import explain_facility_ranking, annotate_ranked_facilities

class FacilityTransparencyTests(unittest.TestCase):
    def test_demo_provenance_and_zero_values(self):
        v = explain_facility_ranking({"score": 0.6, "drop_rate": 0.0, "distance_km": 0}, matrix_enabled=False)
        self.assertEqual(v["source_type"], "local_demo_provider_table")
        self.assertEqual(v["features"]["drop_fraction"], 0)
        self.assertEqual(v["features"]["straight_line_distance_km"], 0)
        self.assertIn("not independently verified", v["disclosure"])

    def test_imported_and_proxy_differ(self):
        a = explain_facility_ranking({"retention_source": "diagnosis_retention"}, matrix_enabled=True)
        b = explain_facility_ranking({"retention_source": "baseline_proxy"}, matrix_enabled=True)
        self.assertNotEqual(a["source_type"], b["source_type"])

    def test_annotation_does_not_mutate_source(self):
        rows = [{"score": 0.5, "provider_score": 0.4}]
        res = annotate_ranked_facilities(rows, matrix_enabled=True)
        self.assertEqual(res[0]["score"], 0.5)
        self.assertNotIn("ranking_explanation", rows[0])

    def test_missing_values_not_fabricated(self):
        x = explain_facility_ranking({"score": float("nan"), "distance_km": -1}, matrix_enabled=True)
        self.assertIsNone(x["features"]["experimental_total"])
        self.assertIsNone(x["features"]["straight_line_distance_km"])
