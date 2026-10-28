import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../lib/auth";
import { fetchReadOnlyWithWarmRetry } from "../../../../lib/read-only-warm-retry";
import { computePublishedScienceCoverage } from "../../../../lib/scientific-cohort-coverage";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 120;

const HEADERS = { "Cache-Control": "private, no-store" };

/** Explicit, session-gated read-only published membership audit.
 *
 * Reads existing non-scientific API endpoints using the existing restricted
 * internal key and returns only aggregated list-to-exact-NCT coverage.
 * Never writes to Neon/Render, imports trials, scores science or adjusts
 * GEM/FS/FA/WT selections.
 */
export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, {
      status: 401, headers: HEADERS,
    });
  }
  const base = process.env.PDUFA_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base?.startsWith("https://") || !key) {
    return NextResponse.json({ error: "Read-only workspace source not configured" }, {
      status: 503, headers: HEADERS,
    });
  }
  try {
    const requests = ["/api/workspace", "/api/program-watch-trade"].map(path =>
      fetchReadOnlyWithWarmRetry(base + path, {
        method: "GET",
        headers: { "x-pdufa-internal-key": key },
        cache: "no-store",
        signal: AbortSignal.timeout(45000),
      }),
    );
    const [workspaceResponse, wtResponse] = await Promise.all(requests);
    if (!workspaceResponse.ok || !wtResponse.ok) {
      return NextResponse.json({ error: "Verified published GEM and WT sources unavailable" }, {
        status: 503, headers: HEADERS,
      });
    }
    const workspace: unknown = await workspaceResponse.json();
    const wt: unknown = await wtResponse.json();
    const coverage = computePublishedScienceCoverage(workspace, wt);
    return NextResponse.json(coverage, { status: 200, headers: HEADERS });
  } catch {
    // No fallback to cached or reconstructed memberships. Fail closed.
    return NextResponse.json({ error: "Published exact-trial coverage could not be verified" }, {
      status: 503, headers: HEADERS,
    });
  }
}
