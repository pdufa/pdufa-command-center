import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../lib/auth";
import { fetchReadOnlyWithWarmRetry } from "../../../../lib/read-only-warm-retry";
import { normalizeHopReadiness } from "../../../../lib/hop-readiness";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 35;
const headers = { "Cache-Control": "private, no-store" };

export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401, headers });
  }
  const base = process.env.PDUFA_API_BASE_URL?.replace(/\/$/, "");
  const secret = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base?.startsWith("https://") || !secret) {
    return NextResponse.json({ error: "HOP evidence source is not configured" }, { status: 503, headers });
  }
  try {
    const upstream = await fetchReadOnlyWithWarmRetry(base + "/api/hop/readiness", {
      headers: { "x-pdufa-internal-key": secret },
      cache: "no-store", signal: AbortSignal.timeout(27000),
    });
    if (!upstream.ok) throw new Error("HOP evidence source unavailable");
    const parsed = normalizeHopReadiness(await upstream.json());
    return NextResponse.json(parsed, { headers });
  } catch {
    return NextResponse.json({ error: "HOP source audit could not be verified; historical counts withheld" }, {
      status: 503, headers,
    });
  }
}
