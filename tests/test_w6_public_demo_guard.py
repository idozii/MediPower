"""Public sample-only demo restrictions; never use real health details."""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from app.main import app
from app.utils.demo_guard import DEMO_SCENARIOS, is_public_demo_request


class PublicDemoGuardTests(unittest.TestCase):
    def test_known_fictional_scenarios_are_accepted(self):
        self.assertEqual(len(DEMO_SCENARIOS), 3)
        for text, location, top_k in DEMO_SCENARIOS:
            self.assertTrue(is_public_demo_request(text, location, top_k, None, None))

    def test_unlisted_or_precise_coordinates_are_denied(self):
        self.assertFalse(is_public_demo_request("patient-identifying story", "Sydney CBD", 5, None, None))
        text, location, top_k = next(iter(DEMO_SCENARIOS))
        self.assertFalse(is_public_demo_request(text, location, top_k, -33.86, 151.2))
        self.assertFalse(is_public_demo_request(text, "Private address", top_k, None, None))
        self.assertFalse(is_public_demo_request(text, location, 20, None, None))

    def test_public_route_denies_non_preset_before_model_initialization(self):
        with patch("app.api.routes.MEDIPOWER_DEMO_PRESETS_ONLY", True), \
             patch("app.api.routes.get_disease_service",
                   side_effect=AssertionError("Model should not be initialized")):
            response = TestClient(app).post("/predict", json={
                "text": "fictional cough in a completely custom scenario",
                "location": "Sydney CBD", "top_k": 5,
            })
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("fictional cough", response.text)

    def test_extra_json_fields_are_rejected_without_echoing_private_text(self):
        text, location, top_k = sorted(DEMO_SCENARIOS)[0]
        response = TestClient(app).post("/predict", json={
            "text": text, "location": location, "top_k": top_k,
            "private_note": "FICTIONAL_MARKER_MUST_NOT_ECHO",
        })
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("FICTIONAL_MARKER_MUST_NOT_ECHO", response.text)

    def test_public_route_accepts_valid_preset_and_retains_scope(self):
        class Retriever:
            def get_diseases(self, text, top_k):
                return []
            def get_mode(self):
                return "offline_tfidf_forced"

        class Ranker:
            def recommend(self, *args, **kwargs):
                raise AssertionError("No conditions should call the ranker")

        text, location, top_k = sorted(DEMO_SCENARIOS)[0]
        with patch("app.api.routes.MEDIPOWER_DEMO_PRESETS_ONLY", True), \
             patch("app.api.routes.get_disease_service", return_value=Retriever()), \
             patch("app.api.routes.get_recommendation_service", return_value=Ranker()):
            response = TestClient(app).post("/predict", json={
                "text": text, "location": location, "top_k": top_k,
            })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["research_use_only"])


if __name__ == "__main__":
    unittest.main()
