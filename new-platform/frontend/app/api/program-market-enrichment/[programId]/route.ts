import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../lib/auth";
import { researchBackendBase } from "../../../../lib/research-backend";
import { verifiedMarketEnrichment } from "../../../../lib/verified-market-enrichment";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** Authenticated, read-only market enrichment for the exact permanent program ID. */
export async function GET(req: NextRequest, context: { params: Promise<{ programId: string }> }) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  }
  const { programId } = await context.params;
  if (!/^PDUFA-[0-9]{6,}$/.test(programId)) {
    return NextResponse.json({ error: "Invalid permanent Program ID" }, { status: 422 });
  }
  const range = req.nextUrl.searchParams.get("range") || "1Y";
  if (!new Set(["1M", "3M", "6M", "1Y", "ALL"]).has(range)) {
    return NextResponse.json({ error: "Invalid market-data range" }, { status: 422 });
  }
  const base = researchBackendBase();
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base || !/^https:\/\//.test(base) || !key) {
    return NextResponse.json({ error: "Backend not configured" }, { status: 503 });
  }
  try {
    const response = await fetch(base + "/api/program-market-enrichment/" + encodeURIComponent(programId) + "?range=" + encodeURIComponent(range), {
      headers: { "x-pdufa-internal-key": key },
      cache: "no-store", redirect: "error",
      signal: AbortSignal.timeout(30000),
    });
    // Never return raw backend errors, internal credentials, or a different trial.
    if (!response.ok) {
      return NextResponse.json({ error: "Research market backend unavailable" },
        { status: response.status === 404 ? 404 : 503, headers: { "Cache-Control": "private, no-store" } });
    }
    const data = verifiedMarketEnrichment(await response.json(), programId);
    return NextResponse.json(data, { headers: { "Cache-Control": "private, no-store" } });
  } catch {
    return NextResponse.json({ error: "Alpaca market enrichment unavailable" }, { status: 503 });
  }
}
