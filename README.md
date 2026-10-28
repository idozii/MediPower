# MediPower — Healthcare Information Retrieval & Care-Navigation Research Prototype

## Goal
Build a web service that:
1. Takes user symptom text
2. Ranks candidate condition information for exploratory retrieval (NOT a diagnosis)
3. Produces experimental department/facility rankings (NOT treatment or clinical referrals) based on:
   - distance
   - provider performance
   - drop-off rate
   - patient flow efficiency

> **Research demonstration only.** Outputs are unvalidated ranking hypotheses, not medical advice, clinical diagnosis, or emergency triage. The legacy retrieval `confidence` field is a heuristic ranking score, not a calibrated probability. Do not enter real patient information.

See [research/README.md](research/README.md) for our evaluation protocol, leakage audit priorities, restrictions and a tested offline ranking-metrics scaffold. No independent clinical benchmark results are currently claimed.

## Milestone M2: leakage audit and baseline benchmarks

See [M2 research runbook](research/M2_BENCHMARK.md) for reproduction commands, independently verified descriptive dataset counts, TF-IDF/BM25/dense/hybrid baselines and important clinical limitations. The production API currently calls the retrieval service, not the separately trained 8-class LogisticRegression classifier. Do not describe the classifier's historical 100% score as independently validated medical performance.


### M3/M4 follow-up: external ontology review and abstention gate

[Development-only DDXPlus mapping coverage and abstention ablation guide](research/M7_COVERAGE_AND_ABSTENTION.md). The 49 synthetic source pathologies have NOT been independently matched to the 29-condition catalog. Dense/Hybrid false positives on one toy negative query motivated a controlled lexical-overlap gate experiment; no clinical safety or generalization claims are made.

## Research milestones (M1–M6)

The repo is a **nonclinical research prototype**. M1/M2 establish evaluation, leakage auditing and lexical baselines. M3/M4/M5/M6 extend the research pipeline but **external data/clinician-approved test results have NOT been collected**. Do not use with real patient data or for medical decisions.

- [M3: approved external synthetic dataset protocol](research/M3_EXTERNAL_EVALUATION.md)
- [M4: controlled ablations and paired robustness evaluation](research/M4_ABLATIONS.md)
- [M5: safety, privacy and transparency checklist](research/M5_SAFETY_REVIEW.md)
- [M6: reproducibility and paper-readiness blockers](research/M6_REPRODUCIBILITY.md)
- [Provisional manuscript outline](research/paper/MANUSCRIPT_OUTLINE.md)

Development-only source audit results are documented at [M2](research/results/M2_DEV_AUDIT_2026-10-28.md). Scientific and clinical generalization claims remain blocked pending external source verification, expert-reviewed mapping and independent held-out evaluation.

## Architecture
User Input -> Disease Retrieval (Embedding + FAISS)
           -> Top-K Diseases
           -> Department Mapping
           -> Scoring Engine
           -> Ranked Hospitals

## Stack
- FastAPI for the diagnosis and recommendation backend
- Next.js for the deployable frontend
- SentenceTransformers
- FAISS
- PostgreSQL (optional)
- Pandas / NumPy
- NetworkX (optional)

## Project Structure
healthcare-ai/
|- app/
|  |- main.py
|  |- api/
|  |  |- routes.py
|  |- models/
|  |- services/
|  |- data/
|  |- utils/
|  |- config.py
|- web/
|  |- app/
|  |  |- api/predict/route.js
|  |  |- globals.css
|  |  |- layout.js
|  |  |- page.js
|  |- package.json
|  |- next.config.mjs
|- notebooks/
|- requirements.txt
|- README.md

## Setup
1. Create and activate a Python virtual environment.
2. Install dependencies:
   pip install -r requirements.txt

## Run Server
uvicorn app.main:app --reload

## Deploy on Vercel
The easiest Vercel path is to deploy the Next.js frontend in `web/` and keep the Python backend running separately.

1. Deploy the Python API anywhere that can run FastAPI, such as Render, Railway, Fly.io, or a VM.
2. Set `HEALTHCARE_AI_API_BASE_URL` in the Vercel project to the public URL of that backend.
3. In Vercel, set the project root directory to `healthcare-ai/web`.
4. Deploy the Next.js app.

