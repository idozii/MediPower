"use client";

import { useEffect, useMemo, useState } from "react";
import { formatRankingScore, makeRequestBody, validateResearchForm, MAX_SYMPTOM_CHARS } from "../lib/research-form.mjs";
import { EXAMPLES } from "../lib/demo-presets.mjs";

const CUSTOM_INPUT_ENABLED = process.env.NEXT_PUBLIC_MEDIPOWER_CUSTOM_INPUT === "1";
const EMPTY_FORM = { text: "", location: "", lat: "", lon: "", top_k: 5 };

function Glyph({ name, size = 20 }) {
  const common = { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.75, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true };
  const paths = {
    spark: <><path d="m12 3 1.9 6.1L20 11l-6.1 1.9L12 19l-1.9-6.1L4 11l6.1-1.9L12 3Z"/><path d="m19 18 .7 2.3L22 21l-2.3.7L19 24l-.7-2.3L16 21l2.3-.7L19 18Z"/></>,
    arrow: <><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></>,
    shield: <><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/></>,
    layers: <><rect x="3" y="4" width="18" height="14" rx="2"/><path d="M7 21h10M8 8h8M8 12h5"/></>,
    activity: <><path d="M2 12h5l3-8 4 16 3-8h5"/></>,
    map: <><path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3V6Z"/><path d="M9 3v15m6-12v15"/></>,
    refresh: <><path d="M20 11a8 8 0 0 0-14-5L4 8"/><path d="M4 4v4h4"/><path d="M4 13a8 8 0 0 0 14 5l2-2"/><path d="M20 20v-4h-4"/></>,
    chevron: <><path d="m6 9 6 6 6-6"/></>,
    flask: <><path d="M9 3h6m-5 0v7l-5.7 8.2A2 2 0 0 0 6 21h12a2 2 0 0 0 1.7-2.8L14 10V3"/><path d="M8 15h8"/></>,
    pin: <><path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></>,
    info: <><circle cx="12" cy="12" r="9"/><path d="M12 11v5m0-8h.01"/></>,
  };
  return <svg {...common}>{paths[name] || paths.info}</svg>;
}

function formatDistance(value) {
  if (value === null || value === undefined || value === "") return "Not available";
  const number = Number(value);
  if (!Number.isFinite(number) || number < 0) return "Not available";
  return number < 1 ? Math.round(number * 1000) + " m" : number.toFixed(1) + " km";
}

function EvidenceBadge({ children }) {
  return <span className="evidence-badge">{children}</span>;
}

function FacilityCard({ item, index }) {
  const details = item.ranking_explanation;
  return (
    <article className="facility-card">
      <div className="facility-main">
        <div className="facility-order">{String(index + 1).padStart(2, "0")}</div>
        <div className="facility-text">
          <h5>{item.facility_name || item.hospital_name || "Unspecified demonstration facility"}</h5>
          <p>{item.department_name || item.facility_type || "Department not stated"}</p>
        </div>
        <div className="facility-score">
          <span>Experimental score</span>
          <strong>{formatRankingScore(item.score)}</strong>
        </div>
      </div>
      <div className="facility-metrics">
        <span><Glyph name="pin" size={15}/> Straight-line {formatDistance(item.distance_km)}</span>
        <span>Provider proxy {formatRankingScore(item.provider_score)}</span>
      </div>
      <details className="explain-details">
        <summary>How this row is explained <Glyph name="chevron" size={17}/></summary>
        <p>{details?.disclosure || "No verified facility-quality evidence is available."}</p>
        {details?.source_type ? <p><strong>Data source:</strong> {details.source_type.replaceAll("_", " ")}</p> : null}
        {details?.retention_note ? <p>{details.retention_note}</p> : null}
      </details>
    </article>
  );
}

