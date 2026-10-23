import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../lib/auth";
import { enrichmentDetail, enrichmentKey, enrichmentTicker, validateEnrichmentIndex, type EnrichmentShard } from "../../../lib/shared-enrichment";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 45;
const SOURCE = "https://raw.githubusercontent.com/pdufa/pdufa-command-center/main/data/shared_enrichment/";
const headers = { "Cache-Control": "private, no-store" };
async function published(path: string, maxBytes: number) {
  const response = await fetch(SOURCE+path, {next: {revalidate: 300}, signal: AbortSignal.timeout(20000)});
  if (!response.ok) throw new Error("Shared data source is unavailable");
  const content = await response.text();
  if (Buffer.byteLength(content) > maxBytes) throw new Error("Shared data source exceeds size limit");
  return JSON.parse(content);
}
export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) return NextResponse.json({error: "Authentication required"}, {status: 401, headers});
  const rawTicker = req.nextUrl.searchParams.get("ticker") || "", rawKey = req.nextUrl.searchParams.get("id") || "";
  const ticker = enrichmentTicker(rawTicker), key = enrichmentKey(rawKey);
  if (rawTicker && !ticker || rawKey && (!key || !ticker)) return NextResponse.json({error: "A valid ticker and exact program key are required"}, {status: 400, headers});
  try {
    const [rawIndex, shard] = await Promise.all([published("index.json", 150000), ticker ? published("records/"+ticker+".json", 4000000) : Promise.resolve(null)]);
    const index = validateEnrichmentIndex(rawIndex);
    if (!ticker) return NextResponse.json(index, {headers});
    if (key && !(shard as EnrichmentShard)?.records?.[key]) return NextResponse.json({error: "This exact program has no shared observation record for this ticker yet."}, {status: 404, headers});
    return NextResponse.json(enrichmentDetail(index, shard, ticker, key), {headers});
  } catch {
    return NextResponse.json({error: "Shared research data is temporarily unavailable. Retry to load the saved publication."}, {status: 503, headers});
  }
}
