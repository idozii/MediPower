"""W5 local deployment boundary smoke: operational health, NOT medical safety.

Uses only fixed fictional content. Default target is loopback. Never supply
patient data or a live location. No remote API token or account is needed.

  python -m scripts.w5_deployment_preflight --mode ready
  python -m scripts.w5_deployment_preflight --mode outage

Start Next.js and FastAPI as documented in research/W5_DEPLOYMENT_READINESS.md.
Only use outage mode after the FastAPI process has been stopped.
"""
from __future__ import annotations

import argparse
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SYNTHETIC_REQUEST = {
    "text": "fictional fever and cough for a research integration check",
    "lat": -33.8688,
    "lon": 151.2093,
    "top_k": 2,
}


def fetch_json(frontend: str, path: str, *, body: dict | None = None) -> tuple[int, dict, dict]:
    if not frontend.startswith("http://127.0.0.1:") and not frontend.startswith("http://localhost:"):
        raise ValueError("W5 preflight intentionally permits loopback HTTP only")
    encoded = None if body is None else json.dumps(body, separators=(",", ":")).encode("utf-8")
    req = Request(
        frontend.rstrip("/") + path,
        data=encoded,
        method="GET" if body is None else "POST",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=5.0) as response:
            return response.status, json.loads(response.read(16384)), dict(response.headers)
    except HTTPError as exc:
        return exc.code, json.loads(exc.read(16384)), dict(exc.headers)


def header(headers: dict, key: str) -> str:
    return str(next((v for k, v in headers.items() if k.lower() == key.lower()), ""))


def verify(mode: str, frontend: str, *, timeout: float = 15.0) -> dict:
    if mode not in {"ready", "outage"}:
        raise ValueError("Mode must be ready or outage")
    if not frontend.startswith("http://127.0.0.1:") and not frontend.startswith("http://localhost:"):
        raise ValueError("W5 preflight intentionally permits loopback HTTP only")

    deadline = time.monotonic() + timeout
    last_status = None
    while time.monotonic() < deadline:
        try:
            status, health, headers = fetch_json(frontend, "/api/health")
            last_status = (status, health.get("backend"))
            good = ((status == 200 and health.get("frontend") == "ready" and health.get("backend") == "ready")
                    if mode == "ready" else
                    (status == 503 and health.get("frontend") == "ready" and health.get("backend") == "unavailable"))
            if good:
                if "no-store" not in header(headers, "Cache-Control").lower():
                    raise AssertionError("Health endpoint may be cached")
                if header(headers, "X-Content-Type-Options").lower() != "nosniff":
                    raise AssertionError("Expected safe MIME header missing")
                break
        except (OSError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
            pass
        time.sleep(0.25)
    else:
        raise AssertionError(f"W5 health check did not reach {mode} state; last={last_status}")

    if mode == "outage":
        status, data, headers = fetch_json(frontend, "/api/predict", body=SYNTHETIC_REQUEST)
        if status != 502:
            raise AssertionError(f"Backend outage should fail closed with 502; got {status}")
        detail = data.get("detail")
        if detail != "Research backend could not be reached. Verify service status.":
            raise AssertionError("Outage response unexpectedly changed or exposed backend content")
        if "no-store" not in header(headers, "Cache-Control").lower():
            raise AssertionError("Failed proxy responses must not be cached")
        if header(headers, "X-Content-Type-Options").lower() != "nosniff":
            raise AssertionError("Failed proxy response missing MIME hardening")
    return {
        "protocol": "medipower-w5-local-deployment-readiness-v1",
        "status": "PASS_OPERATIONAL_CONTRACT_ONLY",
        "mode": mode,
        "frontend_backend_state": "ready" if mode == "ready" else "unavailable",
        "synthetic_predict_failure_checked": mode == "outage",
        "scope": "loopback-health-and-fail-closed-only",
        "limitations": "Not uptime monitoring, load testing, security certification, clinical performance or deployment approval.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frontend", default="http://127.0.0.1:3000")
    parser.add_argument("--mode", choices=["ready", "outage"], default="ready")
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()
    print(json.dumps(verify(args.mode, args.frontend, timeout=args.timeout), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
