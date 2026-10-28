# Phase 2 / R3 — External ontology provenance and reviewer readiness

**Status: BLOCKED.** Earlier development audit observed 49 distinct DDXPlus source pathology labels against MediPower's 29-condition catalog. 49 lexical suggestion rows are NOT clinically approved mappings. The earlier mirror SHA256 values are descriptive only and do not prove an official publisher download.

## What R3 adds

- A **structural gate** for a separate independent clinical review file. It never auto-approves name similarity matches, never downloads external data and never reads an official test split.
- Two distinct reviewer IDs, a written equivalence rationale and a valid target disease ID are required for an `approved` status. Approximate/broader/narrower wording cannot be marked exact equivalence.
- `pending`, `rejected`, `unmappable` cases remain explicit, and unreviewed labels count toward incomplete mapping coverage rather than being silently converted to negative controls.
- A separate optional provenance JSON can record claimed publisher release ID, digest and two reviewers. Its content is only **self-reported metadata** and cannot authenticate license/permissions or clinical expertise.
- All outputs stay aggregate. Never report that mapping is clinically validated from this software alone.

## Input workflow

1. From the existing M3 coverage workflow, obtain development-only `ontology_review_worksheet.csv` under the ignored `research/outputs/m3-coverage`.
2. Copy the header-only template `research/mappings/r3_independent_review_template.csv` into a private local file. Qualified independent reviewers must supply source pathology, target disease ID, status, two identities, evidence and `exact_clinical_equivalence` when justified. Do not ask ChatGPT to invent reviewers or approval notes.
3. Run the structural gate locally:

    python -m research.r3_review_gate --candidates research/outputs/m3-coverage/ontology_review_worksheet.csv --reviewed research/private_data/r3_independent_mapping_review.csv --catalog app/data/diseases.csv --out research/outputs/r3_review_readiness.json

With no reviewed file, omit `--reviewed`; this reports all labels as pending.

## Hard blockers and next research actions

- Independently verify the exact official publisher artifact (hashes, license, reuse permissions, release identity) rather than accepting mirrored validation bytes as official.
- Obtain a qualified clinical reviewer, a distinct second reviewer and consensus/adjudication policy; licenses and provenance documentation must be signed/checked outside this repository.
- Review whether the source pathology ontology and 29-condition catalog are genuinely compatible. Mapping coverage may be insufficient, and unrepresentable diseases must remain excluded/explicit.
- Authorize the official test separately **only after** freezing hypotheses, evaluation scope, ground-truth mapping and metrics. R3 structural software does not change this prohibition.

**Do not use the R3 approval count as medical ground truth or patient-facing evidence.**
