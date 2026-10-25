import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../lib/auth";
import { fetchReadOnlyWithWarmRetry } from "../../../lib/read-only-warm-retry";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  }
  const exactId = req.nextUrl.searchParams.get("exact_id");
  if (!exactId || exactId.length > 512 || !/^(TRIAL\||REG\||PDUFA\|)/.test(exactId)) {
    return NextResponse.json({ error: "Valid exact trial identity required" }, { status: 422 });
  }
  const base = process.env.PDUFA_SCIENTIFIC_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base?.startsWith("https://") || !key) {
    return NextResponse.json({ error: "Backend is not configured" }, { status: 503 });
  }
  try {
    const response = await fetchReadOnlyWithWarmRetry(
      base + "/api/scientific-assessment?exact_id=" + encodeURIComponent(exactId),
      { headers: { "x-pdufa-internal-key": key }, cache: "no-store", signal: AbortSignal.timeout(45000) }
    );
    const data = await response.json();
    if (!response.ok) return NextResponse.json({ error: "Scientific assessment unavailable" }, { status: response.status });
    return NextResponse.json(data, { headers: { "Cache-Control": "private, no-store" } });
  } catch {
    return NextResponse.json({ error: "Scientific assessment could not be loaded" }, { status: 503 });
  }
}
