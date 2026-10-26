/**
 * Strict CSV parser for a PINNED, public ClinicalTrials.gov Phase 3 research
 * census. No candidate in this source is qualified for PIPELINE by this CSV.
 *
 * This module never computes PDUFA/approval odds, changes source rows or writes.
 */
export const PHASE3_CENSUS_CSV_PATH = "/phase3-census-2026-10-26.csv";
export const PHASE3_CENSUS_EXPECTED_ROWS = 741;
export const PHASE3_CENSUS_EXPECTED_COMPANIES = 130;
export const PHASE3_CENSUS_STATUS_VALUES = [
  "RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION",
  "NOT_YET_RECRUITING", "COMPLETED", "TERMINATED", "WITHDRAWN", "UNKNOWN",
] as const;

export type Phase3CensusRegistryStatus = typeof PHASE3_CENSUS_STATUS_VALUES[number];
export type Phase3CensusTrial = {
  nctId: string;
  ticker: string;
  company: string;
  status: Phase3CensusRegistryStatus;
  sourceUrl: string;
  pipelineQualification: null;
  fdaPdufaVerification: false;
};
export type Phase3CensusRows = {
  rows: Phase3CensusTrial[];
  uniqueCompanies: number;
  statusCounts: Record<Phase3CensusRegistryStatus, number>;
  qualifiedPipelineTotal: null;
  pdufaQualifiedCount: null;
};

const MAX_CSV_LENGTH = 250_000;
const EXPECTED_HEADER = [
  "nct_id", "ticker", "company", "status", "source_url",
];
const fail = (): never => {
  throw new Error("Research inventory unavailable: exact dated CSV integrity check failed.");
};

function readCsv(text: string): string[][] {
  if (typeof text !== "string" || !text.length || text.length > MAX_CSV_LENGTH
      || text.includes("\0")) fail();
  const source = text.charCodeAt(0) === 0xfeff ? text.slice(1) : text;
  const rows: string[][] = [];
  let row: string[] = [], value = "";
  let mode: "start" | "unquoted" | "quoted" | "closed" = "start";
  const field = () => {
    if (value.length > 600) fail();
    row.push(value);
    if (row.length > 5) fail();
    value = "";
    mode = "start";
  };
  const line = () => {
    field();
    if (row.length !== 5 || rows.length > PHASE3_CENSUS_EXPECTED_ROWS) fail();
    rows.push(row);
    row = [];
  };
  for (let i = 0; i < source.length; i++) {
    const c = source[i];
    if (mode === "quoted") {
      if (c === '"') {
        if (source[i + 1] === '"') { value += '"'; i++; }
        else mode = "closed";
      } else value += c;
    } else if (c === ",") field();
    else if (c === "\r" || c === "\n") {
      if (c === "\r" && source[i + 1] === "\n") i++;
      if (mode !== "start" || row.length || value) line();
      else if (i !== source.length - 1) fail();
    } else if (mode === "start" && c === '"') {
      mode = "quoted";
    } else if (mode === "closed" || c === '"') {
      fail();
    } else {
      mode = "unquoted";
      value += c;
    }
    if (value.length > 600) fail();
  }
  if (mode === "quoted") fail();
  if (mode !== "start" || row.length || value) line();
  return rows;
}

/** Reject any edited header, duplicate NCT, spoofed source URL, or row-count drift. */
export function parsePhase3CensusCsv(text: string): Phase3CensusRows {
  const parsed = readCsv(text);
  if (parsed.length !== PHASE3_CENSUS_EXPECTED_ROWS + 1
      || parsed[0].some((v, i) => v !== EXPECTED_HEADER[i])) fail();
  const rowIds = new Set<string>(), tickers = new Set<string>();
  const statusCounts = Object.fromEntries(
    PHASE3_CENSUS_STATUS_VALUES.map(status => [status, 0]),
  ) as Record<Phase3CensusRegistryStatus, number>;
  const rows: Phase3CensusTrial[] = [];
  for (const [nctId, ticker, company, status, sourceUrl] of parsed.slice(1)) {
    if (!/^NCT\d{8}$/.test(nctId) || rowIds.has(nctId)
        || !/^[A-Z]{1,7}(?:[.-][A-Z]{1,3})?$/.test(ticker)
        || !company || company !== company.trim()
        || /[\u0000-\u001f\u007f<>]/u.test(company)
        || !PHASE3_CENSUS_STATUS_VALUES.some(x => x === status)
        || sourceUrl !== "https://clinicaltrials.gov/study/" + nctId) fail();
    rowIds.add(nctId);
    tickers.add(ticker);
    statusCounts[status as Phase3CensusRegistryStatus]++;
    rows.push({
      nctId, ticker, company,
      status: status as Phase3CensusRegistryStatus,
      sourceUrl,
      pipelineQualification: null,
      fdaPdufaVerification: false,
    });
  }
  if (rows.length !== PHASE3_CENSUS_EXPECTED_ROWS
      || tickers.size !== PHASE3_CENSUS_EXPECTED_COMPANIES
      || Object.values(statusCounts).reduce((sum, count) => sum + count, 0)
        !== PHASE3_CENSUS_EXPECTED_ROWS) fail();
  return {
    rows, uniqueCompanies: tickers.size, statusCounts,
    qualifiedPipelineTotal: null,
    pdufaQualifiedCount: null,
  };
}
