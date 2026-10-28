"""Phase 1 W1/W2/W3 live integration smoke test (fictional inputs only).

Start local FastAPI with FORCE_OFFLINE_RETRIEVER=1 and the Next.js
production server first. Then run this dependency-free smoke harness:

  python -m scripts.smoke_phase1 --backend http://127.0.0.1:8000 --frontend http://127.0.0.1:3000

Tests real HTTP boundaries, NOT medical correctness, clinical suitability,
accuracy, load, security pen-testing or actual user experience.
No real symptom narratives, patient data or real geolocation are used.
"""
from __future__ import annotations

import argparse
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SAMPLE = {
    "text": "fictional fever, cough, body aches",
    "lat": -33.8688, "lon": 151.2093, "top_k": 2,
}


def request_json(base: str, path: str, payload: dict | None = None,
                 *, content_type: str = "application/json") -> tuple[int, dict, dict]:
    body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
    req = Request(
        base.rstrip("/") + path,
        data=body,
        method="POST" if payload is not None else "GET",
        headers={"Content-Type": content_type, "Accept": "application/json"},
    )
    try:
        with urlopen(req, timeout=12.0) as response:
            return response.status, json.loads(response.read(512_000)), dict(response.headers)
    except HTTPError as exc:
        return exc.code, json.loads(exc.read(512_000)), dict(exc.headers)


def check_ready(backend: str, frontend: str, *, timeout: float = 25.0) -> None:
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        try:
            code, health, _ = request_json(backend, "/health")
            code2, proxy_health, _ = request_json(frontend, "/api/health")
            if code == 200 and health.get("status") == "healthy" and code2 == 200 and proxy_health.get("backend") == "ready":
                return
        except (URLError, TimeoutError, ValueError, TypeError):
            pass
        time.sleep(0.35)
    raise AssertionError("FastAPI and Next.js readiness checks did not become healthy")


def validate_result(result: dict) -> dict:
    assert result.get("research_use_only") is True, "Nonclinical scope flag missing"
    notice = str(result.get("ranking_score_notice", "")).lower()
    assert "not medical probabilities" in notice, "Uncalibrated-score warning missing"
    assert result.get("retrieval_mode") == "offline_tfidf_forced", "Unexpected offline mode"
    assert isinstance(result.get("diseases"), list), "Disease retrieval response missing"
    assert isinstance(result.get("recommendations"), list), "Facility response missing"
    mapping = result.get("recommendations_by_disease")
    assert isinstance(mapping, dict), "Per-condition facility output missing"
    assert result.get("resolved_location", {}).get("source") == "direct_coordinates", "Coordinates were lost"
    assert len(result["diseases"]) <= SAMPLE["top_k"], "Top-K limit not respected"

    facility_count = 0
    for condition in result["diseases"]:
        name = str(condition.get("disease_name") or condition.get("Disease") or "Unknown")
        assert name in mapping, "Missing facility group for retrieved condition"
        facilities = mapping[name]
        assert isinstance(facilities, list), "Facility group must be a list"
        assert len(facilities) <= 3, "Backend facility limit exceeded"
        for facility in facilities:
            explanation = facility.get("ranking_explanation")
            assert isinstance(explanation, dict), "W2 explanation not attached"
            assert explanation.get("score_kind") == "experimental_ranking_score_not_probability"
            assert "not independently verified" in str(explanation.get("disclosure", ""))
            features = explanation.get("features")
            assert isinstance(features, dict), "W2 numeric feature disclosure missing"
            facility_count += 1
    if result["diseases"]:
        name = str(result["diseases"][0].get("disease_name") or result["diseases"][0].get("Disease") or "Unknown")
        assert result["recommendations"] == mapping[name], "Legacy flat facility contract drift"
    return {"retrieval_mode": result["retrieval_mode"],
            "condition_count": len(result["diseases"]),
            "explained_facility_count": facility_count}


def run(backend: str, frontend: str) -> dict:
    check_ready(backend, frontend)
    direct_code, direct, _ = request_json(backend, "/predict", SAMPLE)
    proxy_code, proxied, headers = request_json(frontend, "/api/predict", SAMPLE)
    assert direct_code == proxy_code == 200, f"Unexpected /predict statuses: backend={direct_code}, proxy={proxy_code}"
    summary = validate_result(direct)
    validate_result(proxied)
    assert direct == proxied, "Proxy altered FastAPI research response"
    assert "no-store" in str(headers.get("Cache-Control") or headers.get("cache-control", "")).lower()

    for malformed in (
        {"text": "x", "lat": 0, "lon": 0, "top_k": 2},
        {"text": "fictional cough", "lat": 200, "lon": 0, "top_k": 2},
        {"text": "fictional cough", "top_k": 2},
    ):
        _, _, _ = request_json(backend, "/health")
        backend_status, _, _ = request_json(backend, "/predict", malformed)
        proxy_status, _, _ = request_json(frontend, "/api/predict", malformed)
        assert backend_status == proxy_status == 422, (
            f"Validation mismatch: backend={backend_status}, proxy={proxy_status}"
        )
    return {
        "protocol": "medipower-phase1-live-http-integration-smoke-v1",
        "status": "PASS_NONCLINICAL_INTEGRATION_ONLY",
        "backend_proxy_equal": True,
        "malformed_request_cases_rejected": 3,
        "test_input": "fictional_english_text_and_fixed_sample_coordinates_only",
        **summary,
        "limitations": "Not clinical, privacy, load, penetration, geolocation-accuracy or browser UX validation.",
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--backend", default="http://127.0.0.1:8000")
    p.add_argument("--frontend", default="http://127.0.0.1:3000")
    args = p.parse_args()
    print(json.dumps(run(args.backend, args.frontend), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
