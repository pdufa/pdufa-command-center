import type { Candidate } from "../app/Workspace";
import { parseEvidenceCsv } from "./restriction-evidence";
import { trialId } from "./pipeline-data";

export const DESIGNATION_COLUMNS = [
  { key: "fast_track", label: "Fast Track" },
  { key: "breakthrough_therapy", label: "Breakthrough Therapy" },
  { key: "rmat", label: "RMAT" },
  { key: "orphan_drug", label: "Orphan Drug" },
  { key: "priority_review", label: "Priority Review" },
  { key: "accelerated_approval", label: "Accelerated Approval" },
] as const;
export type DesignationKey = typeof DESIGNATION_COLUMNS[number]["key"];
export type DesignationEvidence = {
  status: "GRANTED" | "REQUESTED" | "NOT_GRANTED" | "WITHDRAWN" | "UNKNOWN" | "CONFLICT";
  verification: "FDA_VERIFIED" | "SOURCE_RECORDED" | "UNVERIFIED";
  source: string; designationDate: string; checkedAt: string; note: string;
};
export type TrialDesignations = Record<DesignationKey, DesignationEvidence>;
export type DesignationProgram = {
  eventKey: string; ticker: string; drug: string; indication: string;
  designations: TrialDesignations;
};
export type DesignationIndex = {
  schemaVersion: 1; fetchedAt: string; linkageAvailable: boolean;
  programs: Record<string, DesignationProgram>; trialEvents: Record<string, string[]>;
};

