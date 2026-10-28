"""W4 regression: no network egress for geocoding unless explicitly opted in.

All locations are fictitious test examples or common cities. Tests mock
external requests; no user text is sent to an outside service.
"""
import json
import unittest
from unittest.mock import MagicMock, patch

from app.utils import geocoding


class PrivacyByDefaultGeocodingTests(unittest.TestCase):
    def setUp(self):
        geocoding._geocode_cached.cache_clear()

    def tearDown(self):
        geocoding._geocode_cached.cache_clear()

    def test_unknown_freeform_location_never_leaves_process_by_default(self):
        with patch.object(geocoding, "ALLOW_EXTERNAL_GEOCODING", False), \
             patch.object(geocoding, "urlopen", side_effect=AssertionError("Unexpected external network request")):
            self.assertIsNone(geocoding.geocode_location("invented place in unknown district"))

    def test_known_city_lookup_stays_local_without_echoing_location_text(self):
        with patch.object(geocoding, "ALLOW_EXTERNAL_GEOCODING", False), \
             patch.object(geocoding, "urlopen", side_effect=AssertionError("Unexpected network")):
            resolved = geocoding.geocode_location("Sydney CBD")
            self.assertEqual(resolved["source"], "known_map")
            self.assertNotIn("query", resolved)
            self.assertAlmostEqual(resolved["lat"], -33.8688, places=4)

    def test_numeric_coordinates_stay_local(self):
        with patch.object(geocoding, "ALLOW_EXTERNAL_GEOCODING", False), \
             patch.object(geocoding, "urlopen", side_effect=AssertionError("Unexpected network")):
            resolved = geocoding.geocode_location("-33.86, 151.20")
            self.assertEqual(resolved["source"], "parsed")
            self.assertNotIn("query", resolved)

    def test_explicit_opt_in_can_invoke_mocked_external_geocoder(self):
        response = MagicMock()
        response.read.return_value = json.dumps([{"lat": "-33.87", "lon": "151.20"}]).encode()
        context = MagicMock()
        context.__enter__.return_value = response
        with patch.object(geocoding, "ALLOW_EXTERNAL_GEOCODING", True), \
             patch.object(geocoding, "urlopen", return_value=context) as network:
            resolved = geocoding.geocode_location("invented public square")
            self.assertEqual(resolved["source"], "nominatim")
            self.assertNotIn("query", resolved)
            self.assertEqual(network.call_count, 1)

    def test_cached_nonexternal_failure_does_not_poison_explicit_opt_in(self):
        place = "fictional remote location 2026"
        response = MagicMock()
        response.read.return_value = b'[{"lat": "1.1", "lon": "2.2"}]'
        context = MagicMock()
        context.__enter__.return_value = response
        with patch.object(geocoding, "ALLOW_EXTERNAL_GEOCODING", False):
            self.assertIsNone(geocoding.geocode_location(place))
        with patch.object(geocoding, "ALLOW_EXTERNAL_GEOCODING", True), \
             patch.object(geocoding, "urlopen", return_value=context):
            self.assertEqual(geocoding.geocode_location(place)["source"], "nominatim")


if __name__ == "__main__":
    unittest.main()
