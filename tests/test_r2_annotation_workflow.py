"""R2: synthetic source and review packet workflow tests; no real cohort."""

import csv
from pathlib import Path
import tempfile
import unittest

from research.r2_annotation_packets import prepare, SOURCE_FIELDS
from research.r2_reconcile_annotations import reconcile


def write_csv(path: Path, columns, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def source_row(qid, text, source):
    return {
        "query_id": qid, "text": text, "split": "development",
        "source_id": source, "template_family": f"family-{source}",
        "source_origin": "fabricated test sample",
        "rights_basis": "original_synthetic_with_permission",
    }


def fill_packet(path: Path, annotator: str, labels: dict[str, str]):
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        row["annotator_id"] = annotator
        row["intent_label"] = labels[row["query_id"]]
    write_csv(path, rows[0].keys(), rows)


class R2HumanAnnotationWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base / "sources.csv"
        write_csv(self.source, SOURCE_FIELDS, [
            source_row("a", "Fictional ankle injury with swelling", "writer-1"),
            source_row("b", "How to rename a data column", "writer-2"),
        ])

    def test_prepare_keeps_gold_blank_and_separates_reviewer_packets(self):
        report = prepare(self.source, self.base / "packets",
                         known_queries=self.base / "no_prior_queries.jsonl")
        self.assertEqual(report["rows"], 2)
        for name in ("reviewer_A_packet.csv", "reviewer_B_packet.csv"):
            with (self.base / "packets" / name).open() as f:
                rows = list(csv.DictReader(f))
            self.assertEqual({r["query_id"] for r in rows}, {"a", "b"})
            self.assertTrue(all(not r["annotator_id"] and not r["intent_label"] for r in rows))
            self.assertTrue(all("source_id" not in r for r in rows))

    def test_two_reviewers_consensus_outputs_validated_m11_development_csv(self):
        prepare(self.source, self.base / "packets", known_queries=self.base / "none.jsonl")
        a = self.base / "packets/reviewer_A_packet.csv"
        b = self.base / "packets/reviewer_B_packet.csv"
        labels = {"a": "symptom_information", "b": "nonclinical_task"}
        fill_packet(a, "human-A", labels)
        fill_packet(b, "human-B", labels)
        output = self.base / "development.csv"
        report = reconcile(self.source, a, b, output,
                           known_queries=self.base / "none.jsonl")
        self.assertEqual(report["disagreements"], 0)
        self.assertEqual(report["raw_agreement_fraction"], 1)
        self.assertTrue(output.is_file())
        with output.open() as f:
            gold = list(csv.DictReader(f))
        self.assertEqual(len(gold), 2)
        self.assertEqual(gold[1]["adjudicator_id"], "")

    def test_disagreement_requires_third_independent_adjudicator(self):
        prepare(self.source, self.base / "packets", known_queries=self.base / "none.jsonl")
        a = self.base / "packets/reviewer_A_packet.csv"
        b = self.base / "packets/reviewer_B_packet.csv"
        fill_packet(a, "human-A", {"a": "symptom_information", "b": "nonclinical_task"})
        fill_packet(b, "human-B", {"a": "ambiguous_or_mixed", "b": "nonclinical_task"})
        output = self.base / "development.csv"
        with self.assertRaisesRegex(ValueError, "third-reviewer"):
            reconcile(self.source, a, b, output,
                      known_queries=self.base / "none.jsonl")
        adjudication = self.base / "adjudication.csv"
        write_csv(adjudication, ("query_id", "adjudicator_id", "final_label"), [
            {"query_id": "a", "adjudicator_id": "human-C", "final_label": "symptom_information"},
        ])
        result = reconcile(self.source, a, b, output, adjudications=adjudication,
                           known_queries=self.base / "none.jsonl")
        self.assertEqual(result["disagreements"], 1)

    def test_reviewer_text_mismatch_rejected(self):
        prepare(self.source, self.base / "packets", known_queries=self.base / "none.jsonl")
        a = self.base / "packets/reviewer_A_packet.csv"
        b = self.base / "packets/reviewer_B_packet.csv"
        labels = {"a": "symptom_information", "b": "nonclinical_task"}
        fill_packet(a, "human-A", labels)
        fill_packet(b, "human-B", labels)
        with b.open(newline="") as f:
            rows = list(csv.DictReader(f))
        rows[0]["text"] = "Someone changed the prompt"
        write_csv(b, rows[0].keys(), rows)
        with self.assertRaisesRegex(ValueError, "text mismatch"):
            reconcile(self.source, a, b, self.base / "development.csv",
                      known_queries=self.base / "none.jsonl")

    def test_test_split_is_refused(self):
        write_csv(self.source, SOURCE_FIELDS, [
            {**source_row("a", "Synthetic fever example", "new-author"), "split": "test"}
        ])
        with self.assertRaisesRegex(ValueError, "development split only"):
            prepare(self.source, self.base / "packets", known_queries=self.base / "none.jsonl")


if __name__ == "__main__":
    unittest.main()
