/** Client-only research demo input contract. No patient data or diagnosis output. */
export const MAX_SYMPTOM_CHARS = 2000;
export const MAX_LOCATION_CHARS = 160;
export const MAX_TOP_K = 20;

function field(value) {
  return typeof value === "string" ? value.trim() : "";
}

function coordinate(value, min, max) {
  const text = field(value);
  if (!text) return { entered: false, valid: true, value: null };
  const number = Number(text);
  return { entered: true, valid: Number.isFinite(number) && number >= min && number <= max, value: number };
}

export function validateResearchForm(form) {
  const text = field(form.text);
  const location = field(form.location);
  const latitude = coordinate(form.lat, -90, 90);
  const longitude = coordinate(form.lon, -180, 180);
  if (text.length < 3 || text.length > MAX_SYMPTOM_CHARS) {
    return "Enter 3–2000 characters of fictional symptoms.";
  }
  if (location.length > MAX_LOCATION_CHARS) {
    return "Location text must be no longer than 160 characters.";
  }
  if (!latitude.valid || !longitude.valid) {
    return "Enter valid latitude (−90 to 90) and longitude (−180 to 180).";
  }
  if (!location && (latitude.entered !== longitude.entered || !latitude.entered)) {
    return "Enter a city or provide both latitude and longitude.";
  }
  const topK = Number(form.top_k);
  if (!Number.isInteger(topK) || topK < 1 || topK > MAX_TOP_K) {
    return "Top K must be an integer from 1 to 20.";
  }
  return null;
}

export function makeRequestBody(form) {
  const problem = validateResearchForm(form);
  if (problem) throw new Error(problem);
  const payload = { text: field(form.text), top_k: Number(form.top_k) };
  const location = field(form.location);
  if (location) {
    payload.location = location;
  } else {
    payload.lat = Number(form.lat);
    payload.lon = Number(form.lon);
  }
  return payload;
}

export function formatRankingScore(value) {
  if (value === null || value === undefined || value === "") return "Not available";
  const score = Number(value);
  if (!Number.isFinite(score) || score < 0 || score > 1) return "Not available";
  return score.toFixed(3) + " / 1";
}

export function formatFacilityMetric(value, digits = 2) {
  if (value === null || value === undefined || value === "") return "Not available";
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : "Not available";
}
