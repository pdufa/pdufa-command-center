import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  }
  const base = process.env.PDUFA_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base || !/^https:\/\//.test(base) || !key) {
    return NextResponse.json({ error: "Backend is not configured" }, { status: 503 });
  }
  try {
    // A freshly waking backend may briefly return 502/503. Retry once,
    // server-side, without triggering a browser polling loop.
    let response = await fetch(base + "/api/workspace/summary", {
      headers: { "x-pdufa-internal-key": key },
      cache: "no-store",
      signal: AbortSignal.timeout(20000),
    });
    if (response.status === 502 || response.status === 503) {
      await new Promise(resolve => setTimeout(resolve, 1500));
      response = await fetch(base + "/api/workspace/summary", {
        headers: { "x-pdufa-internal-key": key },
        cache: "no-store",
        signal: AbortSignal.timeout(20000),
      });
    }
    if (!response.ok) {
      return NextResponse.json({ error: "Verified summary unavailable; backend HTTP " + response.status }, { status: 503 });
    }
    const data: unknown = await response.json();
    if (!data || typeof data !== "object") throw new Error("Invalid summary");
    const summary = data as Record<string, unknown>;
    if (!Number.isSafeInteger(summary.pipeline) || (summary.pipeline as number) < 0) {
      throw new Error("Invalid Pipeline source count");
    }
    // The published legacy backend can still expose historical stage counters.
    // Do not transmit, gate on, or treat those as active site associations.
    return NextResponse.json({
      pipeline: summary.pipeline,
      asOf: typeof summary.asOf === "string" ? summary.asOf : null,
      sourceState: typeof summary.sourceState === "string" ? summary.sourceState : null
    }, { headers: { "Cache-Control": "private, no-store" } });
  } catch {
    return NextResponse.json({ error: "Verified summary unavailable" }, { status: 503 });
  }
}
