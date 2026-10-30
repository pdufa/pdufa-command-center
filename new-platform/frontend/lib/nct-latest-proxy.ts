import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "./auth";
import { NCT_PATTERN } from "./nct-live-stream";

const headers = { "Cache-Control": "private, no-store" };
const error = (message: string, status: number) => NextResponse.json({ error: message }, { status, headers });

export async function relayLatestNctRun(req: NextRequest, nct: string) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) return error("Authentication required", 401);
  if (!NCT_PATTERN.test(nct)) return error("Invalid trial identifier", 422);
  const base = process.env.PDUFA_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base?.startsWith("https://") || !key) return error("Processing backend is not configured", 503);
  try {
    const response = await fetch(base + "/api/nct-stream/" + encodeURIComponent(nct) + "/runs/latest", {
      cache: "no-store", headers: { Accept: "application/json", "X-Pdufa-Internal-Key": key },
      signal: AbortSignal.any([req.signal, AbortSignal.timeout(25000)]),
    });
    if (!response.ok) return error("Saved processing run is unavailable", [404, 409, 422].includes(response.status) ? response.status : 503);
    if (!(response.headers.get("content-type") || "").toLowerCase().startsWith("application/json")) return error("Processing backend returned an unexpected response", 502);
    return NextResponse.json(await response.json(), { headers });
  } catch { return error("Processing backend is unavailable", 503); }
}
