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
/** The 13 agreed FDA designations and regulatory mechanisms; not all are designations in the statutory sense. */
export const SPECIAL_DESIGNATION_CATEGORIES = [
  { key: "fast_track", label: "Fast Track Designation" },
  { key: "breakthrough_therapy", label: "Breakthrough Therapy Designation" },
  { key: "priority_review", label: "Priority Review" },
  { key: "accelerated_approval", label: "Accelerated Approval" },
  { key: "orphan_drug", label: "Orphan Drug Designation" },
  { key: "rmat", label: "Regenerative Medicine Advanced Therapy (RMAT)" },
  { key: "qidp", label: "Qualified Infectious Disease Product (QIDP)" },
  { key: "rare_pediatric_disease", label: "Rare Pediatric Disease Designation" },
  { key: "tropical_disease_prv", label: "Tropical Disease Priority Review Voucher" },
  { key: "rare_pediatric_disease_prv", label: "Rare Pediatric Disease Priority Review Voucher" },
  { key: "material_threat_mcm_prv", label: "Material Threat Medical Countermeasure Priority Review Voucher" },
  { key: "lpad", label: "Limited Population Pathway for Antibacterial and Antifungal Drugs (LPAD)" },
  { key: "animal_rule", label: "Animal Rule" },
] as const;
export type DesignationKey = typeof SPECIAL_DESIGNATION_CATEGORIES[number]["key"];
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
  /** False means the saved scanner has no field for this category: counts must show unavailable, not zero. */
  availableKeys?: Partial<Record<DesignationKey, boolean>>;
  programs: Record<string, DesignationProgram>; trialEvents: Record<string, string[]>;
  /** Limited, manually reviewed exact-NCT crosswalk, never a complete FDA designation census. */
  linkageCoverage?: {verifiedNctCount:number;verifiedClaimCount:number;scope:"REVIEWED_EXACT_NCT_DRUG_INDICATION"};
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
  return Object.fromEntries(SPECIAL_DESIGNATION_CATEGORIES.map(({ key }) => [key, unknown(note)])) as TrialDesignations;
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
  const availableKeys = Object.fromEntries(SPECIAL_DESIGNATION_CATEGORIES.map(({key}) => [key, key in rows[0]])) as Record<DesignationKey, boolean>;
  const programs: DesignationIndex["programs"] = Object.create(null);
  const trialEvents: DesignationIndex["trialEvents"] = Object.create(null);
  const seen = new Set<string>(), duplicate = new Set<string>();
  for (const row of rows) {
    const eventKey = row.event_key, ticker = row.ticker?.toUpperCase();
    if (!/^[A-Z][A-Z0-9.-]{0,14}$/.test(ticker || "") || !eventKey?.startsWith(ticker + "|") || eventKey.length > 512) continue;
    if (seen.has(eventKey)) duplicate.add(eventKey);
    seen.add(eventKey);
    programs[eventKey] = { eventKey, ticker, drug: "", indication: "",
      designations: Object.fromEntries(SPECIAL_DESIGNATION_CATEGORIES.map(({ key }) => [key, evidenceFor(row, key)])) as TrialDesignations };
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
  return { schemaVersion: 1, fetchedAt, linkageAvailable, availableKeys, programs, trialEvents };
}

/**
 * Attach claims only when a reviewed dual-source record identifies the precise NCT,
 * intervention, indication, sponsor and a named FDA/SEC/issuer designation source.
 * This does not infer that a regulatory designation was awarded to the trial itself:
 * it connects a documented drug/indication program to its corresponding trial.
 * Ticker-only and date-only joins are forbidden.
 */
