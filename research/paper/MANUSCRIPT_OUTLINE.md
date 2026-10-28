# MediPower — Research manuscript outline (provisional, not submission-ready)

## Provisional title
**Beyond Perfect Accuracy: Leakage-Aware and Abstention-Aware Evaluation of Hybrid Medical Information Retrieval on Synthetic Symptom Evidence**

This is a tentative direction, not a novelty or acceptance claim. The clinical safety aspects require appropriately qualified expert collaboration. Keep the actual study scoped to information retrieval, not diagnostic care recommendations.

## Proposed abstract structure (no invented results)
- Context: free-text symptom-to-condition retrieval is susceptible to templated training data, ontology mismatch and unsafe ranking-score interpretation.
- Gap: perfect internal classifier scores do not establish external or real-world performance.
- Method: reproduce and audit legacy random split, compare exact-input and template held-out evaluations, use an independently obtained licensed synthetic external cohort with manual ontology mapping, then compare lexical/dense/hybrid/production retrieval modes on the identical candidate catalog.
- Study: quantify Recall@K, MRR@K, nDCG@K, explicitly curated negative-control abstention, paired baseline deltas and robustness by source/template; preregister all choices and use untouched test only once.
- Results: **PENDING external dataset, mapping and approved held-out evaluation**.
- Limitations: synthetic structured records rather than spontaneous complaints, small 29-condition catalog, missing clinical validation and possible weak label harmonization.

## Detailed sections
1. **Introduction** — challenge and exact scope of research problem; distinguish information retrieval from diagnosis.
2. **Related work** — DDXPlus synthetic differential-diagnosis benchmark (Fansi Tchango et al., NeurIPS 2022), sparse/dense retrieval, evaluation leakage, abstention and selective prediction. Review contemporary methods before identifying any novelty.
3. **Data** — 800 templated development labels, 65 duplicate raw-normalized rows; 17 of 160 random test examples have identical processed inputs in training; eight-class classifier and 29-item retrieval catalog are DIFFERENT experimental tasks. Describe exact DDXPlus release and CC BY license with attribution, label coverage and human review.
4. **Methods** — TF-IDF, BM25, dense, fusion alpha grid, production clinical-intent heuristics, frozen thresholds and provenance.
5. **Evaluation** — preregister primary Recall@3, paired baselines, negative controls, source/template/ontology coverage, bootstrap with cluster independence constraints; independent test authorization.
6. **Results** — generated from research/build_research_report.py using M4 JSON, never hand-invented. Stratify error analysis, report confidence intervals and missing classes.
7. **Threats to validity** — structured synthetic data, vocabulary overlap, unknown prevalence, prior dataset exposure by pretrained embeddings, selection bias of mapped 29-class subset, source/license variability.
8. **Ethical and clinical considerations** — nonclinical framing, privacy, safety monitoring and domain-expert evaluation requirements.
9. **Reproducibility** — public scripts, package versions, hashes, model revision, seed, explicit license attribution and run commands (excluding sensitive data).
10. **Discussion and next experiments** — only claim novel contributions actually supported by reproducible independent outcomes.

## Reference starting points
- Fansi Tchango et al., DDXPlus (NeurIPS 2022), https://papers.neurips.cc/paper_files/paper/2022/hash/cae73a974390c0edd95ae7aeae09139c-Abstract-Datasets_and_Benchmarks.html
- Official English DDXPlus dataset: https://figshare.com/articles/dataset/DDXPlus_Dataset_English_/22687585 (version 2 posted 2026-03-09; record exact version used and file checksums).
- Official DDXPlus GitHub: https://github.com/mila-iqia/ddxplus

## Research submission gate
Do not label the study as an original methodological contribution until a literature search and experiments establish novelty. Do not call any model clinically validated. A development-only or toy run cannot justify a conference paper's claimed results.
