# MediPower research evaluation — Milestone M1

**Scope:** Symptom-text information retrieval and healthcare navigation **research prototype**. MediPower is NOT a validated clinical diagnosis, triage, or patient-care service. Legacy field `confidence` is a hybrid *ranking score*, **not** a calibrated disease probability.

## Preregistration and data governance (required before any outcome claims)

1. Record source, collection date, licensing/permissions, privacy/de-identification, inclusion/exclusion criteria, language, and dataset hashes in a manifest kept outside Git.
2. Establish independently reviewed ground-truth query-to-disease IDs, documented annotation rules, adjudication of ambiguous cases, and an explicit negative-control protocol.
3. Split by patient/source/paraphrase-template groups, **not random near-duplicate text**. Review overlap before looking at outcomes.
4. Freeze the disease catalog, query preprocessing, baselines, embedding weights, boosts, threshold policy, random seeds, group partitions and dataset hashes before official test evaluation.
5. Compare the SAME independent queries and candidate catalog for TF-IDF, dense, and hybrid retrieval. Run mode-specific inference to create predictions; the evaluator does not do inference.
6. Report Recall@K, MRR@K, nDCG@K, Hit@K, positive-query abstention rate, and explicit negative-control false-positive rate. Next milestone: group-wise error analysis and 95% confidence intervals. Retrieval metrics alone do not show clinical efficacy.
7. Have qualified experts assess emergency symptom handling and provenance of clinic/provider statistics before any healthcare deployment or safety claim.

## Offline evaluator (standard library only)

Save ground-truth JSONL privately with one JSON object per line. Positive example:

    {"query_id":"example-positive","split":"development","relevant_disease_ids":["21"]}

Explicit non-clinical negative control:

    {"query_id":"example-negative","split":"development","relevant_disease_ids":[],"expected_abstain":true}

Predictions JSONL must contain exactly the same unique query IDs. Disease IDs can be numeric or strings. Each list is in descending rank:

    {"query_id":"example-positive","predicted_disease_ids":["21","2"]}
    {"query_id":"example-negative","predicted_disease_ids":[]}

Execute (replace example paths with independent approved data and model exports):

    python -m research.evaluate_retrieval --gold /path/to/dev.jsonl --prediction tfidf=/path/to/tfidf.jsonl --prediction hybrid=/path/to/hybrid.jsonl --k 1 3 5
    python -m unittest discover -s tests -v

Only aggregate scores are printed; no raw query text. A test file marked `split=test` is refused by default. The `--allow-test` flag is a procedural safeguard, **not authorization**; use it only after legitimate permission and preregistration/freeze. Do not present the example records as benchmark evidence.

## Current research blockers and next work

- Review the existing 100% random-split classifier report for template/phrase leakage and unseen-phrase generalization. It does not establish out-of-source performance.
- Implement reproducible prediction export for each baseline, with identical catalog/query IDs and no modification of official test labels.
- Audit retrieval score semantics, false confidence, abstention behavior, critical symptoms and emergency information flows.
- Establish license and accuracy/provenance of the clinic, retention and diagnosis-volume tables. Never commit patient-level data.
- Publish honest results **only after** approved external labels and held-out evaluations exist.

## M2 extension

See [M2_BENCHMARK.md](M2_BENCHMARK.md) for the classifier data-leakage audit, TF-IDF/BM25/dense/hybrid prediction exporter, development-only demonstrations and commands. Distinguish legacy classification metrics from the production retrieval pipeline; no external clinical benchmark has yet been performed.
