# M8 — Source-aware retrieval evaluation and lexical-overlap stress tests

## Trigger / prior evidence

Owner-provided development smoke test (28 Oct 2026) had 3 hand-authored positive retrieval inputs and 1 off-topic negative. Dense and Hybrid returned conditions for the lone negative; TF-IDF and BM25 abstained. A lexically gated Dense/Hybrid ablation then abstained on that same negative with no loss among those three positives. **This is a pipeline observation, not a meaningful false-positive-rate estimate or clinical safety improvement.** The developer saw the one negative before proposing the gate, so that case is not an independent evaluation.

The DDXPlus community-mirror validation download contains 132,448 synthetic cases and 49 source labels, while MediPower has 29 catalog conditions. There are 0 approved ontology mappings. External retrieval benchmarking is still BLOCKED pending independently reviewed mapping, provenance, coverage, and annotation decisions.

## 1. New stress challenge (illustrative and NOT independent)

Development-only pairs:
- research/examples/abstention_stress_v1_queries.jsonl
- research/examples/abstention_stress_v1_gold.jsonl

There are **10** handcrafted symptom-to-condition information retrieval examples and **20** explicitly negative off-topic requests. The negatives include ordinary unrelated queries and "lexical overlap" challenges involving words such as Migraine, Heart Failure, Influenza and Emergency Department in non-symptom contexts.

This suite was designed **after** observing the prior toy failure and is unsuitable for confirmatory inference, hyperparameter selection, external validation or patient-care claims. Positive associations are hand-authored to probe software behavior, NOT independently validated diagnoses.

## 2. Run original baselines unchanged

    python -m research.export_predictions --queries research/examples/abstention_stress_v1_queries.jsonl --catalog app/data/diseases.csv --out-dir research/outputs/m8-stress-original --models tfidf bm25 dense hybrid

Dense needs the already downloaded model cached locally. If not available, do NOT retry downloading automatically; verify the desired revision and environment.

## 3. Run gated ablations

    python -m research.export_abstention_ablations --queries research/examples/abstention_stress_v1_queries.jsonl --catalog app/data/diseases.csv --out-dir research/outputs/m8-stress-gated

This compares a fixed **lexical-overlap > 0** gate, not an OOD classifier. It will fail on meaningful paraphrases with zero catalog overlap, and may accept off-topic inputs mentioning a disease name. Do not adjust a threshold to improve this suite and then call the result unbiased.

## 4. Inspect subgroup failures and positive abstention

    python -m research.audit_prediction_subgroups --gold research/examples/abstention_stress_v1_gold.jsonl --prediction tfidf=research/outputs/m8-stress-original/tfidf.jsonl --prediction bm25=research/outputs/m8-stress-original/bm25.jsonl --prediction dense=research/outputs/m8-stress-original/dense.jsonl --prediction hybrid=research/outputs/m8-stress-original/hybrid.jsonl --prediction dense_gate=research/outputs/m8-stress-gated/dense_lexical_gate.jsonl --prediction hybrid_gate=research/outputs/m8-stress-gated/hybrid_lexical_gate.jsonl --k 3 --out research/outputs/m8-subgroups.json

Output groups:
- symptom_constructed (positive queries, report Recall@3 and positive abstention)
- nonclinical_clean (negative, report failure-to-abstain count / 10)
- nonclinical_overlap (negative sharing medical vocabulary, report failure-to-abstain count / 10)

Counts and rates are reported independently; no query text is printed. Interpret the small illustrative rates as diagnostics only.

## 5. Cluster-aware paired bootstrap for any later approved DDXPlus development evaluation

M3 adapter now writes group_id to gold.jsonl, hashing the normalized symptom text. M4 paired bootstrap checks group_id on **all** positive examples and draws entire groups together. Confidence intervals are **suppressed when there are fewer than 30 distinct groups**, even if the raw sample count is much larger. This avoids a false increase in certainty from duplicated narratives; however, duplicate-text groups do not fully capture shared synthetic templates or patient/source dependencies, so even cluster CIs must be interpreted cautiously.

    python -m research.compare_models --gold research/examples/abstention_stress_v1_gold.jsonl --prediction bm25=research/outputs/m8-stress-original/bm25.jsonl --prediction hybrid_gate=research/outputs/m8-stress-gated/hybrid_lexical_gate.jsonl --baseline bm25 --k 3 --samples 2000

For this tiny illustrative suite confidence intervals should correctly be unavailable. For external synthetic validation, first obtain appropriate ontology mapping approvals and report source pathology coverage. All official test results remain locked.

## 6. Code-quality checks

    python -m unittest discover -s tests -v
    python -m compileall -q research tests

This milestone is development-only research infrastructure. No dense model or DDXPlus validation set is downloaded by CI. Never upload raw patient text or official test data to GitHub.
