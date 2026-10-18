import { NextRequest, NextResponse } from "next/server";
import { gzipSync } from "node:zlib";
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
    if (!response.ok) {
      const reason = response.status === 503
        ? "Backend returned 503 (database unavailable, program registry unavailable, or source processing failed)"
        : response.status === 401 || response.status === 403
        ? "Backend rejected internal API authentication"
        : "Backend returned HTTP " + response.status;
      return NextResponse.json({ error: reason, sourceHealth: { state: "UNAVAILABLE" } },
        { status: 503, headers: { "Cache-Control": "private, no-store" } });
    }
    const data = await response.json();
    // Accept the live Render backend's original parity field during the
    // backend/frontend branch transition. Normalize before client validation.
    if (data.sourceHealth?.streamlitPipelineParity && !data.sourceHealth.pipelineSourceParity) {
      data.sourceHealth.pipelineSourceParity = data.sourceHealth.streamlitPipelineParity;
    }
    if (!Array.isArray(data.pipeline) ||
        !data.sourceHealth?.pipelineSourceParity ||
        data.pipeline.length !== data.sourceHealth.pipelineSourceParity.exactPrograms) {
      throw new Error("PIPELINE count or parity metadata failed validation");
    }
    // The full published-source 9k+ trial universe is too large for
    // Vercel's uncompressed Serverless Function response limit. Send
    // authenticated gzip bytes; browser fetch().json() decompresses them.
    const output = gzipSync(Buffer.from(JSON.stringify(data)), { level: 6 });
    return new NextResponse(new Uint8Array(output), {
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Content-Encoding": "gzip",
        "Cache-Control": "private, no-store",
        "Vary": "Accept-Encoding",
      }
    });
  } catch (cause) {
    // Do not silently substitute an obsolete tiny bundle. Old source
    // snapshots made the Pipeline total look wrong even after a backend fix.
    return NextResponse.json({
      error: cause instanceof Error && cause.message === "PIPELINE count or parity metadata failed validation"
        ? "PIPELINE data and source totals disagree"
        : cause instanceof Error && cause.name === "TimeoutError"
        ? "Backend request timed out after 30 seconds"
        : "Backend unreachable or invalid workspace response",
      sourceHealth: { state: "UNAVAILABLE" }
    }, { status: 503, headers: { "Cache-Control": "private, no-store" } });
  }
}
