# M3 — External synthetic cohort evaluation protocol

## Provenance
Proposed source: DDXPlus (Mila/NeurIPS 2022), https://github.com/mila-iqia/ddxplus ; English dataset release linked in its README, CC BY. Cite Fansi Tchango et al., NeurIPS Datasets & Benchmarks 2022, DOI 10.52202/068431-2270. Verify license, downloaded file hashes, and publisher identity locally; do not commit raw source data.

## Rules
- Official DDXPlus validation set maps to MediPower development. Official test stays LOCKED, pending permissions and a frozen written preregistration.
- These are synthetic, structured clinical evidence records, NOT independent patient-written narratives or clinically confirmed diagnoses.
- Converter reads symptom EVIDENCES to build query texts; PATHOLOGY only supplies ground-truth labels. It excludes demographics, antecedents and differential diagnosis from queries.
- Map DDXPlus PATHOLOGY to an existing MediPower catalog disease_id only when independently reviewed and approved. Do not auto-approve approximate aliases. Unsupported pathology labels are excluded and counted, NEVER mislabeled as negative controls.
- Report total source cases, proportion mapped, missing label counts and class imbalance before evaluation. The two ontology scopes are different, so low coverage invalidates broad claims.
- All models must use identical queries and catalog versions and a frozen preprocessing, threshold and model revision.
- The flag --allow-test is a procedural gate only, NOT permission.

## Local commands (after you independently obtain the publisher English release)
Make a LOCAL reviewed mapping at research/private_data/ddxplus_reviewed_mapping.csv from research/mappings/ddxplus_mapping_template.csv. Populate source_pathology,target_disease_id,review_status and use approved only after mapping review.

    python -m research.prepare_ddxplus --patients research/private_data/ddxplus/release_validate_patients.csv --evidences research/private_data/ddxplus/release_evidences.json --mapping research/private_data/ddxplus_reviewed_mapping.csv --catalog app/data/diseases.csv --split development --out-dir research/outputs/ddxplus-dev

    python -m research.check_split_integrity --queries research/outputs/ddxplus-dev/queries.jsonl --gold research/outputs/ddxplus-dev/gold.jsonl --catalog app/data/diseases.csv

Sample-only development smoke run: append --max-rows 100 to the converter (deterministic by evidence hash; NOT pathology stratified). Actual archive CSV filenames may differ; inspect extracted files first. Never submit raw patient-level records in chat.

## Exit criteria
Confirm exact dataset publication license and attribution; mapping coverage; non-overlap and source provenance; independent evidence annotations where needed; target model revisions and predefined metrics; and authorization to run the official test. No clinical or real-world safety efficacy may be claimed. Current status: adapter only tested on invented fixtures; official external data not accessed, coverage unknown.

## Candidate mapping assistant (no auto-approval)
After downloading the English DDXPlus metadata, generate *pending* name-similarity candidates:

    python -m research.suggest_ddxplus_mappings --conditions research/private_data/ddxplus/release_conditions.json --catalog app/data/diseases.csv --out research/private_data/ddxplus_mapping_candidates.csv

Output keeps target_disease_id blank and review_status pending. A reviewer must determine any equivalent labels; textual similarity is not medical equivalence. Copy reviewed rows to ddxplus_reviewed_mapping.csv only when truly approved. Send aggregate counts and status, not patient-level data.

Official English publisher page: https://figshare.com/articles/dataset/DDXPlus_Dataset_English_/22687585 ; version 2 posted 9 March 2026. Record exact downloaded version, license, provenance and checksums before use.

## Figshare 403 alternative

For an opt-in community Hugging Face mirror **development validation only**, verified per-file hashes, and source caveats, see [M3 Figshare 403 fallback guide](M3_FIGSHARE_403_FALLBACK.md). This does not establish official provenance; never open the test split to resolve a browser error.