export default function Page() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [selectedExample, setSelectedExample] = useState(-1);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [backend, setBackend] = useState("checking");
  const [showCoordinates, setShowCoordinates] = useState(false);

  async function refreshHealth() {
    setBackend("checking");
    try {
      const response = await fetch("/api/health", { cache: "no-store" });
      const data = await response.json();
      setBackend(response.ok && data.backend === "ready" ? "ready" : "unavailable");
    } catch {
      setBackend("unavailable");
    }
  }

  useEffect(() => {
    let active = true;
    fetch("/api/health", { cache: "no-store" })
      .then(async response => ({ ok: response.ok, data: await response.json() }))
      .then(({ ok, data }) => { if (active) setBackend(ok && data.backend === "ready" ? "ready" : "unavailable"); })
      .catch(() => { if (active) setBackend("unavailable"); });
    return () => { active = false; };
  }, []);

  const diseases = Array.isArray(result?.diseases) ? result.diseases : [];
  const byCondition = result?.recommendations_by_disease || {};
  const groups = useMemo(() => {
    const keys = Object.keys(byCondition);
    if (keys.length) return keys.map(name => ({ name, facilities: byCondition[name] || [] }));
    return result && Array.isArray(result.recommendations) ? [{ name: "Experimental facilities", facilities: result.recommendations }] : [];
  }, [byCondition, result]);

  function chooseExample(example, index) {
    setSelectedExample(index);
    setShowCoordinates(false);
    setForm({ text: example.text, location: example.location, lat: "", lon: "", top_k: example.top_k });
    setError("");
    setResult(null);
  }

  function updateField(key, value) {
    if (!CUSTOM_INPUT_ENABLED) return;
    setSelectedExample(-1);
    setForm(current => ({ ...current, [key]: value }));
    setError("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (loading) return;
    if (!CUSTOM_INPUT_ENABLED && !EXAMPLES.some(example =>
      example.text === form.text && example.location === form.location && example.top_k === Number(form.top_k))) {
      setError("Choose one of the provided fictional scenarios to continue.");
      return;
    }
    const problem = validateResearchForm(form);
    if (problem) { setError(problem); return; }
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const response = await fetch("/api/predict", {
        method: "POST", cache: "no-store",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(makeRequestBody(form)),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data?.detail === "string" ? data.detail : "The research backend is unavailable.");
      if (!data || !Array.isArray(data.diseases) || data.research_use_only !== true) {
        throw new Error("Unexpected research response. No result has been displayed.");
      }
      setBackend("ready");
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The experimental request failed.");
      refreshHealth();
    } finally {
      setLoading(false);
    }
  }

  return (
    <main id="main-content" className="app-shell">
      <nav className="topbar" aria-label="Main navigation">
        <a className="brand" href="#home" aria-label="MediPower home">
          <span className="brand-mark"><Glyph name="activity" size={23}/></span>
          <span>Medi<span className="brand-accent">Power</span><small>RESEARCH LAB</small></span>
        </a>
        <div className="nav-links">
          <a href="#workspace">Explore</a>
          <a href="#methodology">Methodology</a>
          <a href="https://github.com/idozii/MediPower" target="_blank" rel="noreferrer">GitHub ↗</a>
        </div>
        <span className="nav-chip"><span className="dot"/> Research demonstration</span>
      </nav>

      <section id="home" className="hero">
        <div className="hero-copy">
          <div className="eyebrow"><span className="eyebrow-line"/> MEDICAL INFORMATION RETRIEVAL · EXPERIMENTAL</div>
          <h1>Explore information.<br/><em>Understand the evidence.</em></h1>
          <p className="hero-lead">An explainable AI research workspace for exploring fictional symptom scenarios, condition information and experimental facility rankings.</p>
          <div className="hero-actions">
            <a className="hero-primary" href="#workspace">Launch research workspace <Glyph name="arrow" size={18}/></a>
            <a className="hero-secondary" href="#methodology">How it works <Glyph name="arrow" size={16}/></a>
          </div>
          <div className="hero-caption"><Glyph name="shield" size={16}/> Fictional examples only · Not diagnosis, triage or medical advice</div>
        </div>
        <aside className="hero-visual" aria-label="Research process overview">
          <div className="visual-header"><span><Glyph name="flask" size={17}/> RESEARCH WORKFLOW</span><span className="visual-live"><span className="dot"/> EXPERIMENTAL</span></div>
          <div className="visual-track">
            <div className="visual-stage"><span>01</span><div><strong>Fictional scenario</strong><small>Choose a controlled example</small></div><Glyph name="layers" size={22}/></div>
            <div className="visual-connector"/>
            <div className="visual-stage"><span>02</span><div><strong>Condition retrieval</strong><small>Uncalibrated ranking signals</small></div><Glyph name="activity" size={22}/></div>
            <div className="visual-connector"/>
            <div className="visual-stage"><span>03</span><div><strong>Facility exploration</strong><small>Unverified demonstration data</small></div><Glyph name="map" size={22}/></div>
          </div>
          <div className="visual-footer"><span>TRANSPARENCY BY DESIGN</span><span>AI + DATA RESEARCH / v1</span></div>
        </aside>
      </section>

      <section className="boundary-banner" aria-label="Important safety disclaimer">
        <Glyph name="info" size={21}/>
        <p><strong>Research prototype — not a healthcare service.</strong> Outputs may be incorrect or incomplete, and facility scores are not clinical quality ratings. Do not enter identifying information or real patient symptoms. For urgent medical concerns, contact local emergency services.</p>
      </section>

      <section id="workspace" className="workspace">
        <div className="section-heading">
          <div><span className="kicker">INTERACTIVE LAB</span><h2>The research workspace</h2><p>Explore a controlled, non-clinical scenario and inspect what the model returns.</p></div>
          <div className="connection" role="status" aria-live="polite">
            <span className={"connection-dot " + backend}/>
            <div><strong>{backend === "ready" ? "Research API connected" : backend === "checking" ? "Checking API" : "Research API unavailable"}</strong><small>{backend === "ready" ? "Service health endpoint responded" : backend === "checking" ? "Checking the backend connection" : "The demo may be temporarily offline"}</small></div>
            <button type="button" onClick={refreshHealth} aria-label="Refresh backend health" title="Refresh connection"><Glyph name="refresh" size={18}/></button>
          </div>
        </div>
        <div className="work-grid">
          <form className="workspace-card input-card" onSubmit={handleSubmit} aria-busy={loading} noValidate>
            <div className="card-heading"><span className="card-icon"><Glyph name="layers"/></span><div><span className="kicker">STEP 01 / INPUT</span><h3>Choose your scenario</h3></div></div>
            <p className="card-description">Start with one of the fictional prompts below. These are demonstration inputs, not patient cases.</p>
            <div className="scenario-list" role="group" aria-label="Fictional demonstration scenarios">
              {EXAMPLES.map((example, index) => (
                <button type="button" key={example.id} className={"scenario-option " + (selectedExample === index ? "selected" : "")}
                  onClick={() => chooseExample(example, index)} aria-pressed={selectedExample === index}>
                  <span className="scenario-icon"><Glyph name={example.icon} size={20}/></span>
                  <span><strong>{example.label}</strong><small>{example.location} · Fictional input</small></span>
                  <span className="scenario-radio" aria-hidden="true"/>
                </button>
              ))}
            </div>
            <label className="field-label" htmlFor="research-symptoms">Scenario text <span>{CUSTOM_INPUT_ENABLED ? "fictional text only" : "predefined example"}</span></label>
            <textarea id="research-symptoms" className="scenario-textarea" name="research-symptoms"
              value={form.text} maxLength={MAX_SYMPTOM_CHARS}
              readOnly={!CUSTOM_INPUT_ENABLED} onChange={event => updateField("text", event.target.value)}
              placeholder="Select a fictional scenario above to begin." aria-describedby="input-privacy-note" />
            <div className="input-meta"><span id="input-privacy-note">{CUSTOM_INPUT_ENABLED ? "Do not submit real health or identifying information." : "Public preview is limited to fictional sample prompts."}</span><span>{form.text.length}/{MAX_SYMPTOM_CHARS}</span></div>
            {CUSTOM_INPUT_ENABLED ? (
              <details className="input-advanced">
                <summary>Advanced fictional location input <Glyph name="chevron" size={17}/></summary>
                <label className="field-label" htmlFor="research-city">Demo city</label>
                <input id="research-city" value={form.location} onChange={event => updateField("location", event.target.value)} placeholder="e.g. Sydney CBD" />
                <button className="advanced-switch" type="button" onClick={() => setShowCoordinates(!showCoordinates)}> {showCoordinates ? "Hide" : "Enter"} coordinate pair</button>
                {showCoordinates ? <div className="coordinate-grid">
                  <label>Latitude<input value={form.lat} onChange={event => updateField("lat", event.target.value)} inputMode="decimal" placeholder="e.g. -33.8688"/></label>
                  <label>Longitude<input value={form.lon} onChange={event => updateField("lon", event.target.value)} inputMode="decimal" placeholder="e.g. 151.2093"/></label>
                </div> : null}
              </details>
            ) : null}
            <div className="submit-area">
              <button className="submit-button" type="submit" disabled={loading || (!CUSTOM_INPUT_ENABLED && selectedExample === -1) || !form.text.trim()}>
                {loading ? "Running research query…" : "Explore results"} <Glyph name="arrow" size={19}/>
              </button>
              <div className="submit-note"><Glyph name="shield" size={16}/> Results are informational ranking hypotheses only</div>
            </div>
            {error ? <p className="form-error" role="alert">{error}</p> : null}
          </form>

          <section className="workspace-card output-card" aria-busy={loading} aria-label="Research retrieval output">
            <div className="card-heading results-heading">
              <span className="card-icon alt"><Glyph name="activity"/></span>
              <div><span className="kicker">STEP 02 / ANALYSIS</span><h3>Research output</h3></div>
              {result ? <EvidenceBadge>{result.retrieval_mode || "retrieval"}</EvidenceBadge> : null}
            </div>
            {!result ? (
              <div className="output-empty" role="status" aria-live="polite">
                <div className={"empty-orbit " + (loading ? "is-loading" : "")}><Glyph name={loading ? "refresh" : "flask"} size={37}/></div>
                <span className="kicker">{loading ? "RETRIEVING" : "AWAITING RESEARCH INPUT"}</span>
                <h4>{loading ? "Analysing fictional scenario…" : "Your exploration starts here."}</h4>
                <p>{loading ? "Comparing query signals against the research catalog. This is not a diagnosis." : "Select a sample scenario and run a research query. Candidate information and experimental facility results will appear here."}</p>
                <div className="empty-features"><span>01 · Query</span><span>02 · Retrieve</span><span>03 · Explain</span></div>
              </div>
            ) : (
              <div className="output-content" aria-live="polite">
                <div className="output-summary">
                  <div><span>Candidate entries</span><strong>{diseases.length}</strong></div>
                  <div><span>Facility rows</span><strong>{groups.reduce((total, g) => total + g.facilities.length, 0)}</strong></div>
                  <div><span>Retriever</span><strong className="summary-mode">{result.retrieval_mode || "Unknown"}</strong></div>
                </div>
                {result.message ? <p className="result-notice">{result.message}</p> : null}
                <div className="result-section"><div className="subsection-heading"><h4>Candidate condition information</h4><span>Uncalibrated</span></div>
                  {diseases.length ? diseases.map((disease, index) => (
                    <article className="condition-card" key={String(disease.disease_id || disease.disease_name || index) + index}>
                      <div className="condition-rank">{String(index + 1).padStart(2, "0")}</div>
                      <div className="condition-body"><h5>{disease.disease_name || disease.Disease || "Unspecified condition"}</h5>
                        <p>{disease.description || disease.summary || "No additional information returned."}</p>
                        <div className="condition-footer"><EvidenceBadge>Retrieval score: {formatRankingScore(disease.score ?? disease.confidence ?? disease.similarity)}</EvidenceBadge></div>
                      </div>
                    </article>
                  )) : <div className="no-results">No suitable information-retrieval matches. This does not rule out a medical condition.</div>}
                </div>
                <div className="result-section"><div className="subsection-heading"><h4>Experimental facility comparisons</h4><span>Unverified proxies</span></div>
                  {groups.length ? groups.map(group => (
                    <section key={group.name} className="facility-group">
                      <p className="facility-group-name">{group.name} <span>{group.facilities.length} rows</span></p>
                      {group.facilities.length ? group.facilities.map((item, index) => <FacilityCard key={String(item.clinic_id || item.hospital_name || index) + index} item={item} index={index}/>)
                        : <p className="no-results">No facility rows returned for this condition.</p>}
                    </section>
                  )) : <p className="no-results">No experimental facility rows returned.</p>}
                </div>
                <p className="output-disclaimer"><Glyph name="info" size={17}/> Scores are not calibrated probabilities, recommendations, quality ratings or estimates of care availability.</p>
              </div>
            )}
          </section>
        </div>
      </section>

      <section id="methodology" className="method-section">
        <div className="method-heading"><span className="kicker">OUR RESEARCH APPROACH</span><h2>Built for explainability,<br/>not clinical decisions.</h2><p>MediPower explores information retrieval and transparent ranking under research-only limitations.</p></div>
        <div className="method-grid">
          <article><span className="method-icon"><Glyph name="layers"/></span><span className="method-number">01 — RETRIEVAL</span><h3>Candidate information</h3><p>Study how ranking algorithms retrieve catalog entries. Similarity and heuristic scores are not disease likelihoods.</p></article>
          <article><span className="method-icon"><Glyph name="map"/></span><span className="method-number">02 — TRANSPARENCY</span><h3>Visible ranking factors</h3><p>Explore straight-line distance and demonstration-only provider proxies. No facility performance is independently verified.</p></article>
          <article><span className="method-icon"><Glyph name="shield"/></span><span className="method-number">03 — BOUNDARIES</span><h3>Research safeguards</h3><p>Sample-only public UX, fail-closed service checks and clear disclosure of unknowns. No real patient information.</p></article>
        </div>
      </section>
      <footer className="site-footer">
        <div className="footer-brand"><span className="brand-mark"><Glyph name="activity" size={18}/></span><span><strong>MediPower</strong><small>AI RESEARCH PROTOTYPE</small></span></div>
        <p>For fictional research exploration only. Not for diagnosis, triage, treatment decisions or real-world facility selection.</p>
        <a href="https://github.com/idozii/MediPower" target="_blank" rel="noreferrer">Source & methodology ↗</a>
      </footer>
    </main>
  );
}
