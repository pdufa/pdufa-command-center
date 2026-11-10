import { NextResponse } from "next/server";

/** Public, read-only FOCUS calendar publication. Never expose private Sheets credentials. */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const SOURCE = "https://raw.githubusercontent.com/pdufa/pdufa-command-center/main/data/ios_focus_pdufa_calendar.json";
const noStore = {"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"};

function validDate(date: unknown): date is string {
  if (typeof date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return false;
  const parsed = new Date(date + "T00:00:00Z");
  return !Number.isNaN(parsed.valueOf()) && parsed.toISOString().slice(0,10) === date;
}
export async function GET() {
  try {
    const upstream = await fetch(SOURCE, {
      cache: "no-store", redirect: "error", headers: {Accept:"application/json"},
      signal: AbortSignal.timeout(12000)
    });
    if (!upstream.ok) throw new Error("Publication unavailable");
    const body = await upstream.text();
    if (body.length > 300000) throw new Error("Publication too large");
    const raw: unknown = JSON.parse(body);
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error("Invalid root");
    const data = raw as Record<string,unknown>;
    if (data.schemaVersion !== 1 || !Array.isArray(data.events) || data.events.length > 500 ||
      typeof data.generatedAt !== "string" || !Number.isFinite(Date.parse(data.generatedAt)))
      throw new Error("Invalid publication");
    const seen = new Set<string>();
    const events = data.events.map((item: unknown) => {
      if (!item || typeof item !== "object" || Array.isArray(item)) throw new Error("Invalid event");
      const e = item as Record<string,unknown>;
      if (typeof e.id !== "string" || !/^[a-z0-9-]{3,90}$/.test(e.id) || seen.has(e.id) ||
        typeof e.ticker !== "string" || !/^[A-Z0-9.-]{1,10}$/.test(e.ticker) ||
        typeof e.company !== "string" || e.company.length < 1 || e.company.length > 200 ||
        !validDate(e.date) || typeof e.marketCapUsd !== "number" ||
        !Number.isFinite(e.marketCapUsd) || e.marketCapUsd < 300000000 || e.marketCapUsd > 10000000000 ||
        !Array.isArray(e.ncts) || e.ncts.length > 30 ||
        e.ncts.some(n => typeof n !== "string" || !/^NCT\d{8}$/.test(n)) ||
        (e.drug !== undefined && typeof e.drug !== "string") ||
        (e.sourceUrl !== undefined && (typeof e.sourceUrl !== "string" ||
          !/^https:\/\/[^\s]+$/.test(e.sourceUrl))))
        throw new Error("Invalid event fields");
      seen.add(e.id);
      return {id:e.id,ticker:e.ticker,company:e.company,date:e.date,drug:e.drug||"",
        marketCapUsd:e.marketCapUsd,ncts:e.ncts,sourceUrl:e.sourceUrl||null};
    });
    return NextResponse.json({generatedAt:data.generatedAt,events}, {headers:noStore});
  } catch {
    return NextResponse.json({error:"Calendar source unavailable or invalid; no substitute data is displayed."},
      {status:503,headers:noStore});
  }
}
