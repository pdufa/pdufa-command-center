import { NextRequest, NextResponse } from "next/server";
import focus from "../../../../data/p3PostDataActive.json";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 30;
const privateHeaders = { "Cache-Control": "private, no-store" };
const NCT = /^NCT\d{8}$/;
const UUID = /^[a-f0-9]{8}-[a-f0-9]{4}-[1-8][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i;

const json = (payload: unknown, status = 200) =>
  NextResponse.json(payload, { status, headers: privateHeaders });

function authorized(req: NextRequest) {
  return authConfigured() && hasSession(req.cookies.get(COOKIE_NAME)?.value);
}
function knownNct(nct: unknown): nct is string {
  return typeof nct === "string" && NCT.test(nct) && focus.records.some(r => r.nct === nct);
}
function baseAndKey() {
  const base = process.env.PDUFA_API_BASE_URL?.trim().replace(/\/$/, "");
  const key = process.env.PDUFA_INTERNAL_API_KEY?.trim();
  return base?.startsWith("https://") && key ? { base, key } : null;
}
async function upstream(path: string, method: "GET" | "POST", body?: object) {
  const settings = baseAndKey();
  if (!settings) return json({ error: "Persistent medical stage backend not configured" }, 503);
  try {
    const response = await fetch(settings.base + path, {
      method, cache: "no-store", signal: AbortSignal.timeout(24000),
      headers: {
        "X-Pdufa-Internal-Key": settings.key,
        Accept: "application/json",
        ...(body ? { "Content-Type": "application/json" } : {})
      },
      ...(body ? { body: JSON.stringify(body) } : {})
    });
    if (!response.headers.get("content-type")?.toLowerCase().startsWith("application/json"))
      return json({ error: "Medical stage service returned unexpected data" }, 503);
    const payload: unknown = await response.json();
    if (!response.ok) {
      // FastAPI returns a different 404 for an unknown route than for an existing
      // research endpoint with no saved run. Do not disguise a missing backend
      // deployment as "no previous run" when the operator opens the page.
      const missingRun = response.status === 404 && payload !== null &&
        typeof payload === "object" && "detail" in payload &&
        (payload as { detail?: unknown }).detail === "Saved medical research run not found";
      const detail = payload !== null && typeof payload === "object" && "detail" in payload
        ? (payload as { detail?: unknown }).detail : null;
      const missingDatabase = response.status === 503 && typeof detail === "string" &&
        detail.startsWith("Persistent PostgreSQL is not connected");
      const databaseUnavailable = response.status === 503 && detail !== null &&
        typeof detail === "object" && "error" in detail &&
        (detail as { error?: unknown }).error === "Persistent database temporarily unavailable; no data was reset";
      return json({ error: missingRun ? "No saved medical research run" :
          missingDatabase ? "Preview backend is live, but its PostgreSQL database connection is not configured." :
          databaseUnavailable ? "Preview PostgreSQL is temporarily unavailable; saved research has not been reset." :
          response.status === 404 ? "Persistent medical stage backend route is not deployed" :
          response.status === 422 ? "Run identity invalid" :
          response.status === 401 ? "Backend authorization unavailable" :
          "Medical stage backend unavailable" },
        missingRun ? 404 : response.status === 422 ? 422 : 503);
    }
    return json(payload);
  } catch {
    return json({ error: "Persistent medical stage service unavailable; no job started" }, 503);
  }
}

/** Read-only; opening the page only retrieves an existing saved run. */
export async function GET(req: NextRequest) {
  if (!authorized(req)) return json({ error: "Sign in required" }, 401);
  const nct = req.nextUrl.searchParams.get("nct");
  const run = req.nextUrl.searchParams.get("run");
  if (!knownNct(nct) || (run !== null && !UUID.test(run)))
    return json({ error: "Exact FOCUS trial and valid run identifier required" }, 422);
  return upstream("/api/medical-continuous/" + nct + "/runs/" + (run || "latest"), "GET");
}

export async function POST(req: NextRequest) {
  if (!authorized(req)) return json({ error: "Sign in required" }, 401);
  if (req.headers.get("origin") !== req.nextUrl.origin)
    return json({ error: "Same-origin operator action required" }, 403);
  if (!req.headers.get("content-type")?.toLowerCase().startsWith("application/json"))
    return json({ error: "JSON request required" }, 415);
  if (Number(req.headers.get("content-length") || 0) > 1500)
    return json({ error: "Request too large" }, 413);
  const payload: unknown = await req.json().catch(() => null);
  if (!payload || typeof payload !== "object" || Array.isArray(payload))
    return json({ error: "Invalid request" }, 422);
  const { action, nct, run, requestKey } = payload as Record<string, unknown>;
  if (!knownNct(nct)) return json({ error: "Exact FOCUS trial required" }, 422);
  if (action === "start" && typeof requestKey === "string" && UUID.test(requestKey))
    return upstream("/api/medical-continuous/" + nct + "/runs", "POST", { request_key: requestKey });
  if ((action === "stop" || action === "resume") && typeof run === "string" && UUID.test(run))
    return upstream("/api/medical-continuous/" + nct + "/runs/" + run + "/" + action, "POST");
  return json({ error: "Invalid medical stage operator action" }, 422);
}
