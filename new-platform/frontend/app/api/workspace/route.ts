import { NextRequest, NextResponse } from "next/server";
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
    if (!Array.isArray(data.pipeline) ||
        !data.sourceHealth?.streamlitPipelineParity ||
        data.pipeline.length !== data.sourceHealth.streamlitPipelineParity.exactPrograms) {
      throw new Error("Streamlit Pipeline parity not verified by backend");
    }
    return NextResponse.json(data, { headers: { "Cache-Control": "private, no-store" } });
  } catch {
    // Do not silently substitute an obsolete tiny bundle. Old source
    // snapshots made the Pipeline total look wrong even after a backend fix.
    return NextResponse.json({
      error: "Pipeline temporarily unavailable; current Streamlit-parity count could not be verified",
      sourceHealth: { state: "UNAVAILABLE" }
    }, { status: 503, headers: { "Cache-Control": "private, no-store" } });
  }
}
