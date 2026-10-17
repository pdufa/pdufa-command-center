import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ programId: string }> }
) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  }
  const { programId } = await context.params;
  if (!/^PDUFA-[0-9]{6,}$/.test(programId)) {
    return NextResponse.json({ error: "Invalid permanent Program ID" }, { status: 422 });
  }
  const allowedRanges = new Set(["1M","3M","6M","1Y","ALL"]);
  const range = req.nextUrl.searchParams.get("range") || "1Y";
  if(!allowedRanges.has(range))return NextResponse.json({error:"Invalid chart range"},{status:422});
  const base = process.env.PDUFA_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base || !/^https:\/\//.test(base) || !key) {
    return NextResponse.json({ error: "Backend not configured" }, { status: 503 });
  }
  try {
    const result = await fetch(base + "/api/alpaca-chart/" + encodeURIComponent(programId) + "?range=" + encodeURIComponent(range), {
      headers: { "x-pdufa-internal-key": key },
      cache: "no-store",
      signal: AbortSignal.timeout(30000)
    });
    const data = await result.json().catch(() => ({}));
    return NextResponse.json(data, {
      status: result.status,
      headers: { "Cache-Control": "private, no-store" }
    });
  } catch {
    return NextResponse.json({ error: "WT indicator research unavailable" }, { status: 503 });
  }
}
