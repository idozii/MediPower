"""M9 prototype-intent and two-stage gate regression tests; no model downloads."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from research.export_intent_ablations import (
    apply_gates, intent_decision, run,
)


class IntentDecisionTests(unittest.TestCase):
    def test_zero_shot_intent_margin_vs_two_classes(self):
        prototypes = np.array([
            [.8, .75, .7, .2, .3, .1],  # symptom-oriented
            [.2, .15, .3, .9, .8, .7], # unrelated-task-oriented
            [.5, .4, .3, .5, .1, .2],  # ambiguous tie abstains by default
        ])
        accepted, difference = intent_decision(prototypes)
        self.assertEqual(accepted.tolist(), [True, False, False])
        self.assertEqual(len(difference), 3)

    def test_reject_missing_or_malformed_prototypes_and_thresholds(self):
        for invalid in (np.ones((1, 2, 3)), np.ones((2, 1)), np.array([[float("nan"), 1.]])):
            with self.assertRaises(ValueError):
                intent_decision(invalid, positive_prototype_count=1)
        with self.assertRaises(ValueError):
            intent_decision(np.array([[.2, .1]]), positive_prototype_count=1, margin=-.1)


class IntentGateTests(unittest.TestCase):
    def test_can_reject_lexical_overlap_and_accept_positive(self):
        sparse = np.array([[.8, .4], [.5, .3]])
        dense = np.array([[.6, .4], [.8, .6]])
        accepted = np.array([False, True])
        result = apply_gates(["1", "2"], sparse, dense, accepted)
        self.assertEqual(result["hybrid_intent_gate"][0], [])
        self.assertEqual(result["dense_intent_gate"][0], [])
        self.assertNotEqual(result["hybrid_intent_gate"][1], [])
        self.assertNotEqual(result["hybrid_intent_and_lexical_gate"][1], [])

    def test_semantic_intent_gate_can_retain_zero_overlap_paraphrase(self):
        sparse = np.zeros((1, 2))
        dense = np.array([[.9, .5]])
        result = apply_gates(["1", "2"], sparse, dense, np.array([True]))
        self.assertEqual(result["hybrid_intent_gate"][0], ["1", "2"])
        self.assertEqual(result["hybrid_intent_and_lexical_gate"][0], [])

    def test_false_intent_rejection_could_hide_true_symptom(self):
        sparse = np.array([[.7, .1]])
        dense = np.array([[.8, .1]])
        result = apply_gates(["1", "2"], sparse, dense, np.array([False]))
        self.assertEqual(result["hybrid_intent_gate"], [[]])

    def test_invalid_shape_rejected(self):
        with self.assertRaises(ValueError):
            apply_gates(["1"], np.zeros((2, 2)), np.ones((2, 2)), np.array([True, True]))


class IntentExporterTests(unittest.TestCase):
    def test_export_reproducible_outputs_with_mocked_embedding_scores(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "catalog.csv").write_text(
                "disease_id,disease_name,description,mapped_departments\n1,Asthma,wheezing,pulmonology\n2,Pneumonia,fever,pulmonology\n")
            (root / "queries.jsonl").write_text(
                '{"query_id":"p","text":"I am wheezing","split":"development"}\n'
                '{"query_id":"n","text":"Software header asthma","split":"development"}\n')
            intent_sims = np.array([
                [.8, .7, .6, .3, .2, .1],
                [.3, .2, .1, .8, .7, .6],
            ])
            sparse = np.array([[.5, .1], [.8, .1]])
            dense = np.array([[.8, .3], [.9, .1]])
            with patch("research.export_intent_ablations.compute_intent_similarities", return_value=intent_sims), patch(
                "research.export_intent_ablations.tfidf_scores", return_value=sparse
            ), patch("research.export_intent_ablations.dense_scores", return_value=dense):
                report = run(root / "queries.jsonl", root / "catalog.csv", root / "out")
            self.assertEqual(report["intent_accepted"], 1)
            self.assertEqual(report["intent_rejected"], 1)
            rows = [json.loads(x) for x in
                    (root / "out/hybrid_intent_gate.jsonl").read_text().splitlines()]
            self.assertEqual(rows[0]["predicted_disease_ids"][0], "1")
            self.assertEqual(rows[1]["predicted_disease_ids"], [])
            self.assertNotIn("Software header", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
