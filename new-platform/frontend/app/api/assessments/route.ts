import { NextRequest, NextResponse } from "next/server";
import { gzipSync } from "node:zlib";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../lib/auth";
import { fetchReadOnlyWithWarmRetry } from "../../../lib/read-only-warm-retry";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  }
  const identity = req.nextUrl.searchParams.get("identity");
  if (identity !== null && (!identity || identity.length > 512)) {
    return NextResponse.json({ error: "An exact candidate identity is required" }, { status: 422 });
  }
  const base = process.env.PDUFA_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base?.startsWith("https://") || !key) return NextResponse.json({ error: "Backend is not configured" }, { status: 503 });
  try {
    const response = await fetchReadOnlyWithWarmRetry(base + "/api/candidate-assessments" + (identity ? "/detail?identity=" + encodeURIComponent(identity) : ""), {
      headers: { "x-pdufa-internal-key": key }, cache: "no-store", signal: AbortSignal.timeout(45000),
    });
    const data = await response.json();
    if (!response.ok) return NextResponse.json({ error: typeof data.detail === "string" ? data.detail : "Candidate scores are temporarily unavailable" }, { status: response.status });
    return new NextResponse(new Uint8Array(gzipSync(Buffer.from(JSON.stringify(data)))), {
      headers: { "Content-Type": "application/json", "Content-Encoding": "gzip", "Cache-Control": "private, no-store", "Vary": "Accept-Encoding" },
    });
  } catch {
    return NextResponse.json({ error: "Candidate scores could not be loaded. Retry shortly." }, { status: 503 });
  }
}
