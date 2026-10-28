"use client";

import { useMemo, useState } from "react";
import { formatRankingScore, makeRequestBody, validateResearchForm, MAX_SYMPTOM_CHARS } from "../lib/research-form.mjs";

const EXAMPLES = [
  {
    label: "Chest pain + shortness of breath",
    text: "chest pain and shortness of breath",
    location: "Austin, TX",
    top_k: 5
  },
  {
    label: "Flu-like symptoms",
    text: "fever, cough, body aches, sore throat",
    location: "Chicago, IL",
    top_k: 5
  },
  {
    label: "Abdominal pain",
    text: "lower abdominal pain with nausea",
    location: "Seattle, WA",
    top_k: 5
  }
];

const INITIAL_FORM = {
  text: "",
  location: "",
  lat: "",
  lon: "",
  top_k: 5
};

function formatNumber(value, digits = 2) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return "-";
  }
  return number.toFixed(digits);
}

function formatDistance(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return "-";
  }
  if (number < 1) {
    return `${Math.round(number * 1000)} m`;
  }
  return `${number.toFixed(1)} km`;
}

function scoreLabel(value) {
  return formatRankingScore(value);
}

export default function Page() {
  const [form, setForm] = useState(INITIAL_FORM);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const diseases = result?.diseases || [];
  const recommendationsByDisease = result?.recommendations_by_disease || {};
  const diseaseNames = useMemo(() => Object.keys(recommendationsByDisease), [recommendationsByDisease]);

  const activeRecommendations = useMemo(() => {
    if (diseaseNames.length > 0) {
      return recommendationsByDisease[diseaseNames[0]] || [];
    }
    return result?.recommendations || [];
  }, [diseaseNames, recommendationsByDisease, result]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (loading) return;
    const problem = validateResearchForm(form);
    if (problem) {
      setError(problem);
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch("/api/predict", {
        method: "POST",
        headers: {
          "content-type": "application/json"
        },
        body: JSON.stringify(makeRequestBody(form))
      });

      const data = await response.json();
      if (!response.ok) {
        const detail = typeof data?.detail === "string" ? data.detail : null;
        throw new Error(detail || "Research API is unavailable. Check the backend service.");
      }
      if (!data || !Array.isArray(data.diseases) || !data.research_use_only) {
        throw new Error("Unexpected research response format. Do not rely on these results.");
      }
      setResult(data);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Prediction request failed.");
    } finally {
      setLoading(false);
    }
  }

  function applyExample(example) {
    setForm((current) => ({
      ...current,
      text: example.text,
      location: example.location,
      top_k: example.top_k
    }));
  }

  return (
    <main id="main-content" className="shell">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">MediPower / Research prototype</p>
          <h1>MediPower — research-only condition information retrieval</h1>
          <p>
            Experimental condition retrieval and facility ranking for fictional examples only. Not a medical diagnosis, triage service, or substitute for qualified care. Do not enter identifying or real patient health information. In an emergency, contact your local emergency services.
          </p>
          <div className="hero-badges" aria-label="Research capabilities">
            <span>Reproducible retrieval</span>
            <span>Explainable ranking prototype</span>
            <span>Non-clinical evaluation</span>
          </div>
        </div>

        <div className="hero-card">
          <div className="hero-card-top">
            <span className="status-pill">Research boundary</span>
            <strong>Interpret outputs as hypotheses</strong>
          </div>
          <p>
            An experimental ranking score is not a disease probability, facility quality assessment, or clinical referral. The system may return an incorrect or incomplete set of candidates.
          </p>
        </div>
      </section>

      <section className="content-grid">
        <form className="panel form-panel" onSubmit={handleSubmit} aria-busy={loading} noValidate>
          <div className="panel-header">
            <div>
              <p className="section-label">Symptom intake</p>
              <h2>Explore candidate condition information (research only)</h2>
            </div>
            <div className="sample-row">
              {EXAMPLES.map((example) => (
                <button key={example.label} type="button" className="ghost-button" onClick={() => applyExample(example)}>
                  {example.label}
                </button>
              ))}
            </div>
          </div>

          <label htmlFor="research-symptoms">
            Fictional symptoms (research examples only)
            <textarea
              id="research-symptoms"
              name="research-symptoms"
              maxLength={MAX_SYMPTOM_CHARS}
              aria-describedby="symptom-hint"
              required
              value={form.text}
              onChange={(event) => setForm((current) => ({ ...current, text: event.target.value }))}
              placeholder="Use fictional example symptoms only; no real patient information"
            />
            <span id="symptom-hint" className="field-hint">Do not submit real patient information · {form.text.length}/{MAX_SYMPTOM_CHARS} characters</span>
          </label>

          <div className="field-grid">
            <label>
              Location text
              <input
                maxLength={160}
                value={form.location}
                onChange={(event) => setForm((current) => ({ ...current, location: event.target.value }))}
                placeholder="Example: Sydney CBD (fictional)"
              />
            </label>

            <div className="coord-grid">
              <label>
                Latitude
                <input
                  value={form.lat}
                  onChange={(event) => setForm((current) => ({ ...current, lat: event.target.value }))}
                  placeholder="Optional"
                  inputMode="decimal"
                />
              </label>
              <label>
                Longitude
                <input
                  value={form.lon}
                  onChange={(event) => setForm((current) => ({ ...current, lon: event.target.value }))}
                  placeholder="Optional"
                  inputMode="decimal"
                />
              </label>
            </div>
          </div>

          <label>
            Top K
            <input
              type="number"
              min="1"
              max="20"
              value={form.top_k}
              onChange={(event) => setForm((current) => ({ ...current, top_k: event.target.value }))}
            />
          </label>

          <div className="actions">
            <button type="submit" className="primary-button" disabled={loading}>
              {loading ? "Retrieving..." : "Explore research rankings"}
            </button>
          </div>

          <div role="status" aria-live="polite" aria-atomic="true">
            {error ? <p className="feedback error" role="alert">{error}</p> : <p className="feedback">Provide a city OR both coordinates. No patient data should be entered.</p>}
          </div>
        </form>

        <section className="panel results-panel" aria-busy={loading} aria-live="polite" aria-label="Experimental retrieval results">
          <div className="panel-header compact">
            <div>
              <p className="section-label">Results</p>
              <h2>Retrieved diseases and ranked clinics</h2>
            </div>
            {result ? <span className="status-pill muted">{result.retrieval_mode || "unknown"}</span> : null}
          </div>

          {!result ? (
            <div className="empty-state">
              <h3>{loading ? "Running research retrieval…" : "Awaiting a research query"}</h3>
              <p>{loading ? "The model is retrieving candidate information. Results are not a diagnosis." : "Enter a fictional example to explore ranked condition information and experimental facility options."}</p>
            </div>
          ) : (
            <div className="results-stack">
              <div className="summary-row">
                <div className="summary-card">
                  <span className="summary-label">Resolved location</span>
                  <strong>
                    {result.resolved_location?.source === "direct_coordinates"
                      ? `${formatNumber(result.resolved_location?.lat, 4)}, ${formatNumber(result.resolved_location?.lon, 4)}`
                      : `${result.resolved_location?.lat ?? "-"}, ${result.resolved_location?.lon ?? "-"}`}
                  </strong>
                </div>
                <div className="summary-card">
                  <span className="summary-label">Message</span>
                  <strong>{result.message || "Retrieval completed (not a diagnosis)"}</strong>
                </div>
              </div>

              <div className="result-block">
                <h3>Retrieved candidate conditions</h3>
                <div className="stack">
                  {diseases.length > 0 ? (
                    diseases.map((disease, index) => (
                      <article key={`${disease.disease_name || disease.Disease || index}`} className="result-card">
                        <div className="result-card-head">
                          <div>
                            <span className="rank-badge">#{index + 1}</span>
                            <h4>{disease.disease_name || disease.Disease || "Unknown disease"}</h4>
                          </div>
                          <span className="score-pill" title="Uncalibrated retrieval score; not a disease probability">Ranking score: {scoreLabel(disease.score ?? disease.confidence ?? disease.similarity)}</span>
                        </div>
                        <p>{disease.description || disease.summary || disease.reason || "No extra description returned."}</p>
                      </article>
                    ))
                  ) : (
                    <p>No suitable retrieval match returned; this tool cannot rule out illness.</p>
                  )}
                </div>
              </div>

              <div className="result-block">
                <h3>Experimental facility rankings</h3>
                <p className="research-disclosure">Facility scores can include simulated or unverified proxies. They do not assess clinical quality, availability or suitability. Always check the source data.</p>
                {diseaseNames.length > 0 ? (
                  diseaseNames.map((diseaseName) => (
                    <div key={diseaseName} className="recommendation-group">
                      <div className="group-title">
                        <h4>{diseaseName}</h4>
                        <span className="group-count">{(recommendationsByDisease[diseaseName] || []).length} options</span>
                      </div>
                      <div className="stack">
                        {(recommendationsByDisease[diseaseName] || []).map((item, index) => (
                          <article key={`${diseaseName}-${item.clinic_id || item.hospital_name || index}`} className="result-card recommendation-card">
                            <div className="result-card-head">
                              <div>
                                <span className="rank-badge">#{index + 1}</span>
                                <h4>{item.facility_name || item.hospital_name || "Unnamed facility"}</h4>
                              </div>
                              <span className="score-pill" title="Experimental ranking score, not quality or probability">{scoreLabel(item.score)}</span>
                            </div>
                            <p>{item.department_name || item.facility_type || "Care site"}</p>
                          {item.ranking_explanation?.disclosure ? <p className="field-hint">{item.ranking_explanation.disclosure}</p> : null}
                            {item.ranking_explanation?.disclosure ? <p className="field-hint">{item.ranking_explanation.disclosure}</p> : null}
                            <div className="metric-row">
                              <span>Distance {formatDistance(item.distance_km)}</span>
                              <span>Provider proxy {scoreLabel(item.provider_score)}</span>
                              <span>Retention proxy {scoreLabel(item.drop_rate == null ? null : 1 - item.drop_rate)}</span>
                            </div>
                          </article>
                        ))}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="stack">
                    {activeRecommendations.length > 0 ? (
                      activeRecommendations.map((item, index) => (
                        <article key={`${item.clinic_id || item.hospital_name || index}`} className="result-card recommendation-card">
                          <div className="result-card-head">
                            <div>
                              <span className="rank-badge">#{index + 1}</span>
                              <h4>{item.facility_name || item.hospital_name || "Unnamed facility"}</h4>
                            </div>
                            <span className="score-pill">{scoreLabel(item.score)}</span>
                          </div>
                          <p>{item.department_name || item.facility_type || "Care site"}</p>
                          <div className="metric-row">
                            <span>Distance {formatDistance(item.distance_km)}</span>
                            <span>Provider proxy {scoreLabel(item.provider_score)}</span>
                            <span>Retention proxy {scoreLabel(item.drop_rate == null ? null : 1 - item.drop_rate)}</span>
                          </div>
                        </article>
                      ))
                    ) : (
                      <p>No recommendation rows returned.</p>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}