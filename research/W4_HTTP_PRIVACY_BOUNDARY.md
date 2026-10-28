# W4 — HTTP request privacy boundary (supplemental hardening)

**Research demonstration only.** This PR follows privacy-by-default geocoding and does not establish privacy-law compliance, PII/PHI safety, production security or clinical reliability.

## What is covered

- FastAPI's default Pydantic RequestValidationError may return invalid user inputs in the error body. This is replaced by a fixed, non-reflecting 422 error message for malformed JSON, overlong text, invalid coordinates and other schema errors. The original request body must not be echoed.
- /predict, /health and /status return Cache-Control: no-store. Responses include X-Content-Type-Options: nosniff, Referrer-Policy: no-referrer and X-Frame-Options: DENY.
- Regression tests only use synthetic markers and do not access the model, internet or patient information.

## What remains unverified

- Uvicorn, reverse proxy, load balancer, CDN, access logs, tracing, APM, crash reports and external analytics may have their own retention behavior. This code does NOT prove those services do not record request bodies, URLs, IP addresses or headers. Verify operational logging policies separately.
- /predict still accepts arbitrary text; validation and non-reflecting errors do not detect all sensitive inputs.
- No rate limiting, DDoS defense or consent/authorization system is introduced. Public launch requires independent threat modeling, security testing, privacy assessment and provider terms review.
- The legacy FastAPI HTML page also contains inline JavaScript; do not enable a new restrictive CSP without an appropriate migration and browser tests.

## Production operator checklist

1. Disable request-body and query-string logging in all upstream services, and establish a retention/deletion schedule with evidence.
2. Review errors across FastAPI, Next proxy, CDN, telemetry and third-party tools, including request and exception traces.
3. Set ALLOW_EXTERNAL_GEOCODING=0 unless documented opt-in policy and disclosures exist.
4. Prefer anonymous fictional inputs, no real patient cases, and no identifying or precise real addresses.
5. Run CI and manually verify non-reflection and Cache-Control across deployed responses.
