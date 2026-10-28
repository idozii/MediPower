"""Unit checks on fabricated DDXPlus-shaped data; no official dataset is shipped."""

import csv
import json
from pathlib import Path
import tempfile
import unittest

from research.prepare_ddxplus import convert, evidence_phrase, parse_evidences


class DDXPlusAdapterTests(unittest.TestCase):
    def test_binary_categorical_antecedent_and_defaults(self):
        dictionary = {
            "E_A": {"question_en": "Do you wheeze?", "is_antecedent": False, "data_type": "B"},
            "E_B": {"question_en": "What color?", "is_antecedent": False, "data_type": "C",
                    "default_value": "V_0", "value_meaning": {"V_0": {"en": "NA"}, "V_1": {"en": "red"}}},
            "E_C": {"question_en": "Family history?", "is_antecedent": True, "data_type": "B"},
        }
        self.assertIn("wheeze", evidence_phrase("E_A", dictionary))
        self.assertIn("red", evidence_phrase("E_B_@_V_1", dictionary))
        self.assertIsNone(evidence_phrase("E_B_@_V_0", dictionary))
        self.assertIsNone(evidence_phrase("E_C", dictionary))
        with self.assertRaises(ValueError):
            evidence_phrase("UNKNOWN", dictionary)

    def test_safe_list_parser(self):
        self.assertEqual(parse_evidences("['E_A', 'E_B_@_V_1']"), ["E_A", "E_B_@_V_1"])
        with self.assertRaises(ValueError):
            parse_evidences("__import__('os').system('echo unsafe')")

    def test_separation_coverage_and_test_lock(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root)
            (p / "catalog.csv").write_text("disease_id,disease_name\n21,Asthma\n", encoding="utf-8")
            (p / "metadata.json").write_text(json.dumps({"E_A": {
                "question_en": "Do you wheeze?", "is_antecedent": False, "data_type": "B"
            }}), encoding="utf-8")
            (p / "mapping.csv").write_text("source_pathology,target_disease_id,review_status\nAsthma,21,approved\n", encoding="utf-8")
            with (p / "patients.csv").open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["PATHOLOGY", "EVIDENCES"])
                writer.writerow(["Asthma", "['E_A']"])
                writer.writerow(["Unknown", "['E_A']"])
            out = p / "out"
            report = convert(p / "patients.csv", p / "metadata.json", p / "mapping.csv",
                             p / "catalog.csv", out)
            self.assertEqual(report["mapped_exported_rows"], 1)
            self.assertEqual(report["unmapped_rows"], 1)
            query = json.loads((out / "queries.jsonl").read_text().splitlines()[0])
            label = json.loads((out / "gold.jsonl").read_text().splitlines()[0])
            self.assertNotIn("relevant_disease_ids", query)
            self.assertNotIn("text", label)
            self.assertEqual(label["relevant_disease_ids"], ["21"])
            with self.assertRaisesRegex(ValueError, "locked"):
                convert(p / "patients.csv", p / "metadata.json", p / "mapping.csv",
                        p / "catalog.csv", p / "test", split="test")


if __name__ == "__main__":
    unittest.main()
