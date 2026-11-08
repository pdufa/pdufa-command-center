import { NextRequest, NextResponse } from "next/server";
import focus from "../../../../data/p3PostDataActive.json";
import { summarizeRegistryStudy } from "../../../../lib/medical-intelligence-preview";
import { parseRegistryResults } from "../../../../lib/medical-intelligence-registry-results";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 30;
const headers = { "Cache-Control": "private, no-store" };

// A page open is a GET. External research is deliberately available only as an explicit POST.
export async function POST(req: NextRequest) {
  const origin = req.headers.get("origin");
  if (origin) {
    try {
      if (new URL(origin).host !== req.nextUrl.host)
        return NextResponse.json({ error: "Cross-origin request denied" }, { status: 403, headers });
    } catch {
      return NextResponse.json({ error: "Invalid Origin" }, { status: 403, headers });
    }
  }
  if (!(req.headers.get("content-type") || "").includes("application/json"))
    return NextResponse.json({ error: "JSON body required" }, { status: 415, headers });
  try {
    const body: unknown = await req.json();
    const nct = body && typeof body === "object" && !Array.isArray(body)
      ? (body as Record<string, unknown>).nct : null;
    if (typeof nct !== "string" || !/^NCT\d{8}$/.test(nct) || !focus.records.some(x => x.nct === nct))
      return NextResponse.json({ error: "Exact FOCUS trial required" }, { status: 422, headers });
    const sourceUrl = "https://clinicaltrials.gov/api/v2/studies/" + nct;
    const response = await fetch(sourceUrl, {
      cache: "no-store", headers: { Accept: "application/json" }, signal: AbortSignal.timeout(18000)
    });
    if (!response.ok || !(response.headers.get("content-type") || "").toLowerCase().includes("json"))
      throw Error("Official registry unavailable");
    const raw = await response.text();
    if (raw.length > 6000000) throw Error("Registry response too large");
    const study: unknown = JSON.parse(raw);
    return NextResponse.json({
      nct, sourceUrl, retrievedAt: new Date().toISOString(), status: "SOURCE_RETRIEVED_REQUIRES_REVIEW",
      evidence: summarizeRegistryStudy(study, nct), results: parseRegistryResults(study, nct),
      decision: "INSUFFICIENT_EVIDENCE",
      scope: "Only the ClinicalTrials.gov record was checked. FDA, SEC, PubMed, company, CMC and specialist adjudication are not yet automatic."
    }, { headers });
  } catch {
    return NextResponse.json({
      error: "External registry retrieval or identity verification failed. No prediction was saved."
    }, { status: 503, headers });
  }
}
