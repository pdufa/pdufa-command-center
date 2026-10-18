import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  }
  const base = process.env.PDUFA_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base?.startsWith("https://") || !key) return NextResponse.json({ error: "Backend is not configured" }, { status: 503 });
  try {
    const response = await fetch(base + "/api/pipeline-full-records/export-link", {
      headers: { "x-pdufa-internal-key": key }, cache: "no-store", signal: AbortSignal.timeout(30000),
    });
    if (!response.ok) return NextResponse.json({ error: "Full trial download is not complete yet" }, { status: response.status });
    const data = await response.json();
    if (typeof data.path !== "string" || !/^\/downloads\/pipeline-all-fields\/v1\.\d+\.[a-f0-9]{64}$/.test(data.path)) {
      throw new Error("Invalid export path");
    }
    // The browser downloads directly from the backend using a short-lived,
    // export-only signature. The internal API key never reaches the browser.
    return NextResponse.redirect(base + data.path, { status: 307, headers: { "Cache-Control": "private, no-store", "Referrer-Policy": "no-referrer" } });
  } catch {
    return NextResponse.json({ error: "Unable to prepare the complete trial export" }, { status: 503 });
  }
}
