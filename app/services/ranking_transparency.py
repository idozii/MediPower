"""Transparency-only facility output: DO NOT modify the ranking algorithm.

Ranking sources contain demo/proxy signals; data are not verified as official
provider ratings or audited health outcomes. This module adds factual fields
and warnings without making clinical suitability claims.
"""
from __future__ import annotations

import math


def _bounded_score(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return round(number, 4) if math.isfinite(number) and 0 <= number <= 1 else None


def _distance(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return round(number, 3) if math.isfinite(number) and number >= 0 else None


def explain_facility_ranking(row: dict, *, matrix_enabled: bool) -> dict:
    """Return provenance and interpretable raw score features; no clinical claims."""
    retention = str(row.get("retention_source") or "").strip()
    if matrix_enabled and retention == "diagnosis_retention":
        source = "imported_diagnosis_retention_unverified"
        retention_detail = "Retention inferred from imported diagnosis-specific records; independently unverified."
    elif matrix_enabled:
        source = "structural_proxy"
        retention_detail = "Retention is a calculated structural proxy, not observed patient retention."
    else:
        source = "local_demo_provider_table"
        retention_detail = "Drop-off is from a local demonstration dataset; verification unavailable."

    score = _bounded_score(row.get("score"))
    return {
        "score_kind": "experimental_ranking_score_not_probability",
        "source_type": source,
        "features": {
            "straight_line_distance_km": _distance(row.get("distance_km")),
            "provider_proxy": _bounded_score(row.get("provider_score")),
            "drop_fraction": _bounded_score(row.get("drop_rate")),
            "flow_proxy": _bounded_score(row.get("flow_efficiency")),
            "experimental_total": score,
        },
        "retention_note": retention_detail,
        "disclosure": "Experimental comparison only. Facility data and quality proxies are not independently verified; distance is straight-line, not travel time. Not clinical referral advice.",
    }


def annotate_ranked_facilities(items: list[dict], *, matrix_enabled: bool) -> list[dict]:
    """Copy rows before annotating, keeping source data and scores unchanged."""
    if not isinstance(items, list):
        raise TypeError("Facility recommendations must be list rows")
    output = []
    for item in items:
        if not isinstance(item, dict):
            raise TypeError("Facility recommendation must be an object")
        row = dict(item)
        row["ranking_explanation"] = explain_facility_ranking(row, matrix_enabled=matrix_enabled)
        output.append(row)
    return output
