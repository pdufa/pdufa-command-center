import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../lib/auth";
import { newFromScanSummary } from "../../../lib/scan-new-results";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const BASE = "https://raw.githubusercontent.com/pdufa/pdufa-command-center/main/data/";
const FILES = {
  clinical: "nightly_scan_report.json",
  sources: "pdufa_source_report.json",
  gem: "gem_scan_block_report.json",
  pipelineState: "phase_pipeline_state.json",
  membership: "gem_stage_membership.json",
  daily: "daily_scan_results.json",
  scoring: "nightly_scoring_audit.json",
} as const;

async function published(filename: string) {
  const response = await fetch(BASE + filename, {
    cache: "no-store",
    headers: { "Accept": "application/json", "User-Agent": "pdufa-staging-source-status" },
    signal: AbortSignal.timeout(12000),
  });
  if (!response.ok) throw new Error("Original published report unavailable");
  const obj: unknown = await response.json();
  if (!obj || typeof obj !== "object" || Array.isArray(obj)) {
    throw new Error("Invalid published source report");
  }
  return obj as Record<string, unknown>;
}

export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  }
  // No persistent database connection, no replacement IDs, no scan dispatch,
  // and no mutable session operations. Reads original GitHub scan evidence only.
  const entries = await Promise.all(
    Object.entries(FILES).map(async ([name, filename]) => {
      try { return [name, await published(filename)] as const; }
      catch { return [name, null] as const; }
    }),
  );
  const [clinical, sources, gem, pipelineState, membership, daily, scoring] = [
    entries.find(([name]) => name === "clinical")?.[1],
    entries.find(([name]) => name === "sources")?.[1],
    entries.find(([name]) => name === "gem")?.[1],
    entries.find(([name]) => name === "pipelineState")?.[1],
    entries.find(([name]) => name === "membership")?.[1],
    entries.find(([name]) => name === "daily")?.[1],
    entries.find(([name]) => name === "scoring")?.[1],
  ];
  if (!clinical && !sources && !gem) {
    return NextResponse.json({ error: "Original published scans temporarily unavailable" },
                             { status: 503, headers: { "Cache-Control": "private, no-store" } });
  }
  return NextResponse.json({
    status: [clinical, sources, gem].every(Boolean) ? "PUBLISHED" : "PARTIAL_PUBLISHED",
    clinical, sources, gem, daily, scoring,
    newFromScan: newFromScanSummary(clinical, gem, pipelineState, membership),
    caveat: "Read-only original Streamlit reports. Does not certify new-platform storage or trading readiness.",
  }, { headers: { "Cache-Control": "private, no-store" } });
}
