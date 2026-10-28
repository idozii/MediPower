# M10 — Intent-gate failure analysis: selective risk and coverage

## Trigger: owner-run M9 local output, 28 October 2026

The user ran the M9 fixed zero-shot prompt-comparison gate on the same **post-hoc, developer-authored M8 30-query development suite**. These are NOT external, independent or clinically validated results.

Source query SHA256: a420e90b9ed9ee5a990fedaeff7c0fab36d656a7f36186232e31f8521a1340a1. Disease catalog SHA256: 29da44311044269c857adb1bae430bc9c917899465122852d6b838b0870ca7c8. M9 prototypes SHA256: d9f7d097bd36866d061bf1c3bed6dac7c2feac5be1eb9a5d4547f600900c4618.

| Experimental method | Positive Recall@3 (n=10) | Nonclinical false positives (n=20) | Positive false abstentions |
|---|---:|---:|---:|
| Original Hybrid | 1.0 | 20 | 0 |
| Hybrid + lexical gate | 1.0 | 16 | 0 |
| Hybrid + intent gate | **0.2** | **7** (5 clean; 2 medical-vocabulary overlap) | **8** |
| Hybrid + intent AND lexical gates | **0.2** | **6** (4 clean; 2 medical-vocabulary overlap) | **8** |
| Dense + intent gate | 0.2 | 7 | 8 |

M9 accepted 9/30: only 2/10 positive symptom narratives and 7/20 nonclinical tasks. The combination of both gates abstained on 22/30. The **80% positive false abstention** means this gate is unsuitable for promotion into the application. Reducing total false positives by rejecting actual symptom-information queries is NOT a valid safety improvement.

## What M10 implements

M10 is **analysis infrastructure**, not a fix to M9 or a new medical classifier.

1. Export per-query **frozen semantic intent margins**: maximum query-to-symptom-prototype cosine minus maximum query-to-nonclinical-task-prototype cosine. No gold labels or text are used in the exporter; only IDs and scores are saved in ignored local outputs.
2. Pair margins against the **original ungated Hybrid predictions** (using identical query SHA256 and split) and independently annotated development-only gold labels.
3. Report at the **pre-existing threshold 0**: false-abstained positives, off-topic false positives, subgroup counts and end-to-end Recall@3.
4. Produce a **fixed descriptive threshold grid** from -0.25 to +0.25, where each row shows intent coverage, symptom query retention, positive abstention, false positives and retrieval Recall@3. It is exploratory only — do NOT pick the threshold with the best result on the already inspected M8 examples and pretend the result is independent.
5. All M9 prompt text, model name, source hashes and baseline rankings remain unchanged; no production code changes.

## Owner local commands

From the M10 branch with an existing local cached all-MiniLM-L6-v2 and earlier M8 output folders, run:

    python -m research.export_intent_margins --queries research/examples/abstention_stress_v1_queries.jsonl --out-dir research/outputs/m10-intent-margins

Then:

    python -m research.audit_intent_risk_coverage --gold research/examples/abstention_stress_v1_gold.jsonl --margins research/outputs/m10-intent-margins/intent_margins.jsonl --predictions research/outputs/m8-stress-original/hybrid.jsonl --k 3 --out research/outputs/m10-intent-risk-coverage.json

Optional, **local diagnostic only**: add --include-error-ids for explicit problem query identifiers (never raw symptom text). Do not share IDs from any real patient dataset.

No DDXPlus patient records, official test data, or new network downloads are required.

## Interpretation safeguards

- M8 prompts and the M9 comparison prompts have been **seen and modified after failure inspection**. The resulting curve is not a prospective model-selection experiment; any numerical operating point is descriptive only.
- An embedding cosine *margin* is not a calibrated confidence, clinical probability or indication of disease.
- Positive false abstention can be a serious failure for genuine symptom reporting. Even true nonclinical intent detection is different from recognizing when a symptom is urgent or a condition is outside the 29-condition catalog.
- Threshold selection, if later needed, belongs to a **new independently authored development cohort** with predefined constraints and a wholly untouched authorized final test.
- DDXPlus still has 49 synthetic condition names and 0 medically approved mappings to the 29-condition catalog. It does not solve the nonclinical task-intent experiment.
- Independent medical review and data permissions are mandatory before considering real-world deployment or clinical claims.

## Engineering checks

    python -m unittest discover -s tests -v

GitHub CI uses synthetic fixtures and does not execute the heavyweight model. A successful CI run establishes code/regression correctness, NOT performance or safety.
