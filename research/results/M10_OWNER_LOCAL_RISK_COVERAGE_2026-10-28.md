# M10 — Owner-supplied intent margin and risk–coverage diagnostic evidence (28 October 2026)

**Evidence provenance:** results pasted by project owner from local development run. The actual source files/model revision were not independently reproduced in GitHub Actions. No newly annotated clinical or nonclinical benchmark was collected.

- Protocol: medipower-m10-development-intent-risk-coverage-v1.
- Queries: 30 developer-authored M8 development examples, 10 positive symptoms, 20 nonclinical negatives.
- Query SHA256: a420e90b9ed9ee5a990fedaeff7c0fab36d656a7f36186232e31f8521a1340a1.
- Catalog SHA256: 29da44311044269c857adb1bae430bc9c917899465122852d6b838b0870ca7c8.
- M9 prototype SHA256: d9f7d097bd36866d061bf1c3bed6dac7c2feac5be1eb9a5d4547f600900c4618.
- Encoder: all-MiniLM-L6-v2, exact model revision not pinned.
- Intent margin (symptom prototype max cosine minus other task prototype max cosine) ranged **-0.0814011 to 0.0744406**.
- At threshold 0, 9/30 accepted: 2/10 positive symptoms accepted; 7/20 nonclinical negatives incorrectly accepted; 8/10 positive symptoms wrongly abstained.
- At threshold -0.05: positive retention 9/10; nonclinical false accepts 19/20.
- At threshold 0.05: positive retention 1/10; nonclinical false accepts 1/20.
- At thresholds 0.10, 0.15, 0.25, **none accepted**: false accepts are zero ONLY because every positive is rejected.
- At threshold 0, medically overlapping nonclinical requests falsely accepted 2/10; clean nonclinical requests 5/10.

| Intent threshold | Accepted overall | Symptom retention | Nonclinical false accept rate | End-to-end positive Recall@3 |
| ---: | ---: | ---: | ---: | ---: |
| -0.10 | 30/30 | 10/10 | 20/20 | 1.0 |
| -0.05 | 28/30 | 9/10 | 19/20 | 0.9 |
| 0 | 9/30 | 2/10 | 7/20 | 0.2 |
| 0.05 | 2/30 | 1/10 | 1/20 | 0.1 |
| 0.10 | 0/30 | 0/10 | 0/20 | 0 |

**Interpretation:** large overlap between these margin-defined decisions and off-topic negatives; the prototype-similarity zero threshold is not an adequate task-intent classifier. The threshold grid cannot establish that no alternative classifier would work. No threshold may be selected post-hoc on this already observed data and reported as independent validation.

## Next experiment

Do not introduce more prompts tuned to M8. Instead, M11 creates a **separate, prospectively sourced, double-annotated** intent cohort with distinct source/author/template groups and independent test governance. This data is NOT yet available, and no clinical / official test evidence has been produced.
