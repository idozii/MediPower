"""W4 HTTP privacy regression: synthetic markers only, never personal data."""
import unittest

from fastapi.testclient import TestClient
from app.main import app


class W4HTTPPrivacyBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=True)

    def test_rejected_symptom_is_never_reflected_in_validation_response(self):
        marker = "DEMO_MARKER_NEVER_REFLECT_THIS_TEXT"
        response = self.client.post("/predict", json={
            "text": marker * 80, "lat": 0, "lon": 0,
        })
        self.assertEqual(response.status_code, 422)
        self.assertNotIn(marker, response.text)
        self.assertEqual(response.json()["detail"],
                         "Invalid research request. Check fictional symptom length, location and top_k.")
        self.assertEqual(response.headers.get("Cache-Control"), "no-store")

    def test_rejected_location_is_never_reflected(self):
        marker = "FICTIONAL_LOCATION_MARKER_"
        response = self.client.post("/predict", json={
            "text": "fictional fever and cough", "location": marker * 20,
        })
        self.assertEqual(response.status_code, 422)
        self.assertNotIn(marker, response.text)

    def test_malformed_json_does_not_echo_submitted_input(self):
        marker = "PRIVATE_STUDY_MARKER"
        response = self.client.post("/predict",
                                    content=f'{{"text":"{marker}"',
                                    headers={"content-type": "application/json"})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn(marker, response.text)

    def test_health_and_invalid_requests_have_no_store_and_security_headers(self):
        for response in (
            self.client.get("/health"),
            self.client.post("/predict", json={"text": "x", "lat": 0, "lon": 0}),
        ):
            self.assertEqual(response.headers.get("Cache-Control"), "no-store")
            self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
            self.assertEqual(response.headers.get("Referrer-Policy"), "no-referrer")
            self.assertEqual(response.headers.get("X-Frame-Options"), "DENY")

    def test_health_does_not_require_semantic_model(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy"})


if __name__ == "__main__":
    unittest.main()