The frontend will call `/api/predict`, and that route proxies requests to the Python backend.

### Frontend setup
From `healthcare-ai/web`:

1. Install dependencies: `npm install`
2. Start local dev server: `npm run dev`
3. Build for production: `npm run build`

### Environment variables for Vercel
- `HEALTHCARE_AI_API_BASE_URL=https://your-backend.example.com`

### Local development
- Run the Python backend: `uvicorn app.main:app --reload`
- Run the Next.js frontend in another terminal: `cd web && npm run dev`

## Deploy on Render
This project still includes the Python deployment path with `render.yaml`.

Quick steps:
1. Push code to GitHub.
2. In Render dashboard, click New + -> Blueprint.
3. Select your repository and apply the Blueprint.

Render will auto-configure:
- Build command: use `healthcare-ai/` as the working directory if the repo is deployed from the root
- Start command: use `healthcare-ai/` as the working directory if the repo is deployed from the root
- Environment variables from render.yaml.

Optional (recommended) in Render dashboard Environment Variables:
- MIN_DISEASE_CONFIDENCE=0.20
- HYBRID_DENSE_WEIGHT=0.65
- RETRIEVAL_CANDIDATE_POOL=120
- RETRIEVAL_QUERY_CACHE_SIZE=256

Local override for full semantic mode:
- FORCE_OFFLINE_RETRIEVER=0 uvicorn app.main:app --reload

## Test API
POST /predict
{
  "text": "chest pain and shortness of breath",
  "lat": -33.86,
  "lon": 151.20,
  "top_k": 5
}

## Clinic Matrix + Diagnosis Mapping
To enable diagnosis-specific clinic scoring with these files:
- clinic_profiles.csv
- clinic_retention.csv
- clinic_diagnosis_volume.csv

Add a manual mapping table:
- disease_to_code_manual.csv with columns: disease_name,DiagnosisValue

Then run:
- Dry run (no write):
   python scripts/map_disease_to_diagnosis_value.py --project-root .
- Apply updates into app/data/diseases.csv:
   python scripts/map_disease_to_diagnosis_value.py --project-root . --write

Auto-suggest DiagnosisValue from diagnosis dictionary:
- Dry run with suggestions:
   python scripts/map_disease_to_diagnosis_value.py --project-root . --auto-suggest
- Auto-apply confident suggestions and write:
   python scripts/map_disease_to_diagnosis_value.py --project-root . --auto-suggest --min-score 0.72 --write

The script also writes:
- disease_mapping_unresolved.csv
so you can quickly review diseases that still need a valid DiagnosisValue.
- disease_code_suggestions.csv
  includes top candidate codes and similarity scores per disease.

## Next Upgrade Ideas
- FAISS IVF index for faster search
- Caching embeddings with Redis
- Graph-based ranking using NetworkX
- Explanation layer for recommendation transparency

### M8 — Source-aware stress testing

[Reproducible, development-only abstention stress tests and cluster-aware evaluation](research/M8_CLUSTERED_STRESS.md). This adds constructed nonclinical overlap cases, subgroup audits, and grouping of duplicate synthetic symptom narratives for paired uncertainty estimates. These examples were designed after viewing earlier failures and are **not independent validation**. Clinical ontology mapping and official test access remain blocked.

### M9 — Task-intent-aware research abstention

[M9 two-stage zero-shot intent ablation and source-disjoint evaluation requirements](research/M9_INTENT_AWARE_ABSTENTION.md). On a post-hoc 30-query stress suite, lexical overlap alone could not distinguish medical terminology used in nonclinical tasks from genuine symptom descriptions. M9 separates a generic query-task intent gate from disease catalog ranking **for development diagnostics only**; this is not clinically validated and is not enabled in the public API.

### M10 — Intent risk–coverage diagnostics

[M10: frozen M9 intent margins, false-abstention analysis and descriptive risk–coverage grid](research/M10_INTENT_RISK_COVERAGE.md). The owner's post-hoc M9 local run rejected 8/10 constructed symptom-information queries despite reducing off-topic false positives, so the experimental gate is **not approved for production**. M10 does not tune the gate or claim independent validation.
