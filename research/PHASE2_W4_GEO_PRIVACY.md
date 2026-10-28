# Phase 2 — W4 Geocoding privacy boundary

**Status:** research demo privacy hardening, NOT privacy-law compliance certification.

## Why this change

The previous geocoder silently sent unknown free-form location text to a public third-party Nominatim endpoint. A user might enter a private street address or identifying details. The new default is **no external geocoding requests**.

- `ALLOW_EXTERNAL_GEOCODING=0` (default): only explicit latitude/longitude and built-in coarse demo cities (e.g. Sydney CBD, Melbourne, Brisbane) resolve. Unknown locations are rejected; location text never leaves the service through this geocoding fallback.
- `ALLOW_EXTERNAL_GEOCODING=1`: opt-in third-party lookup via Nominatim for unknown location text. **Do not enable in a real public demo** until a privacy review, disclosures, appropriate consent and third-party terms/rate-limit policy are in place.
- Resolved-location API dictionaries no longer echo the original free-form location query.
- Known-city examples in the Next.js UI are updated to work without a network geocoder. Frontend copy explains limited demo city support.

## Local regression

    python -m unittest discover -s tests -v

    FORCE_OFFLINE_RETRIEVER=1 ALLOW_EXTERNAL_GEOCODING=0 uvicorn app.main:app --reload

Use an explicit coordinate pair or known demo city; unknown city text correctly returns a location resolution error. This is a *privacy default* and does not establish the correctness or currentness of the small hardcoded city list.

## Outstanding W4 blockers

- Explicit documented retention/deletion policy and a check that production logs contain no input narratives, location text or personally identifiable information.
- Rate limiting and abuse prevention at an appropriate perimeter with shared state; in-process counters are insufficient on serverless multi-instance services.
- Secret/config management, dependency/security testing beyond npm audits, threat modeling, external provider terms and access control.
- User experience and accessibility/privacy consent review, plus independent security/privacy assessment before any public release.

There is no diagnostic, emergency triage, clinical or patient-facing validation from this work.