export function applyReviewedDesignationLinks(index: DesignationIndex, evidenceCsv: string): DesignationIndex {
  const rows=parseEvidenceCsv(evidenceCsv);
  const required=["event_key","ticker","nct_id","drug","indication","trial_source_url",
    "designation_key","designation_source_url","designation_date","evidence_scope","reviewed_at"];
  if(!rows.length||rows.length>5000||required.some(k=>!(k in rows[0])))
    throw Error("Invalid trial-to-FDA designation crosswalk");
  const supported=new Set<string>(SPECIAL_DESIGNATION_CATEGORIES.map(x=>x.key));
  const unique=new Set<string>();
  const programIdentities=new Map<string,string>();
  let accepted=0;
  for(const row of rows){
    const event=row.event_key?.trim(),ticker=row.ticker?.trim().toUpperCase();
    const nct=row.nct_id?.trim().toUpperCase();
    const key=row.designation_key?.trim() as DesignationKey;
    const program=index.programs[event];
    const source=designationSource(row.designation_source_url);
    const trialSource=designationSource(row.trial_source_url);
    const grantHost=source?new URL(source).hostname:"";
    const ctUrl="https://clinicaltrials.gov/study/"+nct;
    const scope=row.evidence_scope?.trim(),drug=row.drug?.trim(),indication=row.indication?.trim();
    if(!program||!ticker||program.ticker!==ticker||!/^NCT\d{8}$/.test(nct||"")||
      !supported.has(key)||!source||!trialSource||trialSource!==ctUrl||
      !scope||scope.length>600||!drug||!indication||
      !sourceDate(row.reviewed_at)||
      !(/(^|\.)sec\.gov$|(^|\.)fda\.gov$|^investors\.dyne-tx\.com$/).test(grantHost))
      throw Error("Unverifiable trial-to-designation row: "+String(event).slice(0,90));
    const linkKey=[event,nct,key].join("|");
    if(unique.has(linkKey))throw Error("Duplicate reviewed designation claim "+linkKey);
    unique.add(linkKey);
    const identity=drug.toLowerCase()+"|"+indication.toLowerCase();
    if(programIdentities.has(event)&&programIdentities.get(event)!==identity)
      throw Error("Conflicting drug/indication for reviewed event "+event);
    programIdentities.set(event,identity);
    // A known denial/withdrawal cannot be silently replaced by another source.
    const current=program.designations[key];
    if(["NOT_GRANTED","WITHDRAWN","CONFLICT"].includes(current.status))
      throw Error("Conflicting designation claim requires manual review: "+linkKey);
    program.drug=drug;program.indication=indication;
    program.designations[key]={
      status:"GRANTED",verification:grantHost==="www.accessdata.fda.gov"?"FDA_VERIFIED":"SOURCE_RECORDED",
      source,designationDate:sourceDate(row.designation_date),checkedAt:sourceDate(row.reviewed_at),
      note:"Reviewed drug/indication program link to "+nct+"; trial source: "+trialSource+
        ". Scope: "+scope+". This regulatory status belongs to the drug/program, not the trial itself."
    };
    index.trialEvents[nct]=[...new Set([...(index.trialEvents[nct]||[]),event])];
    if(index.availableKeys)index.availableKeys[key]=true;
    accepted++;
  }
  index.linkageAvailable=accepted>0;
  index.linkageCoverage={
    verifiedNctCount:new Set(rows.map(r=>r.nct_id.toUpperCase())).size,
    verifiedClaimCount:accepted,scope:"REVIEWED_EXACT_NCT_DRUG_INDICATION"
  };
  return index;
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
  if (program) for (const { key } of SPECIAL_DESIGNATION_CATEGORIES) result[key] = { ...(program.designations[key] || result[key]) };
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

/** Selected designation checkboxes act as an OR filter within their group.
 * Unlike a missing datum, a source-recorded positive must have a linked HTTPS citation.
 */
export function matchesSelectedDesignations(
  row: Candidate, selected: readonly DesignationKey[], index?: DesignationIndex | null,
): boolean {
  if (!selected.length) return true;
  if (!index) return false;
  const evidence = resolveTrialDesignations(row, index);
  return selected.some(key => evidence[key]?.status === "GRANTED" &&
    evidence[key].verification !== "UNVERIFIED" && !!evidence[key].source);
}

export function filterBySelectedDesignations(
  rows: Candidate[], selected: readonly DesignationKey[], index?: DesignationIndex | null,
): Candidate[] {
  return selected.length ? rows.filter(row => matchesSelectedDesignations(row, selected, index)) : rows;
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
