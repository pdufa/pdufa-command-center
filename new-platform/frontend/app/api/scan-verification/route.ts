import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../lib/auth";

// Read-only display of the complete, source-published evidence ledger.
// Verification labels are never inferred or upgraded by the dashboard.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const LEDGER = "https://raw.githubusercontent.com/pdufa/pdufa-command-center/main/data/pdufa_source_verification.csv";
const FIELDS = ["event_key", "ticker", "category", "claim", "verification_status", "verification_required",
  "expected", "observed", "reason", "source_url", "checked_at"] as const;
type Evidence = Record<(typeof FIELDS)[number], string>;

function csvRows(input: string): string[][] {
  const output: string[][] = [];
  let row: string[] = [], field = "", quoted = false;
  for (let i = 0; i < input.length; i++) {
    const ch = input[i];
    if (quoted) {
      if (ch === '"') {
        if (input[i + 1] === '"') { field += '"'; i++; }
        else quoted = false;
      } else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { row.push(field); field = ""; }
    else if (ch === "\n") { row.push(field.replace(/\r$/, "")); output.push(row); row = []; field = ""; }
    else field += ch;
  }
  if (quoted) throw new Error("Unterminated CSV quote");
  if (field || row.length) { row.push(field.replace(/\r$/, "")); output.push(row); }
  return output;
}

export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  }
  try {
    const response = await fetch(LEDGER, { cache: "no-store", signal: AbortSignal.timeout(15000),
      headers: { Accept: "text/csv", "User-Agent": "pdufa-new-platform-verification-ledger" } });
    if (!response.ok) throw new Error("Published evidence ledger unavailable");
    const csv = await response.text();
    if (csv.length > 5_000_000) throw new Error("Oversized evidence ledger");
    const [header, ...rows] = csvRows(csv);
    if (!header || !FIELDS.every(f => header.includes(f))) throw new Error("Invalid evidence columns");
    const indices = Object.fromEntries(FIELDS.map(f => [f, header.indexOf(f)])) as Record<string, number>;
    const records: Evidence[] = rows.filter(row => row.some(Boolean)).map(row => {
      if (row.length !== header.length) throw new Error("Evidence row width mismatch");
      return Object.fromEntries(FIELDS.map(key => [key, row[indices[key]] || ""])) as Evidence;
    });
    const counts: Record<string, number> = {}, categories: Record<string, Record<string, number>> = {};
    for (const item of records) {
      counts[item.verification_status] = (counts[item.verification_status] || 0) + 1;
      const group = categories[item.category] ||= {};
      group[item.verification_status] = (group[item.verification_status] || 0) + 1;
    }
    const params = req.nextUrl.searchParams;
    const category = String(params.get("category") || "ALL").toUpperCase();
    const status = String(params.get("status") || "REVIEW_REQUIRED").toUpperCase();
    const search = String(params.get("search") || "").trim().slice(0, 72).toLowerCase();
    const page = Math.max(1, Math.min(5000, Number.parseInt(params.get("page") || "1", 10) || 1));
    const pageSize = 50;
    const filtered = records.filter(item =>
      (category === "ALL" || item.category === category) &&
      (status === "ALL" || item.verification_status === status) &&
      (!search || [item.ticker, item.event_key, item.claim, item.reason].some(field => field.toLowerCase().includes(search)))
    );
    return NextResponse.json({
      status: "SAVED_SOURCE_LEDGER_NOT_INDEPENDENT_RECHECK", asOf: records.reduce((max, item) =>
        item.checked_at > max ? item.checked_at : max, ""),
      total: records.length, counts, categories, filteredCount: filtered.length,
      page, pageSize, pages: Math.ceil(filtered.length / pageSize),
      items: filtered.slice((page - 1) * pageSize, page * pageSize).map(item => ({
        ...item, source_url: /^https:\/\//i.test(item.source_url) ? item.source_url : ""
      })),
      disclaimer: "These are saved source verification observations, not fresh independent checks or trade permissions."
    }, { headers: { "Cache-Control": "private, no-store" } });
  } catch {
    return NextResponse.json({ error: "Item-level verification ledger is unavailable; no status was inferred" },
      { status: 503, headers: { "Cache-Control": "private, no-store" } });
  }
}
