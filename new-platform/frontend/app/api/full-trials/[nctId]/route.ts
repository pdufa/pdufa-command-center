import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest, context: { params: Promise<{ nctId: string }> }) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  }
  const { nctId } = await context.params;
  if (!/^NCT\d{8}$/.test(nctId)) return NextResponse.json({ error: "Invalid NCT ID" }, { status: 422 });
  const base = process.env.PDUFA_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base?.startsWith("https://") || !key) return NextResponse.json({ error: "Backend is not configured" }, { status: 503 });
  try {
    const response = await fetch(base + "/api/pipeline-full-records/" + nctId + "/view-link", {
      headers: { "x-pdufa-internal-key": key }, cache: "no-store", signal: AbortSignal.timeout(30000),
    });
    if (!response.ok) return NextResponse.json({ error: "Saved full record is not available yet" }, { status: response.status });
    const value = await response.json();
    if (typeof value.path !== "string" || !new RegExp("^/downloads/pipeline-trial/" + nctId + "/v1\\.\\d+\\.[a-f0-9]{64}$").test(value.path)) {
      throw new Error("Invalid record link");
    }
    return NextResponse.json({ url: base + value.path }, { headers: { "Cache-Control": "private, no-store" } });
  } catch {
    return NextResponse.json({ error: "Full trial details are temporarily unavailable" }, { status: 503 });
  }
}
