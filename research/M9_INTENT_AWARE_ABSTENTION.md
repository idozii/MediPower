# M9 — Two-stage task-intent abstention experiment

## Motivation and strict evidence limits

In the owner-provided M8 local development stress test (10 handcrafted symptoms + 20 nonclinical requests), the existing lexical gate still returned disease candidates for 16/20 nonclinical tasks; all 10 off-topic tasks containing medical vocabulary failed to abstain. Hybrid Recall@3 on the 10 handcrafted positive cases was 1.0. These are **diagnostic counterexamples, not independent estimates of reliability**. See [M8 owner local evidence](results/M8_OWNER_LOCAL_STRESS_2026-10-28.md).

The observed failure suggests medical-keyword overlap does not determine **query purpose**. Therefore M9 evaluates a two-stage research architecture:

1. **Query-task intent decision** — compare normalized SentenceTransformer query embeddings to 3 generic symptom-information prototypes and 3 non-medical-task prototypes. Accept only if maximum symptom similarity exceeds maximum other-task similarity by the *predeclared* intent margin (default 0).
2. **Disease-information retrieval** — only after acceptance, rank the same 29 catalog conditions with unchanged Dense and Hybrid scores, or with an additional lexical-overlap gate.

No gold annotations are read by the exporter. Its prototypes are fixed in the source file and recorded via SHA256 in the manifest. The threshold of zero was selected as a no-training starting point, **not optimized on the 30 M8 examples**.

**This is a generic embedding-similarity heuristic, not a supervised medical intent classifier.** It can misinterpret symptoms, accident, emergencies, rare conditions, paraphrases, and long multi-intent requests. It must not be used for real-world clinical triage or deciding whether someone needs care.

## Local commands (model already cached by owner)

Ensure you are on the current M9 branch and have the same 29-condition catalog.

    python -m research.export_intent_ablations --queries research/examples/abstention_stress_v1_queries.jsonl --catalog app/data/diseases.csv --out-dir research/outputs/m9-intent-dev

Expected prediction files:
- hybrid_intent_gate.jsonl — original hybrid ranking, gated on task intent.
- dense_intent_gate.jsonl — original dense ranking, gated on task intent.
- hybrid_intent_and_lexical_gate.jsonl — intersection of semantic intent and lexical-overlap >0.

Inspect aggregate count and model manifest first. All are development experiments, not deployment changes.

To compare the gate against previous baselines on the **same** dataset and catalog:

    python -m research.audit_prediction_subgroups --gold research/examples/abstention_stress_v1_gold.jsonl --prediction hybrid=research/outputs/m8-stress-original/hybrid.jsonl --prediction hybrid_lexical=research/outputs/m8-stress-gated/hybrid_lexical_gate.jsonl --prediction dense_intent=research/outputs/m9-intent-dev/dense_intent_gate.jsonl --prediction hybrid_intent=research/outputs/m9-intent-dev/hybrid_intent_gate.jsonl --prediction hybrid_both=research/outputs/m9-intent-dev/hybrid_intent_and_lexical_gate.jsonl --k 3 --out research/outputs/m9-intent-subgroups.json

**Important:** All outcomes on the M8 30-query set are **post-hoc debugging results**, as the M9 prompts were designed after seeing the M8 labels/aggregate results. Do not compute or publish a confirmatory test significance claim. Do not change the prompt text, margin or threshold to get better M8 scores and then claim unbiased improvements. Retain unexpected failures in the research log.

## Before any research paper or clinical relevance claim

- Independently annotate a new prospective, source/author-disjoint task-intent cohort containing health questions, overlapping nonhealth intents, semantically subtle paraphrases, language variants and realistic ambiguity; freeze this dataset before scoring models. Do not use any real patient data without permissions.
- Review ambiguous labels with multiple annotators and document disagreements and unknown/abstain policy.
- Define and freeze model revision, positive/negative prototypes, margin and catalog version. Evaluate group-aware uncertainty and per-class failure types, not just Recall@3.
- Separate **task-intent negative** (not requesting health information) from **open-set clinical negative** (genuine symptoms for a condition missing from the 29-item catalog). The latter is an important problem and MUST NOT be treated as nonclinical.
- Assess potential failure-to-refer on emergency symptom reports by qualified clinicians before any patient-facing prototype.
- The 49 DDXPlus pathologies remain 0 approved mappings to the 29-condition catalog. DDXPlus is synthetic and structured and does not supply independently labeled nonclinical intent negatives; these are **separate experiments**.

## CI

    python -m unittest discover -s tests -v

All automated M9 tests use fabricated embedding matrices and mock inputs; CI does **not** download SentenceTransformers or process the DDXPlus mirror.
