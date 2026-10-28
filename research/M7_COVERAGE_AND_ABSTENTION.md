# M3/M4 follow-up — Development ontology coverage and abstention trade-offs

**Scope:** synthetic DDXPlus validation from an unverified community mirror, plus an illustrative 4-query smoke test. This is not independent medical diagnosis or safety evidence.

## Supplied local evidence (2026-10-28)

- 132,448 synthetic DDXPlus validation rows, 49 distinct source pathologies. Mirror validation SHA256 b84733533bff01daa1d47d27a0cd4d684bb54a0fc20d80aaee1250ff8ff989ed.
- Evidences SHA256 281c78b044ae60514e28ecc9052d08a8225dd3e2db3f00f8788b99c47b05e0c0; conditions SHA256 61e16706a2ab78efb997bab8a865c83b46151b10b0377b63530745f1e18e71a8.
- 49 pending mapping candidates, zero approved. No mapped DDXPlus benchmark is authorized by this output.
- Three positive and one negative illustrative query: TF-IDF/BM25/Hybrid recall@1 0.8333, Dense recall@1 0.5; all recall@3 1.0. Dense/Hybrid returned a condition on the single nonclinical negative (1/1 false positives); TF-IDF/BM25 did not (0/1). No inferential significance.
- Shifted dense cosine via (cosine+1)/2 can produce positive scores for irrelevant queries. Zero threshold is not a reliable OOD detector.

## M3 — Review worksheet

Run on development-only validation data:

    python -m research.audit_ddxplus_coverage --patients research/private_data/ddxplus/validate.csv --candidates research/private_data/ddxplus_mapping_candidates.csv --catalog app/data/diseases.csv --out-dir research/outputs/m3-coverage

Output: aggregate JSON at research/outputs/m3-coverage/ontology_coverage_summary.json and pending human-review worksheet at research/outputs/m3-coverage/ontology_review_worksheet.csv.

- Source labels, distribution and name-similarity candidates are descriptive. A qualified reviewer must approve actual equivalence; empty mapping columns are intentional.
- Do not assume 49 source pathology labels can be represented by 29 target conditions. Report source coverage before selecting evaluation labels.
- Keep local data under research/private_data and research/outputs (gitignored). Do not access official test.
- Community mirror integrity does not establish official provenance.

## M4 — Lexical-evidence gate experiment

Two new, separate research baselines:
- dense_lexical_gate: dense ranking only when maximum TF-IDF similarity to the catalog is greater than zero, or a preregistered development-only threshold.
- hybrid_lexical_gate: same gate applied to the unchanged alpha=0.65 hybrid score.

This is NOT a clinically validated OOD detector. It may reject legitimate paraphrases that have no vocabulary overlap, and may retain irrelevant queries that do share generic terms. Report negative false-positive and positive abstention jointly; do not tune against one negative sample.

    python -m research.export_abstention_ablations --queries research/examples/dev_queries.jsonl --catalog app/data/diseases.csv --out-dir research/outputs/m4-lexical-gate

    python -m research.evaluate_retrieval --gold research/examples/dev_gold.jsonl --prediction dense_gate=research/outputs/m4-lexical-gate/dense_lexical_gate.jsonl --prediction hybrid_gate=research/outputs/m4-lexical-gate/hybrid_lexical_gate.jsonl --k 1 3 5

These four toy queries can only verify wiring, NOT quantify real-world improvements. Any publishable comparison needs independently reviewed labels, diverse negatives and relevant paraphrases, clear source documentation, and untouched test authorization.

## CI

    python -m unittest discover -s tests -v

CI uses fabricated data and does not download DDXPlus or embeddings. No changes here are authorized for real patient-care use.
