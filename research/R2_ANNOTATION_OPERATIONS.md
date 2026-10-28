# R2 — Intent annotation operations (development only)

R2 extends the M11 study protocol. No independent dataset or actual reviewer judgments have been collected. Do not describe current local stress examples as external validation. All annotation texts stay in ignored research/private_data paths.

1. Source a new permission-reviewed development CSV with columns: query_id,text,split,source_id,template_family,source_origin,rights_basis. Use the blank source template. Do not reuse the known M8 prompts or mix test samples into development.
2. Run: python -m research.r2_annotation_packets --source research/private_data/intent_cohort/source_development.csv --out-dir research/private_data/intent_cohort/packets
3. Supply reviewer_A_packet.csv and reviewer_B_packet.csv to separate reviewers. Each fills the annotator_id and intent_label columns without viewing model outputs or each other's decisions. The reviewers themselves must be independently verified; this script cannot do that.
4. Where labels disagree, a third distinct reviewer completes a separate CSV with query_id,adjudicator_id,final_label.
5. Run: python -m research.r2_reconcile_annotations --source research/private_data/intent_cohort/source_development.csv --reviewer-a research/private_data/intent_cohort/packets/reviewer_A_packet.csv --reviewer-b research/private_data/intent_cohort/packets/reviewer_B_packet.csv --adjudications research/private_data/intent_cohort/adjudications.csv --out research/private_data/intent_cohort/development.csv
6. Omit --adjudications only if both reviewers agree on every record. The reconciler rejects incomplete labels, changed reviewer prompt text, repeated query identifiers and unreviewed disagreements.
7. Run: python -m research.validate_intent_cohort --development research/private_data/intent_cohort/development.csv --out research/outputs/r2-annotation-audit.json
8. Existing M11 development workflow: export_intent_cohort, export_intent_margins, evaluate_annotated_intent using threshold zero without tuning against the already-seen M8 examples.

Completion gates: actual rights and provenance verification, independent source groups, independent reviewer labeling, third-party adjudication, disjoint authorized final holdout, frozen protocol and group-aware reporting. This is engineering infrastructure until those requirements are met.
