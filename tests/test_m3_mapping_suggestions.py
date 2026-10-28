"""Ontology suggestions must never silently approve clinical equivalence."""

import unittest

from research.suggest_ddxplus_mappings import candidates


class MappingSuggestionTests(unittest.TestCase):
    def test_never_auto_approves(self):
        catalog = [
            {"disease_id": "1", "disease_name": "Asthma"},
            {"disease_id": "2", "disease_name": "Migraine"},
        ]
        suggested = candidates({"SomeCondition": {"condition_name": "Asthma"}}, catalog)
        self.assertEqual(suggested[0]["review_status"], "pending")
        self.assertEqual(suggested[0]["target_disease_id"], "")
        self.assertEqual(suggested[0]["candidate_ids"], "1 | 2")

    def test_rejects_duplicate_conditions(self):
        with self.assertRaisesRegex(ValueError, "duplicated"):
            candidates([{"condition_name": "A"}, {"condition_name": "A"}],
                       [{"disease_id": "1", "disease_name": "A"}])


if __name__ == "__main__":
    unittest.main()
