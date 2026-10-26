import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../lib/auth";
import { fetchReadOnlyWithWarmRetry } from "../../../../lib/read-only-warm-retry";
import { validateScientificPairProgress } from "../../../../lib/scientific-review-progress";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const PRIVATE = { "Cache-Control": "private, no-store" };
const NCT = "NCT02142738";

/** Separate preview-only identity gate; no reviewer credential or reviewer records. */
export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, {
      status: 401, headers: PRIVATE,
    });
  }
  if (req.nextUrl.searchParams.get("nct_id") !== NCT
      || [...req.nextUrl.searchParams.keys()].some(key => key !== "nct_id")) {
    return NextResponse.json({ error: "Exact historical pilot required" }, {
      status: 422, headers: PRIVATE,
    });
  }
  const base = process.env.PDUFA_SCIENTIFIC_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_SCIENTIFIC_PREVIEW_READ_KEY;
  if (!base || !/^https:\/\/[^/]+$/.test(base) || !key) {
    return NextResponse.json({ error: "Isolated scientific reviewer preflight unavailable" }, {
      status: 503, headers: PRIVATE,
    });
  }
  try {
    const response = await fetchReadOnlyWithWarmRetry(
      base + "/api/scientific-assessment/pilot/reviewer-progress/" + NCT,
      {
        headers: { "x-pdufa-internal-key": key },
        cache: "no-store",
        signal: AbortSignal.timeout(20000),
      },
    );
    if (!response.ok
        || response.headers?.get("x-pdufa-scientific-api-contract")
            !== "science-review-pair-progress-v1") {
      return NextResponse.json({ error: "Protected reviewer preflight contract unavailable" }, {
        status: 503, headers: PRIVATE,
      });
    }
    const report = validateScientificPairProgress(await response.json());
    // This strict projection discards any untrusted backend extras, including PII.
    return NextResponse.json(report, { headers: PRIVATE });
  } catch {
    return NextResponse.json({ error: "Scientific reviewer preflight could not be verified" }, {
      status: 503, headers: PRIVATE,
    });
  }
}
