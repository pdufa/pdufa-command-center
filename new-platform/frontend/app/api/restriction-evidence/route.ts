import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../lib/auth";
import { buildRestrictionEvidence } from "../../../lib/restriction-evidence";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;
const SOURCE = "https://raw.githubusercontent.com/pdufa/pdufa-command-center/main/data/";
const FILES = ["company_registry.csv", "phase_pipeline_market_caps.csv", "all_phase_trials.csv"];

export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  }
  const files = await Promise.allSettled(FILES.map(async name => {
    const response = await fetch(SOURCE + name, { cache: "no-store", signal: AbortSignal.timeout(20000) });
    if (!response.ok) throw new Error("Source unavailable");
    const content = await response.text();
    if (content.length > 8_000_000) throw new Error("Source too large");
    return [name, content] as const;
  }));
  const sources = Object.fromEntries(files.flatMap(result => result.status === "fulfilled" ? [result.value] : []));
  const evidence = buildRestrictionEvidence(sources, new Date().toISOString());
  return NextResponse.json(evidence, { status: evidence.sources.length ? 200 : 503,
    headers: { "Cache-Control": "private, no-store" } });
}
