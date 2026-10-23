import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../lib/auth";
import { buildSalesIndex, companySales, salesTicker, SALES_SOURCE_URL } from "../../../lib/approved-drug-sales";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 30;
const headers = { "Cache-Control": "private, no-store" };

export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) return NextResponse.json({ error: "Authentication required" }, { status: 401, headers });
  const ticker = salesTicker(req.nextUrl.searchParams.get("ticker") || "");
  if (!ticker) return NextResponse.json({ error: "A valid company ticker is required" }, { status: 400, headers });
  try {
    const response = await fetch(SALES_SOURCE_URL, { next: { revalidate: 300 }, signal: AbortSignal.timeout(20000) });
    if (!response.ok) throw new Error("Sales ledger unavailable");
    const csv = await response.text();
    if (csv.length > 2_000_000) throw new Error("Sales ledger exceeds limit");
    return NextResponse.json(companySales(buildSalesIndex(csv, new Date().toISOString()), ticker), { headers });
  } catch {
    return NextResponse.json({ error: "Saved sales disclosures could not be loaded. Try again." }, { status: 503, headers });
  }
}
