import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../lib/auth";
import { buildDesignationIndex, applyReviewedDesignationLinks } from "../../../lib/trial-designations";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 45;
const SOURCE = "https://raw.githubusercontent.com/pdufa/pdufa-command-center/main/data/";

export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  }
  const files = await Promise.allSettled(["prediction_engine_designations.csv", "pdufa_candidates.csv", "fda_designation_nct_evidence.csv"].map(async name => {
    const response = await fetch(SOURCE + name, { next: { revalidate: 300 }, signal: AbortSignal.timeout(20000) });
    if (!response.ok) throw new Error("Designation source unavailable");
    const text = await response.text();
    if (text.length > 2_000_000) throw new Error("Designation source exceeds limit");
    return text;
  }));
  try {
    if (files[0].status !== "fulfilled") throw new Error("Designation source unavailable");
    if (files[2].status !== "fulfilled") throw new Error("Reviewed NCT designation crosswalk unavailable");
    const index = applyReviewedDesignationLinks(
      buildDesignationIndex(files[0].value, files[1].status === "fulfilled" ? files[1].value : null, new Date().toISOString()),
      files[2].value
    );
    return NextResponse.json(index, { headers: { "Cache-Control": "private, no-store" } });
  } catch {
    return NextResponse.json({ error: "Saved FDA designation details are unavailable. Trial rows remain available." },
      { status: 503, headers: { "Cache-Control": "private, no-store" } });
  }
}
