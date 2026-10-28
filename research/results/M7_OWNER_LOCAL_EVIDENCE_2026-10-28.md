# MediPower M3/M4 — local development evidence (owner-supplied, 28 October 2026)

**Status:** owner-supplied output, NOT independently reproduced in GitHub Actions. Research-only toy evaluation; no external official test outcomes, clinical claims or approved pathology equivalences.

## DDXPlus community mirror preflight

- Development validation rows: 132,448.
- Unique source PATHOLOGY labels: 49.
- Mirror equivalence to official publisher release: NOT_CONFIRMED.
- Validation SHA256: b84733533bff01daa1d47d27a0cd4d684bb54a0fc20d80aaee1250ff8ff989ed.
- Evidence definitions SHA256: 281c78b044ae60514e28ecc9052d08a8225dd3e2db3f00f8788b99c47b05e0c0.
- Condition definitions SHA256: 61e16706a2ab78efb997bab8a865c83b46151b10b0377b63530745f1e18e71a8.
- Name-similarity candidates generated: 49; approved: 0. The mapping is still blocked pending qualified independent review. No DDXPlus retrieval performance is measured.

## Four-model smoke test (three illustrative positives and one unrelated negative)

Same 29-condition catalog SHA256 29da44311044269c857adb1bae430bc9c917899465122852d6b838b0870ca7c8; same query SHA256 a5deb9797c1f3bc09770e3f6f0e7bcd4b236466327613e5559f9234f327fc1f1; sklearn 1.8.0; split development.

| Method | Recall@1 | MRR@3 | Recall@3 | Nonclinical false positives |
| --- | ---: | ---: | ---: | ---: |
| TF-IDF | 0.8333 | 1.0000 | 1.0000 | 0/1 |
| BM25 | 0.8333 | 1.0000 | 1.0000 | 0/1 |
| Dense (all-MiniLM-L6-v2) | 0.5000 | 0.7778 | 1.0000 | 1/1 |
| Hybrid (alpha=0.65) | 0.8333 | 1.0000 | 1.0000 | 1/1 |

**Important:** One negative input cannot support a meaningful false-positive-rate estimate or a claim that sparse is better. Positive labels are hand-authored illustrative references, not validated medical ground truth. This identified a reproducible concern to investigate: shifted dense scores combined with a zero threshold are not a robust reason to return a medical condition. The proposed lexical-overlap gate is a new **ablation only**, with its own potential false abstention costs.

## Next gates

1. Run M3 development ontology frequency audit, have a qualified reviewer determine true approved mappings, and report covered/uncovered pathology counts.
2. Run M4 lexical-gate ablations on the toy examples to validate wiring, then on an independently reviewed development set including diverse negatives and meaning-preserving paraphrases.
3. Precommit all thresholds and validate in an untouched, authorized test set; do not adapt after seeing test labels.
