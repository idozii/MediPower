"""Nonclinical contract checks for Phase 1 live smoke assertions."""
import unittest

from scripts.smoke_phase1 import validate_result


def valid_payload():
    facility = {
        "score": 0.6,
        "ranking_explanation": {
            "score_kind": "experimental_ranking_score_not_probability",
            "features": {"straight_line_distance_km": 1.2, "experimental_total": 0.6},
            "disclosure": "Example metrics not independently verified",
        },
    }
    return {
        "research_use_only": True,
        "ranking_score_notice": "Scores are retrieval heuristics, not medical probabilities or clinical advice.",
        "retrieval_mode": "offline_tfidf_forced",
        "diseases": [{"disease_name": "Fictional syndrome"}],
        "recommendations": [facility],
        "recommendations_by_disease": {"Fictional syndrome": [facility]},
        "resolved_location": {"source": "direct_coordinates", "lat": -33.8688, "lon": 151.2093},
    }


class Phase1SmokeContractTest(unittest.TestCase):
    def test_complete_proxy_payload(self):
        summary = validate_result(valid_payload())
        self.assertEqual(summary["explained_facility_count"], 1)
        self.assertEqual(summary["condition_count"], 1)

    def test_research_boundary_cannot_be_removed(self):
        payload = valid_payload()
        payload["research_use_only"] = False
        with self.assertRaisesRegex(AssertionError, "scope flag"):
            validate_result(payload)

    def test_facility_disclosure_cannot_be_removed(self):
        payload = valid_payload()
        del payload["recommendations_by_disease"]["Fictional syndrome"][0]["ranking_explanation"]
        with self.assertRaisesRegex(AssertionError, "W2 explanation"):
            validate_result(payload)

    def test_missing_condition_no_match_remains_valid(self):
        payload = valid_payload()
        payload["diseases"] = []
        payload["recommendations"] = []
        payload["recommendations_by_disease"] = {}
        result = validate_result(payload)
        self.assertEqual(result["condition_count"], 0)
        self.assertEqual(result["explained_facility_count"], 0)


if __name__ == "__main__":
    unittest.main()
