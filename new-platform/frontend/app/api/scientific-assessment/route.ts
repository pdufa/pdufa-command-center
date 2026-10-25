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
    if (!response.ok) return NextResponse.json({ error: "Scientific assessment unavailable" }, { status: response.status });
    if (response.headers?.get("x-pdufa-scientific-api-contract") !== "science-integrated-v1") {
      // Prevent the normal assessment UI from bypassing the connection
      // diagnostic and treating an older isolated Render release as current.
      return NextResponse.json({ error: "Integrated scientific backend release not deployed" }, {
        status: 503, headers: { "Cache-Control": "private, no-store" },
      });
    }
    const data: unknown = await response.json();
    return NextResponse.json(data, { headers: { "Cache-Control": "private, no-store" } });
  } catch {
    return NextResponse.json({ error: "Scientific assessment could not be loaded" }, { status: 503 });
  }
}
