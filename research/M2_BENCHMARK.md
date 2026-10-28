# M2 — Leakage audit and reproducible retrieval baselines

> **Research/development only. Not clinical evaluation, diagnosis, real-world triage, or medical advice.**

## Verified raw-data inspection (28 October 2026)

The repository's `diagnosis_dataset.csv` contains **800 rows** across **8 classes** (100 per class). A simple case/punctuation/whitespace-normalized comparison found **735 unique strings / 65 extra duplicate rows** and **0 conflicting disease labels** among those duplicate strings. All 800 sentences use one of five repeated lead-in phrases. The checked-in classifier report lists 1.0 accuracy and macro-F1 on 160 random-split samples. **The exact cross-split leakage count and group-split model performance require running the audit script and inspecting its output; do not infer them from these counts.** This is a highly templated data source, not an externally validated clinical cohort.

## Reproduce classifier audit

```bash
python -m pip install numpy pandas scikit-learn
python -m research.audit_dataset --data diagnosis_dataset.csv --out research/outputs/m2_dataset_audit.json
```

The audit script matches the legacy classifier's text preprocessing, 80/20 stratified split, random seed 42 and TF-IDF + LogisticRegression hyperparameters. It compares:
- `random_stratified`: reproduces the legacy split, measures exact overlap of post-processed model inputs across train/test.
- `exact_input_grouped`: separates duplicate post-processed symptom inputs between train and test.
- `held_out_sentence_prefix`: holds out one or more of the five recurring sentence-opening templates to test sensitivity to writing style.

It records exact normalized duplicate counts, template counts, class balance, per-split accuracy and macro-F1. **Even the grouped variants reuse the same diagnosis/symptom vocabulary; they do not establish external validity.** Repeated templates can still leak via other constructions. Report seeds, data hashes and limitations.

Run `--audit-only` to inspect data without fitting classifiers.

## Reproducible retrieval baseline export

This is a **separate experiment** from the legacy 8-class text classifier. It ranks a shared catalog of disease IDs using four methods:
1. TF-IDF cosine similarity over condition names, descriptions and departments.
2. BM25 with tokenized bag-of-words (`k1=1.5`, `b=0.75`).
3. Dense embedding cosine similarity (optional local or explicitly downloaded SentenceTransformer).
4. Experimental hybrid fusion: `0.65 * ((dense_cosine + 1)/2) + 0.35 * tfidf_cosine`.

These methods share the same catalog and queries. The hybrid baseline does **not** reproduce production-specific clinical boosts/intent filtering in `app/models/disease_model.py`; that is a distinct future ablation. These retrieval scores are not calibrated probabilities. Results from this tiny catalog and four illustrative inputs are only **pipeline sanity checks**, not meaningful scientific comparisons.

```bash
# Offline lexical baselines, no network required:
python -m research.export_predictions \
  --queries research/examples/dev_queries.jsonl \
  --catalog app/data/diseases.csv \
  --out-dir research/outputs/dev \
  --models tfidf bm25 --top-k 5

python -m research.evaluate_retrieval \
  --gold research/examples/dev_gold.jsonl \
  --prediction tfidf=research/outputs/dev/tfidf.jsonl \
  --prediction bm25=research/outputs/dev/bm25.jsonl --k 1 3 5

# To add dense and hybrid: cache an approved version first or explicitly opt in:
python -m pip install sentence-transformers
python -m research.export_predictions \
  --queries research/examples/dev_queries.jsonl \
  --out-dir research/outputs/dev-dense \
  --models tfidf bm25 dense hybrid --allow-model-download
```

For a proper independent benchmark, replace both `research/examples` files with separated approved and annotated query/gold files (kept off Git) and freeze the model revision, parameters, data hashes and label/abstention policy before official test use. The exporter refuses to read gold labels within query files. Test-split runs are locked by default; `--allow-test` is **not** permission and should only be used after written authorization and preregistration.

**Known limitations:** No clinical validation, no calibrated abstention thresholds, no confidence intervals or external data yet. Dense model revision is not currently pinned; production service behavior is not measured by this baseline. BM25 uses a simple English tokenizer and counts each query term once. Non-clinical inputs may be ranked by dense/hybrid regardless of meaning, and that failure must be reported as a negative-control risk.

## CI and local checks

```bash
python -m unittest discover -s tests -v
```

GitHub Actions `.github/workflows/research-checks.yml` runs the unit tests, legacy audit and illustrative lexical retrieval demonstration, and uploads **aggregate audit counts only**. Confirm the workflow result in GitHub before merging; newly added tests must not be claimed as passed without execution.

## Next milestones

- M3: independently permitted and annotated symptom-to-candidate dataset; patient/source/template-disjoint splits, expert-backed emergency/negative controls.
- M4: production retrieval vs lexical/dense/hybrid ablations, stratified failures, calibration, confidence intervals.
- M5: safety and provider-provenance review; no patient-facing medical decision support until qualified external validation.
