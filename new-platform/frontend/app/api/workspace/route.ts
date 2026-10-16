import { NextRequest, NextResponse } from "next/server";
import snapshot from "../../../data/stageSnapshot.json";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

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
    const response = await fetch(base + "/api/workspace", {
      headers: { "x-pdufa-internal-key": key },
      cache: "no-store",
      signal: AbortSignal.timeout(30000)
    });
    if (!response.ok) throw new Error("Upstream source unavailable");
    const data = await response.json();
    return NextResponse.json(data, { headers: { "Cache-Control": "private, no-store" } });
  } catch {
    // Explicitly label the last bundled snapshot rather than falsely showing it as live.
    return NextResponse.json({
      ...snapshot,
      mode: "BUNDLED_FALLBACK_SOURCE_SNAPSHOT",
      sourceHealth: {
        state: "STALE", issues: ["Unable to connect to the read-only published-source backend. Showing bundled historical snapshot."],
        clinicalRows: 0, regulatoryRows: snapshot.pipeline.length, publishedScan: null
      },
    }, { headers: { "Cache-Control": "private, no-store" } });
  }
}
