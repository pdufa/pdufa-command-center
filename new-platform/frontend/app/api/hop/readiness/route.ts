import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../lib/auth";
import { fetchReadOnlyWithWarmRetry } from "../../../../lib/read-only-warm-retry";
import { normalizeHopReadiness } from "../../../../lib/hop-readiness";
import { hopBackendBase } from "../../../../lib/hop-backend";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;
const headers = { "Cache-Control": "private, no-store" };
type SourceFailure = "SOURCE_UNREACHABLE" | "SOURCE_AUTHENTICATION_FAILED" | "SOURCE_ROUTE_MISSING" | "SOURCE_HTTP_ERROR" | "SOURCE_INVALID_RESPONSE";
function unavailable(reason: SourceFailure) {
  return NextResponse.json({
    error: "HOP source audit could not be verified; historical counts withheld", reason,
  }, { status: 503, headers });
}

export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401, headers });
  }
  const base = hopBackendBase();
  const secret = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base || !secret) {
    return NextResponse.json({ error: "HOP evidence source is not configured" }, { status: 503, headers });
  }
  let upstream: Response;
  try {
    upstream = await fetchReadOnlyWithWarmRetry(base + "/api/hop/readiness", {
      headers: { "x-pdufa-internal-key": secret },
      cache: "no-store", redirect: "error", signal: AbortSignal.timeout(45000),
    });
  } catch {
    return unavailable("SOURCE_UNREACHABLE");
  }
  if (!upstream.ok) {
    return unavailable(upstream.status === 401 || upstream.status === 403
      ? "SOURCE_AUTHENTICATION_FAILED" : upstream.status === 404
      ? "SOURCE_ROUTE_MISSING" : "SOURCE_HTTP_ERROR");
  }
  try {
    const parsed = normalizeHopReadiness(await upstream.json());
    return NextResponse.json(parsed, { headers });
  } catch {
    return unavailable("SOURCE_INVALID_RESPONSE");
  }
}
