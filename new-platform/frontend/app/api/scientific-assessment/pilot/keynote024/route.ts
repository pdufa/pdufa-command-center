import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../../lib/auth";
import { fetchReadOnlyWithWarmRetry } from "../../../../../lib/read-only-warm-retry";
import { validTrialSciencePilot } from "../../../../../lib/trial-science-pilot";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const PRIVATE = { "Cache-Control": "private, no-store" };

/**
 * An explicitly requested, historical pilot only. No arbitrary trial ID
 * or URL is accepted here; no external-search or database-write endpoint
 * is reachable through this route.
 */
export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, {
      status: 401, headers: PRIVATE,
    });
  }
  const base = process.env.PDUFA_SCIENTIFIC_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base?.startsWith("https://") || !key) {
    return NextResponse.json({ error: "Scientific review service not configured" }, {
      status: 503, headers: PRIVATE,
    });
  }

  try {
    const response = await fetchReadOnlyWithWarmRetry(
      base + "/api/scientific-assessment/pilot/keynote024",
      {
        headers: { "x-pdufa-internal-key": key },
        cache: "no-store",
        signal: AbortSignal.timeout(45000),
      },
    );
    if (!response.ok) {
      return NextResponse.json({
        error: response.status === 404
          ? "Historical pilot is not yet available on the review service"
          : "Historical pilot evidence is unavailable",
      }, {
        status: response.status === 404 ? 404 : 503, headers: PRIVATE,
      });
    }

    const data: unknown = await response.json();
    if (!validTrialSciencePilot(data)) {
      return NextResponse.json({
        error: "Historical pilot evidence did not pass identity and safety validation",
      }, { status: 503, headers: PRIVATE });
    }
    return NextResponse.json(data, { headers: PRIVATE });
  } catch {
    return NextResponse.json({ error: "Historical pilot could not be loaded" }, {
      status: 503, headers: PRIVATE,
    });
  }
}
