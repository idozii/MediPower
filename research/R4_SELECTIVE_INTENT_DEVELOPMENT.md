# R4 — Development-only selective task-intent diagnostic

**Status:** RESEARCH INFRASTRUCTURE ONLY. No newly collected, independently authored, permissioned or double-annotated R2 cohort has been supplied. There are no new scientific performance estimates from this PR.

## Research question

Can a task-intent abstention rule reduce acceptance of unrelated tasks while maintaining symptom-information queries? There are **two asymmetric error types**:
- **Positive false abstention**: an actual symptom-information query is rejected.
- **Nonclinical false acceptance**: a nonclinical task passes the symptom-information intent gate.

Neither should be called a clinical harm estimate or diagnostic false positive. Out-of-catalog clinical queries remain symptom-oriented but are not included as nonclinical negatives. The result does not measure whether a retrieved condition is relevant or clinically correct.

## Fixed exploratory grid (NOT threshold optimization)

The thresholds -0.05, 0.0 and +0.05 were already examined during M10, following exposure to M8 examples. Therefore they do not constitute a new prospective pre-registration, are not eligible for independent claims and cannot be used to pick a supposedly unbiased optimal threshold.

For each threshold the script reports binary coverage, symptom retention, symptom false abstention, nonclinical false acceptance, binary error fraction and accepted binary positive fraction. It also reports three other R2/M11 categories separately:
- clinical_out_of_catalog
- general_health_information
- ambiguous_or_mixed

95% **source-group clustered bootstrap intervals** are descriptive only and should not be given inferential weight on tiny, biased or reused author groups. Invalid resamples that lack one of the two binary labels are counted rather than ignored.

## Run on a properly sourced DEVELOPMENT-only R2 cohort

First satisfy M11 annotation rights, review and source-disjointness requirements and follow research/R2_ANNOTATION_OPERATIONS.md to export annotated data and frozen intent similarities. Never commit private query files.

    python -m research.r4_selective_intent_analysis --queries research/outputs/r2-intent-dev/queries.jsonl --gold research/outputs/r2-intent-dev/intent_gold.jsonl --margins research/outputs/r2-intent-margins/intent_margins.jsonl --bootstrap-repeats 1000 --seed 20261028 --out research/outputs/r4-intent-selective-development.json

The script verifies M10/M11 manifests and rejects any non-development label. Output is aggregate statistics with model/prototype hashes and unresolved revision metadata. If model revision is not pinned, the study is not reproducibly frozen.

## Gates to credible academic results

- R2 must supply genuine rights-cleared, independently sourced and double-annotated queries, with third-reviewer resolution and source/template disjointness.
- Freeze exact model checkpoint and prototype text, threshold procedure, analysis units, subgroup design and precommit genuine external test labels before accessing them.
- Evaluate task-intent and catalog OOD as distinct questions; no diagnosis, care guidance or clinical safety claims based on R4 results.
- Benchmark against matched trivial/binary baselines on the *same approved cohort* and report complete uncertainty, error tradeoffs and failures.
- A future *separate authorized script* may access test after approval. This script always rejects test and never auto-promotes an intent gate into the web application.

Only fabricated synthetic examples are included in CI unit tests.
