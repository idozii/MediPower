"""W5 operational contract unit tests with synthetic responses only."""
import unittest
from unittest.mock import patch

from scripts.w5_deployment_preflight import validate_loopback, verify


class W5ReadinessTests(unittest.TestCase):
    def test_loopback_origin_rejects_tricky_hostnames_and_credentials(self):
        validate_loopback("http://127.0.0.1:3000")
        validate_loopback("http://localhost:3000")
        for bad in (
            "http://127.0.0.1:3000.evil.org",
            "http://127.0.0.1.evil.org:3000",
            "http://127.0.0.1:3000@evil.org",
            "https://127.0.0.1:3000",
            "http://localhost:3000/api/predict",
            "http://localhost:3000?query=private",
            "http://localhost:3000#fragment",
            "http://127.0.0.1",
            "http://user:pass@localhost:3000",
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_loopback(bad)

    def test_ready_requires_health_ok_and_no_store(self):
        with patch("scripts.w5_deployment_preflight.fetch_json",
                   return_value=(200, {"frontend": "ready", "backend": "ready"},
                                 {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})):
            result = verify("ready", "http://localhost:3000", timeout=0.5)
        self.assertEqual(result["status"], "PASS_OPERATIONAL_CONTRACT_ONLY")
        self.assertFalse(result["synthetic_predict_failure_checked"])

    def test_outage_health_and_predict_fail_closed(self):
        answers = [
            (503, {"frontend": "ready", "backend": "unavailable"},
             {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}),
            (502, {"detail": "Research backend could not be reached. Verify service status."},
             {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}),
        ]
        with patch("scripts.w5_deployment_preflight.fetch_json", side_effect=answers) as mock_fetch:
            result = verify("outage", "http://127.0.0.1:3000", timeout=0.5)
        self.assertTrue(result["synthetic_predict_failure_checked"])
        self.assertEqual(mock_fetch.call_count, 2)

    def test_outage_rejects_detail_leak_or_wrong_status(self):
        answers = [
            (503, {"frontend": "ready", "backend": "unavailable"},
             {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}),
            (502, {"detail": "PRIVATE_SOURCE_STACK_TRACE"},
             {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}),
        ]
        with patch("scripts.w5_deployment_preflight.fetch_json", side_effect=answers):
            with self.assertRaisesRegex(AssertionError, "exposed backend content"):
                verify("outage", "http://127.0.0.1:3000", timeout=0.5)

    def test_ready_missing_security_header_fails(self):
        with patch("scripts.w5_deployment_preflight.fetch_json",
                   return_value=(200, {"frontend": "ready", "backend": "ready"},
                                 {"Cache-Control": "no-store"})):
            with self.assertRaisesRegex(AssertionError, "MIME header"):
                verify("ready", "http://localhost:3000", timeout=0.5)


if __name__ == "__main__":
    unittest.main()
