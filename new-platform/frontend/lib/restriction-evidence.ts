import type { RestrictionEvidence } from "./restriction-impact";

/** Quoted RFC 4180 fields, escaped quotes, CRLF and embedded newlines. */
export function parseEvidenceCsv(text: string): Record<string, string>[] {
  const records: string[][] = []; let row: string[] = [], field = "", quoted = false;
  text = text.replace(/^\uFEFF/, "");
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    if (char === '"') {
      if (quoted && text[i + 1] === '"') { field += '"'; i++; }
      else quoted = !quoted;
    } else if (!quoted && (char === "," || char === "\n")) {
      row.push(field.replace(/\r$/, "")); field = "";
      if (char === "\n") { if (row.some(Boolean)) records.push(row); row = []; }
    } else field += char;
  }
  if (quoted) throw new Error("Unclosed CSV quote");
  if (field || row.length) { row.push(field.replace(/\r$/, "")); records.push(row); }
  const headers = records.shift() || [];
  if (!headers.length) throw new Error("Empty source CSV");
  return records.map(values => {
    if (values.length !== headers.length) throw new Error("Source CSV column count mismatch");
    return Object.fromEntries(headers.map((key, i) => [key, values[i].trim()]));
  });
}
export function buildRestrictionEvidence(sources: Record<string, string>, fetchedAt: string): RestrictionEvidence {
  const result: RestrictionEvidence = { fetchedAt, issuers: {}, trialTypes: {}, issues: [], sources: [] };
  const base = "https://raw.githubusercontent.com/pdufa/pdufa-command-center/main/data/";
  const load = (name: string, expected: string) => {
    try {
      if (!sources[name]) throw new Error("unavailable");
      const rows = parseEvidenceCsv(sources[name]);
      if (!rows.length || !(expected in rows[0])) throw new Error("invalid source");
      result.sources.push({ name, url: base + name, rows: rows.length });
      return rows;
    } catch { result.issues.push(name + " unavailable or invalid; affected facts need verification."); return []; }
  };
  const registry = load("company_registry.csv", "exchange");
  const duplicates = new Set<string>(), seen = new Set<string>();
  for (const row of registry) {
    const ticker = row.ticker?.toUpperCase(); if (!ticker) continue;
    if (seen.has(ticker)) duplicates.add(ticker); seen.add(ticker);
    result.issuers[ticker] = { listed: row.exchange && row.status ? "PASS" : "UNKNOWN", marketCap: null, capAsOf: "" };
  }
  for (const ticker of duplicates) result.issuers[ticker].listed = "UNKNOWN";
  const caps = load("phase_pipeline_market_caps.csv", "market_cap_status");
  const capTickers = new Set<string>(), capDuplicates = new Set<string>();
  for (const row of caps) {
    const ticker = row.ticker?.toUpperCase(); if (!ticker) continue;
    if (capTickers.has(ticker)) capDuplicates.add(ticker); capTickers.add(ticker);
    const issuer = result.issuers[ticker] ||= { listed: "UNKNOWN", marketCap: null, capAsOf: "" };
    if (row.market_cap_status === "NOT_LISTED") issuer.listed = "FAIL";
    const cap = Number(row.market_cap);
    issuer.marketCap = row.market_cap_status === "VERIFIED" && Number.isFinite(cap) && cap > 0 ? cap : null;
    issuer.capAsOf = row.market_cap_checked_at || "";
  }
  for (const ticker of capDuplicates) { result.issuers[ticker].marketCap = null; result.issuers[ticker].listed = "UNKNOWN"; }
  const trials = load("all_phase_trials.csv", "intervention_type");
  for (const row of trials) {
    if (!/^NCT\d{8}$/.test(row.nct_id || "")) continue;
    const types = (row.intervention_type || "").split("|").map(t => t.trim().toUpperCase()).filter(Boolean);
    result.trialTypes[row.nct_id] = [...new Set([...(result.trialTypes[row.nct_id] || []), ...types])];
  }
  return result;
}
