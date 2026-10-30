import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Fail closed: do not fabricate historical FDA decisions or conflate Phase 3
// endpoint success with application-level approval. Connect an audited,
// provenance-backed catalog service before returning verified trial records.
export async function GET(req: NextRequest) {
  const period = req.nextUrl.searchParams.get("period");
  if (period !== "CURRENT" && period !== "PREVIOUS") return NextResponse.json({ error: "Invalid period" }, { status: 400 });
  return NextResponse.json({ period, trials: [], source_status: "NOT_CONNECTED", last_updated: null }, { headers: { "Cache-Control": "no-store" } });
}