export function designationSource(value: string | undefined): string {
  try {
    const url = new URL(value || "");
    return url.protocol === "https:" && !url.username && !url.password ? url.href : "";
  } catch { return ""; }
}
function fdaDocument(value: string): boolean {
  const source = designationSource(value);
  if (!source) return false;
  const url = new URL(source);
  return (url.hostname === "fda.gov" || url.hostname.endsWith(".fda.gov")) && url.pathname !== "/";
}
function sourceDate(value: string | undefined): string {
  if (!value) return "";
  const day = value.slice(0, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(day) && Number.isFinite(Date.parse(day)) &&
    new Date(day).toISOString().slice(0, 10) === day ? day : "";
}
function unknown(note = "No designation evidence is linked to this exact trial or application."): DesignationEvidence {
  return { status: "UNKNOWN", verification: "UNVERIFIED", source: "", designationDate: "", checkedAt: "", note };
}
export function emptyTrialDesignations(note?: string): TrialDesignations {
  return Object.fromEntries(DESIGNATION_COLUMNS.map(({ key }) => [key, unknown(note)])) as TrialDesignations;
}
function evidenceFor(row: Record<string, string>, key: DesignationKey): DesignationEvidence {
  const value = (row[key] || "").trim().toUpperCase();
  const source = designationSource(row[key + "_source_url"] || row.designation_source_url);
  const statuses: Record<string, DesignationEvidence["status"]> = {
    YES: "GRANTED", GRANTED: "GRANTED", APPROVED: "GRANTED", CONFIRMED: "GRANTED",
    REQUESTED: "REQUESTED", PENDING: "REQUESTED", NO: "NOT_GRANTED", DENIED: "NOT_GRANTED",
    REJECTED: "NOT_GRANTED", WITHDRAWN: "WITHDRAWN", RESCINDED: "WITHDRAWN",
  };
  // Blank flags and a scan with no verified positive are never evidence of NO.
  if (!statuses[value] || !source) return unknown(row.designation_evidence_note || undefined);
  return {
    status: statuses[value], verification: "SOURCE_RECORDED", source,
    designationDate: sourceDate(row[key + "_designation_date"] || row[key + "_approval_date"]),
    checkedAt: sourceDate(row[key + "_verified_at"] || row.designation_verified_at),
    note: row.designation_evidence_note || "Saved source record; current status has not been independently rechecked.",
  };
}
function ncts(value: string | undefined): string[] {
  return [...new Set((value || "").toUpperCase().split(/[|;,\s]+/).filter(x => /^NCT\d{8}$/.test(x)))];
}

/** Exact application keys and explicit NCT links only. Never join by ticker or deadline. */
export function buildDesignationIndex(csv: string, applicationsCsv: string | null, fetchedAt: string): DesignationIndex {
  const rows = parseEvidenceCsv(csv);
  if (!rows.length || rows.length > 5000 ||
      ["event_key", "ticker", ...DESIGNATION_COLUMNS.map(x => x.key)].some(key => !(key in rows[0]))) {
    throw new Error("Invalid designation source");
  }
  const programs: DesignationIndex["programs"] = Object.create(null);
  const trialEvents: DesignationIndex["trialEvents"] = Object.create(null);
  const seen = new Set<string>(), duplicate = new Set<string>();
  for (const row of rows) {
    const eventKey = row.event_key, ticker = row.ticker?.toUpperCase();
    if (!/^[A-Z][A-Z0-9.-]{0,14}$/.test(ticker || "") || !eventKey?.startsWith(ticker + "|") || eventKey.length > 512) continue;
    if (seen.has(eventKey)) duplicate.add(eventKey);
    seen.add(eventKey);
    programs[eventKey] = { eventKey, ticker, drug: "", indication: "",
      designations: Object.fromEntries(DESIGNATION_COLUMNS.map(({ key }) => [key, evidenceFor(row, key)])) as TrialDesignations };
  }
  for (const key of duplicate) delete programs[key];
  const link = (row: Record<string, string>) => {
    const program = programs[row.event_key];
    if (!program || program.ticker !== row.ticker?.toUpperCase()) return;
    program.drug = row.drug || program.drug;
    program.indication = row.indication || program.indication;
    for (const nct of ncts(row.nct_id)) trialEvents[nct] = [...new Set([...(trialEvents[nct] || []), program.eventKey])];
  };
  for (const row of rows) link(row);
  let linkageAvailable = false;
  if (applicationsCsv) {
    try {
      const applications = parseEvidenceCsv(applicationsCsv);
      if (applications.length && ["event_key", "ticker", "nct_id"].every(key => key in applications[0])) {
        const counts = new Map<string, number>();
        for (const row of applications) counts.set(row.event_key, (counts.get(row.event_key) || 0) + 1);
        for (const row of applications) if (counts.get(row.event_key) === 1) link(row);
        linkageAvailable = true;
      }
    } catch { /* Keep exact application records available when trial links are unavailable. */ }
  }
  return { schemaVersion: 1, fetchedAt, linkageAvailable, programs, trialEvents };
}

export function resolveTrialDesignations(row: Candidate, index?: DesignationIndex | null): TrialDesignations {
  const result = emptyTrialDesignations();
  let program: DesignationProgram | undefined;
  const eventKey = row.id.startsWith("APPLICATION|") ? row.id.slice("APPLICATION|".length) : "";
  if (eventKey) {
    if (row.eventKey && row.eventKey !== eventKey) return emptyTrialDesignations("Application identities disagree; the applicable program needs review.");
    const exact = index?.programs[eventKey];
    if (exact?.ticker === row.ticker.toUpperCase()) program = exact;
  } else {
    const matches = (index?.trialEvents[trialId(row)] || []).map(key => index?.programs[key])
      .filter((value): value is DesignationProgram => !!value &&
        (row.ticker === "CLINICAL TRIAL" || value.ticker === row.ticker.toUpperCase()));
    if (matches.length === 1) program = matches[0];
    else if (matches.length > 1) return emptyTrialDesignations("Multiple applications are linked to this trial; the applicable drug/indication needs review.");
  }
  if (program) for (const { key } of DESIGNATION_COLUMNS) result[key] = { ...program.designations[key] };
  // Preserve the existing application-specific FDA-verified Priority Review alert.
  const priority = row.priorityReview;
  if (priority?.status === "FDA_VERIFIED" && fdaDocument(priority.source || "")) {
    if (["NOT_GRANTED", "WITHDRAWN"].includes(result.priority_review.status)) {
      result.priority_review = { ...result.priority_review, status: "CONFLICT", verification: "UNVERIFIED",
        note: "Linked Priority Review sources disagree; review the application-specific evidence." };
    } else result.priority_review = {
      status: "GRANTED", verification: "FDA_VERIFIED", source: designationSource(priority.source),
      designationDate: sourceDate(priority.designationDate), checkedAt: "",
      note: "Application-specific FDA Priority Review evidence linked in the Pipeline record.",
    };
  }
  return result;
}

export function designationLabel(value: DesignationEvidence, key: DesignationKey): string {
  if (value.status === "GRANTED") return value.verification === "FDA_VERIFIED"
    ? key === "priority_review" ? "IMP: Priority Review" : "Granted · FDA verified"
    : key === "accelerated_approval" ? "Approval reported" : "Grant reported";
  return { UNKNOWN: "Not verified", REQUESTED: "Requested", NOT_GRANTED: "Not granted",
    WITHDRAWN: "Withdrawn", CONFLICT: "Needs review" }[value.status];
}

/** Supplemental FDA details accompany the original, otherwise unmodified registry fields. */
export function trialDesignationDownload(study: Record<string, unknown>, row: Candidate, index?: DesignationIndex | null) {
  return { ...study, pdufaRegulatoryDetails: {
    trialId: trialId(row), applicationKey: row.id.startsWith("APPLICATION|") ? row.eventKey || row.id.slice(12) : "",
    sourceRetrievedAt: index?.fetchedAt || "", designations: resolveTrialDesignations(row, index),
    note: "Supplemental FDA designation/program evidence; not part of the ClinicalTrials.gov registry record. Missing evidence is UNKNOWN.",
  } };
}
