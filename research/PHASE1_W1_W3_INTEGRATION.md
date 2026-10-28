# Phase 1 — Integrated W1/W2/W3 verification

**Current status:** W1 (#15/#19), W2 (#16), W3 (#17), R2 tooling (#18), and security fix (#20) were merged to main before this PR. This milestone adds an integration **verification gate**, not new medical evidence.

## Covered functionality

- Production Next.js server and FastAPI server start on loopback addresses with the explicitly forced **offline TF-IDF** retriever.
- `GET /health` on FastAPI and `GET /api/health` via Next agree that the backend is reachable.
- `POST /predict` on FastAPI and `POST /api/predict` via Next with the same fictional query/coordinates yield equivalent JSON, preserve the research-only flag and the uncalibrated-score warning.
- W2 adds a facility ranking_explanation to every returned facility in each per-condition group, including source type, experimental metric features and a disclosure that these are not independently verified.
- W3 ensures invalid bounds (short text, impossible coordinates and missing location) lead to HTTP 422 at **both** HTTP boundaries; no PHI is used or submitted.
- Next response has no-store cache semantics; no patient narratives are logged by the smoke tool.
- CI runs all 8 frontend tests instead of only 4 proxy-contract tests, the 87 Python research tests, and the real loopback HTTP integration job.

## Run locally on current branch

At repository root, set up one terminal:

    FORCE_OFFLINE_RETRIEVER=1 ALLOW_MODEL_DOWNLOAD=0 python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

In a separate terminal:

    cd web
    npm ci
    npm run build
    HEALTHCARE_AI_API_BASE_URL=http://127.0.0.1:8000 npm run start -- --hostname 127.0.0.1 --port 3000

In a third terminal at the repository root:

    python -m scripts.smoke_phase1 --backend http://127.0.0.1:8000 --frontend http://127.0.0.1:3000

Expected success result: `PASS_NONCLINICAL_INTEGRATION_ONLY` with checked backend/proxy parity. The exact retrieved condition names and ranking values are **not** expected or asserted.

## What passing does NOT prove

This does not measure condition-ranking accuracy, disease diagnostic validity, facility performance, clinician-approved risk assessment, real geolocation correctness, security penetration testing, cross-browser responsiveness, uptime or load performance. It is not a medical-product deployment approval. The previous M9 semantic intent gate that rejected 8/10 development symptom prompts remains disabled in production.

## Outstanding R2 dependencies

R2 code has prepared two-reviewer packet and adjudication workflows, but external independent authorship, rights approval, source-disjoint corpus, double annotation and third-party adjudication still need to happen outside GitHub. M11 protocol and test access restrictions remain in force.

## Follow-on work

After smoke/test gate is green and user visual testing on desktop/mobile passes, next stage can focus on W4 privacy/security hardening and R3 dataset rights/ontology review (without claiming clinical validation).
