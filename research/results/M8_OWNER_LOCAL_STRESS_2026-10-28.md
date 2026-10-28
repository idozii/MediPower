# M8 owner-supplied local stress results — 28 October 2026

**Evidence level:** user executed local commands and supplied JSON output in chat. This report is a faithful summary of owner-provided development-only observations, **not** a GitHub Actions run of the heavy embedding models and **not** external clinical validation.

## Dataset and model settings

- 30 developer-authored development-only illustrative queries (10 positive symptom narratives and 20 negative nonclinical tasks: 10 clean, 10 medically overlapping).
- Disease catalog: 29 entries, SHA256 29da44311044269c857adb1bae430bc9c917899465122852d6b838b0870ca7c8.
- Query file: SHA256 a420e90b9ed9ee5a990fedaeff7c0fab36d656a7f36186232e31f8521a1340a1.
- Dense encoder: all-MiniLM-L6-v2, sklearn 1.8.0; alpha=0.65; top_k=5. No independently fixed model revision reported.

| Model | Positive Recall@3 (n=10) | Clean nonclinical false positives (n=10) | Medical-vocabulary nonclinical false positives (n=10) | Total false positives (n=20) | Positive abstentions |
| --- | ---: | ---: | ---: | ---: | ---: |
| TF-IDF | 0.90 | 6 | 10 | 16 | 0 |
| BM25 | 0.90 | 6 | 10 | 16 | 0 |
| Dense | 0.90 | 10 | 10 | 20 | 0 |
| Hybrid | 1.00 | 10 | 10 | 20 | 0 |
| Dense + lexical gate | 0.90 | 6 | 10 | 16 | 0 |
| Hybrid + lexical gate | 1.00 | 6 | 10 | 16 | 0 |

The lexical gate abstained on four development queries, which were all clean nonclinical negatives, preserving the ten developer-authored positive inputs. All six baselines failed to abstain on *every* nonclinical query that mentioned a medical term. Thus, zero lexical overlap is only a weak filter and does not establish user task intent. The M8 challenge was authored after an earlier single-negative gate failure, making it a diagnostic test, not confirmatory inference.

## M9 research hypothesis (prospective follow-up; NOT validation)

Add a second-stage prototype-based semantic intent decision **separate from disease catalog retrieval**. Compare:
- original Dense and Hybrid (no gate),
- lexical overlap gates,
- Dense/Hybrid gated by a general-task semantic prototype comparison,
- Hybrid with both intent and lexical gates.

Report the two error axes (positive false abstention and off-topic false positive) separately, including nonclinical-clean and nonclinical-overlap subgroups. Predeclare the prompt set, minimum acceptance margin=0 and disease catalog; record hashes. Because the prompts are selected after M8 outcomes, all results against M8 must be labeled **development diagnostics only**; no statistical or medical generalization claims.

## External research blockers

The community DDXPlus validation source has 132,448 synthetic rows and 49 source pathologies, and an unverified mirror equivalence. The ontology reviewer has approved **0** condition mappings into MediPower's 29-condition catalog. Do not convert DDXPlus to "ground-truth" MediPower disease IDs until authorized qualified mapping review; do not use the official test set to tune any part of this pipeline. Independent prospective evaluation would require separately sourced negatives and genuine symptom paraphrases as well as target labels.
