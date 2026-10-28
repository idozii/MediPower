# M4 — Controlled retrieval ablations, paired evaluation and robustness

## Scope and preregistration
M4 evaluates information retrieval performance on exactly identical disease IDs, queries and catalog. It does NOT measure diagnostic safety, medical advice quality or clinical outcomes. Set and freeze a hypothesis, label mapping, split rules, model version, fusion alpha grid, thresholds and primary metric before official test. Changes suggested after inspecting test outcomes need a new preregistered evaluation; do not tune repeatedly on test.

Primary metric suggestion: Recall@3 (macro mean over positive queries); secondary: MRR@3, nDCG@3, Hit@3, false-positive rate on independently identified nonclinical negative controls. Report both absolute performance and paired differences vs BM25, and empirical 95% paired bootstrap intervals when n >= 30 independent positive examples. Correlated or templated cases are not independent; cluster bootstrap is needed for repeated patient/template groups.

## Reproducible local commands

Prerequisites: M3 approved mapped development queries, source provenance and catalog integrity validation. First run offline baselines:

    python -m research.export_predictions --queries research/outputs/ddxplus-dev/queries.jsonl --catalog app/data/diseases.csv --out-dir research/outputs/m4-dev --models tfidf bm25

To execute an OPTIONAL dense model, install pinned compatible sentence-transformers dependencies, download/cache the exact approved model revision yourself, then:

    python -m research.export_predictions --queries research/outputs/ddxplus-dev/queries.jsonl --catalog app/data/diseases.csv --out-dir research/outputs/m4-dev-all --models tfidf bm25 dense hybrid

If model is not cached, exporter will refuse network access unless --allow-model-download is explicitly passed. Document model revision, package versions and local hardware.

Controlled fusion alpha on DEVELOPMENT only:

    python -m research.export_alpha_ablations --queries research/outputs/ddxplus-dev/queries.jsonl --catalog app/data/diseases.csv --out-dir research/outputs/m4-alpha --weights 0 0.25 0.5 0.65 0.75 1

Actual MediPower production DiseaseService can silently use offline fallback, so assert its mode:

    FORCE_OFFLINE_RETRIEVER=1 python -m research.export_production_predictions --queries research/outputs/ddxplus-dev/queries.jsonl --out research/outputs/m4-dev/production_offline.jsonl --require-mode offline_tfidf_forced

For semantic mode: cache a matching SentenceTransformer or set ALLOW_MODEL_DOWNLOAD=1 after approving external download, then run:

    FORCE_OFFLINE_RETRIEVER=0 python -m research.export_production_predictions --queries research/outputs/ddxplus-dev/queries.jsonl --out research/outputs/m4-dev/production_semantic.jsonl --require-mode semantic_faiss

The above distinguishes production intent boosts and rule filters from the simplified fusion-only research baseline. Never confuse modes.

Compare lexical models on the same validation labels (the sample scripts will reject official test by default):

    python -m research.compare_models --gold research/outputs/ddxplus-dev/gold.jsonl --prediction bm25=research/outputs/m4-dev/bm25.jsonl --prediction tfidf=research/outputs/m4-dev/tfidf.jsonl --baseline bm25 --k 3 --samples 2000 --out research/outputs/m4-comparison.json

Extend --prediction for hybrid, dense, production_offline and production_semantic once these predictions exist. Different model folders and dataset hashes must be checked manually before comparing.

## Limitations and blockers
- DDXPlus evidence conversion is synthetic structured query text, not real freeform complaints; source ontology coverage is mandatory to report.
- Benchmark needs independently approved label mapping, dataset permissions and a frozen protocol before official test.
- The current single-query bootstrap assumes independent cases, invalid for duplicated patient/template groups. A cluster-aware statistical method is needed for published confidence intervals whenever cases share sources.
- Dense and full production semantic runs are local-only when model isn't installed; CI only checks lightweight toy tests.
- Choosing the best alpha on development and reporting the same development as unbiased generalization would overfit. Use an untouched official test set after authorization.
- Negative controls must be independently selected nonclinical inputs, never excluded out-of-catalog pathologies.
