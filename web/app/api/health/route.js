import { NextResponse } from "next/server";
import { resolveBackendBaseUrl } from "../../../lib/proxy-contract.mjs";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const headers = { "cache-control": "no-store", "x-content-type-options": "nosniff" };
  let backend;
  try {
    const base = resolveBackendBaseUrl(process.env.HEALTHCARE_AI_API_BASE_URL);
    backend = new URL("health", base.href.endsWith("/") ? base.href : base.href + "/");
  } catch {
    return NextResponse.json({ frontend: "ready", backend: "configuration_error" },
      { status: 503, headers });
  }
  try {
    const response = await fetch(backend, { cache: "no-store", signal: AbortSignal.timeout(3500) });
    if (!response.ok) throw new Error("Backend health endpoint did not succeed");
    const result = await response.json();
    if (result?.status !== "healthy") throw new Error("Backend health response contract invalid");
    return NextResponse.json({ frontend: "ready", backend: "ready" }, { headers });
  } catch {
    return NextResponse.json({ frontend: "ready", backend: "unavailable" },
      { status: 503, headers });
  }
}
