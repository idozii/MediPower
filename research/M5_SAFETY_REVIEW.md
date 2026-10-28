# M5 — Healthcare research transparency and safety boundaries

## Scope
This is a research demonstration, not clinically validated diagnosis, triage, navigation or treatment. No performance or patient-safety certification is claimed.

## Changes in this milestone
- FastAPI request limits: 3–2000 characters of symptom text, location <=160 chars and latitude/longitude restricted to legal numeric bounds. Add explicit research and non-probability notices to API responses.
- Update embedded FastAPI demo and Next.js frontend to identify outputs as information-retrieval candidate ranking, NOT diagnosis. Avoid use of real patient information.
- Remove the hard-coded U.S.-only emergency phone number. Guidance uses local emergency services without claiming the system detects every urgent condition.
- Add source-level regression checks, Python compilation, and Next.js production build to CI.

## Required external approvals before real deployment
1. Identify and independently verify intended users, locations, critical-symptom scenarios and safe fallback behavior. Have qualified healthcare experts review high-risk workflows.
2. Evaluate sensitivity to relevant clinical red flags, abstention and failure-to-refer. This repo currently has NO clinically validated detection rules. Do not claim comprehensive emergency detection.
3. Check dataset quality, rights, subgroup representativeness and provider data provenance. Hospital rankings are not evidence of service quality.
4. Create privacy policy: confirm actual geocoder/provider requests, logs, retention of symptom strings and coordinates, hosting jurisdiction and consent. Do not submit sensitive real patient information to a public demo.
5. Add authentication, rate limits, abuse controls and deployment threat model as appropriate. Current code improvements are **not** a security audit or HIPAA/GDPR compliance assessment.
6. Clinical governance and relevant local regulatory obligations require professional assessment if targeting real care decisions.

## Local checks
    python -m unittest discover -s tests -v
    python -m compileall -q app research tests
    npm ci --prefix web
    npm run build --prefix web

Check PR CI jobs for Python and Next.js build. The test suite verifies warnings and input bounds, not medical correctness. Keep a clinical release blocker until external evidence exists.
