import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  }
  const ids = req.nextUrl.searchParams.get("ids") || "";
  if (ids && (ids.split(",").length > 50 || !/^NCT\d{8}(,NCT\d{8})*$/.test(ids))) {
    return NextResponse.json({ error: "Invalid trial IDs" }, { status: 422 });
  }
  const base = process.env.PDUFA_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base?.startsWith("https://") || !key) return NextResponse.json({ error: "Backend is not configured" }, { status: 503 });
  try {
    const response = await fetch(base + "/api/pipeline-full-records/rows?ids=" + encodeURIComponent(ids), {
      headers: { "x-pdufa-internal-key": key }, cache: "no-store", signal: AbortSignal.timeout(30000),
    });
    return NextResponse.json(await response.json(), { status: response.status, headers: { "Cache-Control": "private, no-store" } });
  } catch {
    return NextResponse.json({ error: "Saved trial summaries are temporarily unavailable" }, { status: 503 });
  }
}
