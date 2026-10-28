/** Pure Next.js API boundary validation: research demo, not medical input triage. */
const MAX_TEXT_CHARS = 2000;
const MAX_LOCATION_CHARS = 160;

export function checkPredictionPayload(payload) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return "A JSON object is required.";
  }
  if (typeof payload.text !== "string" || payload.text.trim().length < 3 || payload.text.length > MAX_TEXT_CHARS) {
    return "Fictional symptom text must contain 3–2000 characters.";
  }
  if (!Number.isInteger(payload.top_k ?? 4) || (payload.top_k ?? 4) < 1 || (payload.top_k ?? 4) > 20) {
    return "top_k must be a whole number from 1 to 20.";
  }
  const location = payload.location;
  const hasLocation = typeof location === "string" && location.trim().length > 0;
  if (location !== undefined && location !== null && typeof location !== "string") {
    return "Location must be text.";
  }
  if (hasLocation && location.trim().length > MAX_LOCATION_CHARS) {
    return "Location must contain at most 160 characters.";
  }
  const hasLat = payload.lat !== undefined && payload.lat !== null;
  const hasLon = payload.lon !== undefined && payload.lon !== null;
  if (hasLat !== hasLon && !hasLocation) {
    return "Both latitude and longitude are required.";
  }
  if (!hasLocation && !hasLat) {
    return "A city or both coordinates must be provided.";
  }
  if (hasLat || hasLon) {
    if (typeof payload.lat !== "number" || !Number.isFinite(payload.lat) || payload.lat < -90 || payload.lat > 90) {
      return "Latitude is outside the accepted range.";
    }
    if (typeof payload.lon !== "number" || !Number.isFinite(payload.lon) || payload.lon < -180 || payload.lon > 180) {
      return "Longitude is outside the accepted range.";
    }
  }
  return null;
}

export function resolveBackendBaseUrl(raw) {
  const base = raw || "http://127.0.0.1:8000";
  let url;
  try { url = new URL(base); } catch { throw new Error("Backend URL configuration is invalid."); }
  if (!["http:", "https:"].includes(url.protocol) || url.username || url.password ||
      url.search || url.hash) {
    throw new Error("Backend URL must be an HTTP(S) origin or base path without credentials.");
  }
  return url;
}

export function sanitizedBackendError(data, status) {
  if (status === 422) return "Request failed backend validation. Check fictional symptoms and location.";
  if (status === 400) return "Location could not be resolved. Try a city name or coordinates.";
  if (status >= 500) return "Research backend is temporarily unavailable.";
  return "Unable to retrieve experimental ranking data.";
}
