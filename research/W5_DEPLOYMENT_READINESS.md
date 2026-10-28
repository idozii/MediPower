# W5 — Local deployment readiness and backend outage response

**Status:** offline/loopback operational smoke only. This milestone does **not** deploy MediPower, monitor external availability or approve medical use. No production application endpoint is contacted or configured by this PR.

## Why W5

W1–W4 already verify valid research requests, privacy boundaries, frontend errors and API proxy behavior. A deployment must also fail predictably **when the backend is offline**, without reflecting internal errors, silently caching the failure or returning a success code.

## Verification implemented

1. Existing CI live integration job starts Next.js **production** build and FastAPI on 127.0.0.1, with `FORCE_OFFLINE_RETRIEVER=1`, `ALLOW_MODEL_DOWNLOAD=0`, and the sample research-only dataset. W1–W4 HTTP smoke verifies both services.
2. After this passes, CI deliberately stops FastAPI and runs `scripts.w5_deployment_preflight --mode outage`.
3. The preflight expects `GET /api/health` to report HTTP 503 and `backend: unavailable`; `POST /api/predict` with **one fixed fictional text** must report sanitized HTTP 502, no-store and nosniff headers.
4. It rejects non-loopback origins to prevent accidental requests to real hosted demos, and never writes actual query text or identifying location information to a report. Synthetic unit tests verify the operational contract.

## Manual local check

From repo root, first run both services in separate terminals:

**Terminal 1**

    FORCE_OFFLINE_RETRIEVER=1 ALLOW_MODEL_DOWNLOAD=0 ALLOW_EXTERNAL_GEOCODING=0 python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

**Terminal 2 (at repo root)**

    npm ci --prefix web
    npm run build --prefix web
    HEALTHCARE_AI_API_BASE_URL=http://127.0.0.1:8000 npm run start --prefix web -- --hostname 127.0.0.1 --port 3000

**Terminal 3**

    python -m scripts.smoke_phase1
    python -m scripts.w5_deployment_preflight --mode ready

Now stop **only Terminal 1's** FastAPI using Ctrl+C, leave Next.js running and check:

    python -m scripts.w5_deployment_preflight --mode outage

Do not claim a fail-open/fail-closed readiness check passed unless both scenarios have been observed. On completion, restart FastAPI as needed.

## Deployment review blockers (manual, not solved by this PR)

- Choose hosting provider and topology. Do not assume a hosting choice. Ensure backend address is a **server-only** environment variable `HEALTHCARE_AI_API_BASE_URL`. Do not store API keys in `NEXT_PUBLIC_...`.
- Restrict access to the fictional research demo; do **not** accept real patient details, store PHI or represent research predictions as diagnoses/medical triage.
- Verify rate limiting, authentication, runtime resource limits, autoscaling, health check configuration and backend outage alarms in the **actual hosting environment**.
- Review privacy/access logs, third-party analytics, retention and deletion at CDN/host/tracing layers; `Cache-Control` and sanitized errors do not prove data protection.
- Document model checkpoint/catalog provenance, catalog version and date; the service can fall back to offline TF-IDF rather than proving semantic model readiness.
- Deploy a restricted/staging demo and run manual mobile/browser/a11y checks, a consent/privacy review and independent security testing before any public demo.
- R2/R3 remain blocked on independently approved rights, annotation and ontology mapping. W5 success is neither medical nor scientific validation.

**CI status is only a proxy for loopback reliability**, not measured uptime or incident response maturity.
