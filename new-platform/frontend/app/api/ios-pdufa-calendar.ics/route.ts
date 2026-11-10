import { NextResponse } from "next/server";

/**
 * Public, read-only Apple Calendar subscription for the FOCUS $300M-$10B
 * issuer universe. The published JSON is refreshed separately from the
 * authoritative FOCUS Google Sheet. Never expose Sheets credentials or
 * other private research records to unauthenticated calendar clients.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const SOURCE = "https://raw.githubusercontent.com/pdufa/pdufa-command-center/main/data/ios_focus_pdufa_calendar.json";

type CalendarEvent = {
  id: string; ticker: string; company: string; date: string;
  ncts: string[]; marketCapUsd: number; sourceUrl?: string; drug?: string;
};
type CalendarData = {
  schemaVersion: number; generatedAt: string; events: CalendarEvent[];
};

function escapeIcs(value: string): string {
  return value.replace(/\\/g, "\\\\").replace(/\r?\n/g, "\\n")
    .replace(/,/g, "\\,").replace(/;/g, "\\;");
}
function fold(line: string): string {
  const chunks = [""];
  for (const ch of line) {
    const last = chunks.length - 1;
    if (Buffer.byteLength(chunks[last] + ch, "utf8") > 73) chunks.push(" " + ch);
    else chunks[last] += ch;
  }
  return chunks.join("\r\n");
}
function validDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const d = new Date(value + "T00:00:00Z");
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === value;
}
function plusDay(value: string): string {
  const d = new Date(value + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString().slice(0, 10).replace(/-/g, "");
}
function stamp(value: string): string {
  return new Date(value).toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
}
const failHeaders = { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" };

export async function GET() {
  try {
    const response = await fetch(SOURCE, {
      cache: "no-store", redirect: "error",
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(12000)
    });
    if (!response.ok) throw new Error("Calendar publication unavailable");
    const body = await response.text();
    if (body.length > 300_000) throw new Error("Calendar publication too large");
    const data = JSON.parse(body) as CalendarData;
    if (data.schemaVersion !== 1 || !Array.isArray(data.events)
        || data.events.length > 500 || !data.generatedAt
        || Number.isNaN(Date.parse(data.generatedAt))) {
      throw new Error("Invalid calendar publication");
    }
    const publishedStamp = stamp(data.generatedAt);
    const revision = Math.max(0, Math.floor(Date.parse(data.generatedAt) / 1000));
    const lines = [
      "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//PDUFA//FOCUS Calendar//EN",
      "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
      "X-WR-CALNAME:PDUFA $300M-$10B",
      "X-WR-CALDESC:FOCUS FDA milestone target dates - research only",
      "X-PUBLISHED-TTL:PT1H", "REFRESH-INTERVAL;VALUE=DURATION:PT1H"
    ];
    const seen = new Set<string>();
    for (const item of data.events) {
      if (!item || !/^[a-z0-9-]{3,90}$/.test(item.id)
          || !/^[A-Z0-9.-]{1,10}$/.test(item.ticker)
          || typeof item.company !== "string" || item.company.length > 200
          || !validDate(item.date) || !Array.isArray(item.ncts)
          || item.ncts.length > 30
          || item.ncts.some(nct => typeof nct !== "string" || !/^NCT\d{8}$/.test(nct))
          || !Number.isFinite(item.marketCapUsd)
          || item.marketCapUsd < 300_000_000 || item.marketCapUsd > 10_000_000_000
          || (item.sourceUrl && !/^https:\/\/[^\s]+$/.test(item.sourceUrl))
          || seen.has(item.id)) {
        throw new Error("Invalid PDUFA event or duplicate UID");
      }
      seen.add(item.id);
      const day = item.date.replace(/-/g, "");
      const label = [item.ticker, item.drug ? item.drug : item.company].join(" - ");
      const description = [
        "FOCUS source-reported FDA/PDUFA target; not a confirmed FDA decision.",
        "Reported market cap: $" + (item.marketCapUsd / 1e9).toFixed(2) + "B.",
        item.ncts.length ? "Associated trials: " + item.ncts.join(", ") : "",
        "Source snapshot updated " + data.generatedAt.slice(0, 10) + ".",
        "Dates and company eligibility may change. Verify issuer and FDA releases.",
        item.sourceUrl ? "Evidence: " + item.sourceUrl : ""
      ].filter(Boolean).join("\n");
      lines.push(
        "BEGIN:VEVENT",
        "UID:" + item.id + "@pdufa-new-dashboard.vercel.app",
        "DTSTAMP:" + publishedStamp,
        "LAST-MODIFIED:" + publishedStamp,
        "SEQUENCE:" + revision,
        "DTSTART;VALUE=DATE:" + day,
        "DTEND;VALUE=DATE:" + plusDay(item.date),
        "SUMMARY:" + escapeIcs("PDUFA: " + label),
        "DESCRIPTION:" + escapeIcs(description),
        ...(item.sourceUrl ? ["URL:" + escapeIcs(item.sourceUrl)] : []),
        "TRANSP:TRANSPARENT", "STATUS:CONFIRMED",
        "END:VEVENT"
      );
    }
    lines.push("END:VCALENDAR");
    return new NextResponse(lines.map(fold).join("\r\n") + "\r\n", {
      status: 200,
      headers: {
        "Content-Type": "text/calendar; charset=utf-8",
        "Content-Disposition": "inline; filename=\"pdufa-focus-300m-10b.ics\"",
        "Cache-Control": "public, max-age=0, s-maxage=300, stale-while-revalidate=300",
        "X-Content-Type-Options": "nosniff"
      }
    });
  } catch {
    return NextResponse.json(
      { error: "FOCUS calendar source unavailable; no stale substitute published" },
      { status: 503, headers: failHeaders }
    );
  }
}
