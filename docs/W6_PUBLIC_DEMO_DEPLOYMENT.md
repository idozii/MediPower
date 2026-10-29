# W6 — Publish MediPower as a restricted research-only portfolio demo

**Status:** Configuration and UI are prepared for an opt-in deployment. No deployment, production URL, patient-facing evaluation, or clinical performance validation has occurred in this PR.

## Recommended topology

Browser → **Vercel** (Next.js, \`web/\`) → server-side \`/api/predict\` route → **Render** (Docker/FastAPI, offline TF-IDF) → bundled demonstration CSV data.

No database, analytics scripts, browser geolocation, real-person records, credentials or LLM API key needed. The browser must call the same-origin \`/api/predict\`, not Render directly.

A public demo should use only the three hardcoded **fictional scenarios**. UI selection is not a security boundary, so independent FastAPI and Next.js route allowlists are provided. Nothing in this project detects all personally identifying or medical details: do not describe it as PHI-safe.

## Why these services

- Vercel has native Next.js Git deployment and previews for the \`web\` root directory.
- Render deploys the Python API from a small offline Docker image; use \`/health\` as readiness probe.
- For a portfolio demo that should respond reliably, use a **paid always-on Render instance** if affordable. Render Free services spin down after 15 minutes idle and can take around a minute to cold start; Next.js proxy currently times out after 15 seconds. Free is fine to experiment, not for a responsive public launch. Check current provider pricing and quotas before enabling services.
- Vercel Hobby is restricted to personal/non-commercial use. Review eligibility; use a paid tier when required.
- No claim that split hosting is automatically private: traffic travels between providers over HTTPS. Verify provider logs, retention, region and security policies.

## Step 1 — Review and merge the W6 pull request

Verify GitHub Actions are green (Python tests, all Node tests, Next build, live HTTP smoke, demo Docker build). Manually check mobile/keyboard layouts, loading/error/empty states and all disclaimer wording. Do not auto-merge just because a build succeeds.

## Step 2 — Deploy backend to Render *first*

1. Render Dashboard → **New** → **Blueprint**; select \`idozii/MediPower\` and review \`render.yaml\`, or create a Docker Web Service using \`Dockerfile\` at repository root.
2. Choose the verified \`main\` commit. Keep manual deployments (\`autoDeployTrigger: off\`) until public release checks are completed.
3. Use the lightweight research demo container with these variables (already specified in \`render.yaml\`):
   - \`FORCE_OFFLINE_RETRIEVER=1\`
   - \`ALLOW_MODEL_DOWNLOAD=0\`
   - \`ALLOW_EXTERNAL_GEOCODING=0\`
   - \`MEDIPOWER_DEMO_PRESETS_ONLY=1\`
   - \`RETRIEVAL_QUERY_CACHE_SIZE=64\`
4. Probe path: \`/health\`. Expected 200 JSON: \`{"status":"healthy"}\`.
5. Check \`POST /predict\` refuses a *fictional but non-preset* JSON payload with HTTP 403. Never use patient information in tests.
6. Note the assigned backend URL, e.g. \`https://YOUR-RENDER-SERVICE.onrender.com\`. This is a placeholder, not a deployed URL. Do not use \`localhost\` for the Vercel environment variable.
7. Restrict/monitor the backend endpoint and its public direct reachability. A preset allowlist is not authentication, rate limiting, firewalling or a privacy compliance system. Consider a private-network topology where available after evaluation.

### Docker image policy

This Dockerfile is intentionally **offline-TF-IDF only**. It installs \`requirements-demo.txt\`, not \`requirements.txt\`: the latter includes SentenceTransformers, Torch and FAISS for separate research experiments. Heavy semantic retrieval should use its own reviewed deployment rather than accidentally download models on a public demo. Avoid including the private R2/R3 datasets, experiment outputs or environment files in the container.

## Step 3 — Deploy Next.js on Vercel

1. Vercel → **Add New → Project** → import \`idozii/MediPower\` from GitHub.
2. Set **Root Directory = \`web\`** (critical; the repo root is a Python app, not the Next.js project).
3. Framework: **Next.js**. Use detected \`npm ci\` / \`npm run build\` defaults, Node 20 or compatible supported Node LTS. Do not force a static HTML export: \`/api/predict\` and \`/api/health\` are server-side routes.
4. Vercel → Project → Settings → Environment Variables. Add:
   - \`HEALTHCARE_AI_API_BASE_URL=https://YOUR-RENDER-SERVICE.onrender.com\` **server-only**, for Preview/Production as appropriate.
   - \`MEDIPOWER_PRESET_ONLY=1\` **server-only** on public Preview/Production.
   - \`NEXT_PUBLIC_MEDIPOWER_CUSTOM_INPUT=0\` (optional: public UI is sample-only by default; NEVER put secrets in \`NEXT_PUBLIC_...\`).
5. Trigger Preview deployment and verify the generated URL. Promote to Production only after testing. Environment-variable edits require a new deployment.
6. Verify HTTPS, responsive rendering, correct environment-specific backend URL and no unauthorized external scripts. Connect your custom domain only after final review.

**Do not point \`HEALTHCARE_AI_API_BASE_URL\` to \`http://127.0.0.1:8000\` from Vercel.** That is the Vercel instance's own loopback, not your laptop or Render.

## Step 4 — Verify the hosted deployment

- On Vercel: \`GET https://YOUR-VERCEL-DOMAIN/api/health\` should return \`{"frontend":"ready","backend":"ready"}\`. It depends on Render reaching READY state.
- Click all three fictional scenarios. The model result must be labeled experimental, with source/proxy disclosures. Compare basic behavior to local smoke.
- Submit an unknown sample to the frontend API **using invented fictional text only** and verify HTTP 403. Verify direct Render API also returns 403 for the same invalid preset.
- Stop or temporarily suspend the backend in staging and confirm the proxy returns a non-sensitive error (502/504 as applicable), not a fabricated successful result.
- Run a mobile and keyboard accessibility pass (focus order, aria-live, contrast, disclosure controls).
- Confirm no real-world facility-quality claims or diagnosis wording are present.
- Audit platform logs, reverse proxies, IP retention, analytics, rate limits and abuse handling before sharing broadly. Disable public access if unexpected user submissions occur.

## Local preview

From \`~/Desktop/MediPower\`, with your Python environment activated:

Terminal 1:

    FORCE_OFFLINE_RETRIEVER=1 ALLOW_MODEL_DOWNLOAD=0 ALLOW_EXTERNAL_GEOCODING=0 MEDIPOWER_DEMO_PRESETS_ONLY=1 python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

Terminal 2:

    npm ci --prefix web
    npm run build --prefix web
    HEALTHCARE_AI_API_BASE_URL=http://127.0.0.1:8000 MEDIPOWER_PRESET_ONLY=1 npm start --prefix web -- --hostname 127.0.0.1 --port 3000

Visit \`http://127.0.0.1:3000\`. Browser runs preset-only mode. For **private local research**, both allowlist environment variables may be omitted and \`NEXT_PUBLIC_MEDIPOWER_CUSTOM_INPUT=1\` may be set *before the Next build*. Never set those relaxed values in public deployment.

## Release blockers

This is **not clinical deployment approval**. Before unrestricted public demo access: set up platform-layer rate limiting, access controls, monitoring, privacy statement and log retention; verify licensing of facility/proxy datasets; check geographic region and hosting costs; use restricted preview while review is incomplete. R2 intent study and R3 mapping provenance are still externally blocked. The demo may return incorrect or misleading condition names.
