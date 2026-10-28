"""M5 safety transparency regression tests; these do NOT certify medical safety."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SafetyCopyAndSchemaTests(unittest.TestCase):
    def test_both_web_surfaces_display_research_only_warning(self):
        backend = (ROOT / "app/main.py").read_text(encoding="utf-8")
        frontend = (ROOT / "web/app/page.js").read_text(encoding="utf-8")
        self.assertIn("NOT a medical diagnosis", backend)
        self.assertIn("Not a medical diagnosis", frontend)
        self.assertIn("Do not enter real patient information", backend)
        self.assertIn("Do not enter identifying or real patient health information", frontend)
        self.assertNotIn("call 911", backend)

    def test_request_bounds_and_response_notice(self):
        code = (ROOT / "app/api/routes.py").read_text(encoding="utf-8")
        for fragment in ("max_length=2000", "max_length=160",
                         "ge=-90, le=90", "ge=-180, le=180",
                         '"research_use_only": True', '"ranking_score_notice"'):
            self.assertIn(fragment, code)

    def test_research_scores_not_claimed_as_probabilities(self):
        backend = (ROOT / "app/api/routes.py").read_text(encoding="utf-8")
        self.assertIn("not medical probabilities", backend)
        frontend = (ROOT / "web/app/page.js").read_text(encoding="utf-8")
        self.assertIn("Ranking score:", frontend)


if __name__ == "__main__":
    unittest.main()
