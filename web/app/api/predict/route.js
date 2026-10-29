import { NextResponse } from "next/server";
import { isAllowedDemoPayload } from "../../../lib/demo-presets.mjs";
import { checkPredictionPayload, resolveBackendBaseUrl, sanitizedBackendError } from "../../../lib/proxy-contract.mjs";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const MAX_BODY_BYTES = 16384;
const REQUEST_TIMEOUT_MS = 15000;
const HEADERS = { "cache-control": "no-store", "x-content-type-options": "nosniff" };

function json(data, status = 200) {
  return NextResponse.json(data, { status, headers: HEADERS });
}

export async function POST(request) {
  if (!request.headers.get("content-type")?.toLowerCase().includes("application/json")) {
    return json({ detail: "Content-Type must be application/json." }, 415);
  }
  const declaredLength = Number(request.headers.get("content-length") || "0");
  if (Number.isFinite(declaredLength) && declaredLength > MAX_BODY_BYTES) {
    return json({ detail: "Input payload is too large for this research demo." }, 413);
  }

  let payload;
  try {
    const raw = await request.text();
    if (new TextEncoder().encode(raw).byteLength > MAX_BODY_BYTES) {
      return json({ detail: "Input payload is too large for this research demo." }, 413);
    }
    payload = JSON.parse(raw);
  } catch {
    return json({ detail: "Invalid JSON request." }, 400);
  }
  const validationError = checkPredictionPayload(payload);
  if (validationError) return json({ detail: validationError }, 422);
  if (process.env.MEDIPOWER_PRESET_ONLY === "1" && !isAllowedDemoPayload(payload)) {
    return json({ detail: "Choose one of the provided fictional scenarios for this research preview." }, 403);
  }

  let backendUrl;
  try {
    const configured = resolveBackendBaseUrl(process.env.HEALTHCARE_AI_API_BASE_URL);
    backendUrl = new URL("predict", configured.href.endsWith("/") ? configured.href : configured.href + "/");
  } catch {
    return json({ detail: "Research backend configuration is unavailable." }, 503);
  }

  let response;
  try {
    response = await fetch(backendUrl, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch (error) {
    const timedOut = error?.name === "TimeoutError" || error?.name === "AbortError";
    return json({ detail: timedOut ? "Research backend timed out; try again later." :
      "Research backend could not be reached. Verify service status." }, timedOut ? 504 : 502);
  }

  // Reject non-JSON responses instead of reflecting HTML, tracebacks or other
  // unintended backend content into a public page.
  if (!response.headers.get("content-type")?.toLowerCase().includes("application/json")) {
    return json({ detail: "Research backend returned an unexpected response format." }, 502);
  }
  let data;
  try { data = await response.json(); }
  catch { return json({ detail: "Research backend returned invalid JSON." }, 502); }
  if (!response.ok) {
    return json({ detail: sanitizedBackendError(data, response.status) },
      response.status >= 400 && response.status < 500 ? response.status : 502);
  }
  if (!data || typeof data !== "object" || !Array.isArray(data.diseases) ||
      data.research_use_only !== true) {
    return json({ detail: "Research backend response contract is invalid." }, 502);
  }
  return json(data);
}
