"""Check that M3 source preflight avoids patient-level output."""

import csv
import json
from pathlib import Path
import tempfile
import unittest

from research.m3_source_preflight import inspect


class SourcePreflightTests(unittest.TestCase):
    def test_fake_validation_file_and_checksum_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            e = p / "release_evidences.json"
            c = p / "release_conditions.json"
            q = p / "validate.csv"
            e.write_text(json.dumps({"E_1": {"question_en": "Wheeze?", "data_type": "B"}}))
            c.write_text(json.dumps({"Asthma": {"condition_name": "Asthma"}}))
            with q.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["PATHOLOGY", "EVIDENCES"])
                writer.writerow(["Asthma", "['E_1']"])
            result = inspect(q, e, c)
            self.assertEqual(result["validation_rows"], 1)
            self.assertEqual(result["metadata_condition_types"], 1)
            self.assertEqual(result["unknown_evidence_code_count_first_250"], 0)
            self.assertNotIn("wheeze", json.dumps(result).lower())
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                inspect(q, e, c, expected_patients_sha256="0" * 64)


if __name__ == "__main__":
    unittest.main()
