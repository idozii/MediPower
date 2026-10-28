"""Generate an honest, reproducible *draft* retrieval results report from M4 JSON.

This script does not turn development results into test evidence or certify
scientific novelty, ethics, clinical efficacy, or paper acceptance.

Example:
 python -m research.build_research_report --comparison research/outputs/m4-comparison.json \
   --out research/outputs/paper/results_draft.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _format_ci(point: dict) -> str:
    if not isinstance(point, dict) or not isinstance(point.get("mean"), (int, float)):
        raise ValueError("Expected numeric mean")
    value = float(point["mean"])
    interval = point.get("ci95")
    if interval is None:
        return f"{value:.3f} (CI unavailable)"
    if not isinstance(interval, list) or len(interval) != 2:
        raise ValueError("Expected CI as two-element list")
    return f"{value:.3f} [{float(interval[0]):.3f}, {float(interval[1]):.3f}]"


def render(comparison: dict) -> str:
    if comparison.get("protocol") != "medipower-m4-paired-bootstrap-v1":
        raise ValueError("Unsupported comparison protocol")
    split = comparison.get("split")
    if split not in ("development", "test"):
        raise ValueError("Missing valid split")
    n = comparison.get("positive_queries")
    if not isinstance(n, int) or n < 1:
        raise ValueError("Missing positive query count")
    models = comparison.get("models")
    if not isinstance(models, dict) or not models:
        raise ValueError("No model evidence")
    k = comparison.get("k")
    if not isinstance(k, int) or k < 1:
        raise ValueError("Invalid K")
    label = "DEVELOPMENT-ONLY — NOT SUBMISSION-READY" if split == "development" else "UNVERIFIED TEST RESULTS — REQUIRE PROTOCOL AND SOURCE AUDIT"
    lines = [
        f"# MediPower retrieval study — {label}", "",
        f"Evaluation protocol: {comparison['protocol']}",
        f"Split: {split} | Positive queries: {n} | Negative controls: {comparison.get('negative_controls', 0)}",
        f"Baseline: {comparison.get('baseline')} | K: {k} | Bootstrap draws: {comparison.get('bootstrap_samples')}",
        "",
        "## Paired model comparisons", "",
        "| Model | Recall@K | MRR@K | nDCG@K | Δ Recall@K vs baseline | Negative false-positive rate |",
        "|---|---|---|---|---|---|",
    ]
    for name, result in sorted(models.items()):
        metrics = result["positive_metrics"]
        delta = result["difference_vs_baseline"]
        negatives = result.get("negative_false_positive_rate")
        fpr = "not measured" if negatives is None else f"{float(negatives):.3f} (n={result.get('negative_control_n')})"
        lines.append(f"| {name} | {_format_ci(metrics[f'recall@{k}'])} | "
                     f"{_format_ci(metrics[f'mrr@{k}'])} | "
                     f"{_format_ci(metrics[f'ndcg@{k}'])} | "
                     f"{_format_ci(delta[f'recall@{k}'])} | {fpr} |")
    lines += [
        "", "## Required interpretation",
        "- These are information retrieval metrics against the supplied disease ID labels, NOT diagnosis accuracy, patient safety, or effective treatment.",
        "- CIs, if present, use query-level paired bootstrap and are invalid as independent-case inference if queries share templates, patients or source clusters.",
        "- Verify source permissions, external ontology coverage, held-out split access, dataset and model hashes, and annotation protocol independently.",
        "- The table alone does not demonstrate novel research contribution or conference readiness.",
        "- Any test-split outcomes require proof of preregistration and authorized data access before publication.",
        "", "## Reproduction and provenance to complete",
        "- [ ] Record official dataset release, license, checksum and source URL.",
        "- [ ] Freeze reviewed pathology-to-catalog mapping and coverage limitations.",
        "- [ ] Record model versions, preprocessing, seeds, all prespecified hyperparameters and machine environment.",
        "- [ ] Supply source-disjoint checks and failure analyses; identify high-risk and off-catalog conditions.",
        "- [ ] Obtain independent medical/domain expert review before any clinical framing.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--comparison", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    report = json.loads(args.comparison.read_text(encoding="utf-8"))
    markdown = render(report)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(markdown, encoding="utf-8")
    print(f"Report draft written to {args.out}; source split={report.get('split')}. NOT clinical or peer-reviewed evidence.")


if __name__ == "__main__":
    main()
