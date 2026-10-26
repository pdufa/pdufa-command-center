/**
 * Evidence gaps for the dated 741-study *research census*. This is not a
 * PIPELINE eligibility engine, source authenticator or trading decision.
 * Source: 2026-10-26 exact-lead-sponsor market-cap/Phase 3 census.
 */
import {
  parsePhase3CensusCsv, PHASE3_CENSUS_EXPECTED_ROWS,
  type Phase3CensusTrial, type Phase3CensusRows,
} from "./phase3-census-rows";

export const PIPELINE_REVIEW_GATES = [
  { id: "phase3_registry_snapshot", label: "Phase 3 trial identity in dated registry census", state: "CENSUS_ONLY" },
  { id: "listed_market_cap_snapshot", label: "Exact-lead-sponsor listed company in dated $300M–$10B census", state: "CENSUS_ONLY" },
  { id: "drug_indication", label: "Current investigational drug, formulation and indication", state: "NOT_VERIFIED" },
  { id: "program_active", label: "Sponsor confirms program still active / developing", state: "NOT_VERIFIED" },
  { id: "sponsor_rights", label: "Current development rights, sponsor/partner/licensee identity", state: "NOT_VERIFIED" },
  { id: "fda_us_pathway", label: "Authoritative U.S. FDA status, relevant pathway and PDUFA target", state: "NOT_VERIFIED" },
  { id: "mandatory_restrictions", label: "All remaining mandatory Pipeline filters independently checked", state: "NOT_VERIFIED" },
] as const;

type GateId = typeof PIPELINE_REVIEW_GATES[number]["id"];
type GateState = "CENSUS_ONLY" | "NOT_VERIFIED";
export type PipelineReviewGroup = "REGISTRY_OPEN_RECORD" | "REGISTRY_CLOSED_RECORD" | "REGISTRY_UNKNOWN";
export type PipelineEvidenceGap = {
  nctId: string;
  ticker: string;
  company: string;
  registryStatus: Phase3CensusTrial["status"];
  registryGroup: PipelineReviewGroup;
  registrySource: string;
  gates: Record<GateId, GateState>;
  missingEvidenceGateCount: 5;
  sourceVerifiedPipelineEligibility: false;
  qualifiedPipeline: null;
  fdaDecisionProbability: null;
};

function fail(): never {
  throw new Error("Pipeline evidence gap worksheet blocked: census source or qualification status changed.");
}

function groupFor(status: Phase3CensusTrial["status"]): PipelineReviewGroup {
  switch(status) {
    case "RECRUITING":
    case "ACTIVE_NOT_RECRUITING":
    case "ENROLLING_BY_INVITATION":
    case "NOT_YET_RECRUITING":
      return "REGISTRY_OPEN_RECORD";
    case "COMPLETED":
    case "TERMINATED":
    case "WITHDRAWN":
      return "REGISTRY_CLOSED_RECORD";
    case "UNKNOWN":
      return "REGISTRY_UNKNOWN";
  }
}

/** A CLOSED registry trial is NOT proof its development program ended. */
export function assessmentForPhase3CensusRow(row: Phase3CensusTrial): PipelineEvidenceGap {
  if (!row || row.pipelineQualification !== null || row.fdaPdufaVerification !== false
      || !/^NCT\d{8}$/.test(row.nctId)
      || row.sourceUrl !== "https://clinicaltrials.gov/study/" + row.nctId
      || !/^[A-Z]{1,7}(?:[.-][A-Z]{1,3})?$/.test(row.ticker)
      || typeof row.company !== "string" || !row.company
      || !PIPELINE_REVIEW_GATES.length) fail();
  const registryGroup = groupFor(row.status);
  if (!registryGroup) fail();
  return {
    nctId: row.nctId, ticker: row.ticker, company: row.company,
    registryStatus: row.status, registryGroup, registrySource: row.sourceUrl,
    gates: Object.fromEntries(PIPELINE_REVIEW_GATES.map(gate => [gate.id,gate.state])) as Record<GateId,GateState>,
    missingEvidenceGateCount: 5,
    sourceVerifiedPipelineEligibility: false,
    qualifiedPipeline: null,
    fdaDecisionProbability: null,
  };
}

export type PipelineCensusGapSummary = {
  total: 741;
  registryOpenRecords: number;
  registryClosedRecords: number;
  registryUnknownRecords: number;
  qualifiedPipelineTotal: null;
  fdaPdufaQualifiedTotal: null;
  evidenceVerifiedComplete: false;
  gates: typeof PIPELINE_REVIEW_GATES;
};

/** Reconciles all 741 original trial records before presenting anything. */
export function summarizePhase3EvidenceGaps(inventory: Phase3CensusRows): PipelineCensusGapSummary {
  if (!inventory || inventory.rows.length !== PHASE3_CENSUS_EXPECTED_ROWS
      || inventory.qualifiedPipelineTotal !== null || inventory.pdufaQualifiedCount !== null
      || inventory.uniqueCompanies !== 130) fail();
  const ids = new Set<string>();
  let registryOpenRecords=0, registryClosedRecords=0, registryUnknownRecords=0;
  for (const trial of inventory.rows) {
    const row=assessmentForPhase3CensusRow(trial);
    if (ids.has(row.nctId)) fail();
    ids.add(row.nctId);
    if (row.registryGroup==="REGISTRY_OPEN_RECORD") registryOpenRecords++;
    else if (row.registryGroup==="REGISTRY_CLOSED_RECORD") registryClosedRecords++;
    else registryUnknownRecords++;
  }
  if (registryOpenRecords + registryClosedRecords + registryUnknownRecords !== 741
      || registryOpenRecords!==254 || registryClosedRecords!==484 || registryUnknownRecords!==3) fail();
  return {
    total:741, registryOpenRecords, registryClosedRecords,registryUnknownRecords,
    qualifiedPipelineTotal:null, fdaPdufaQualifiedTotal:null,
    evidenceVerifiedComplete:false, gates:PIPELINE_REVIEW_GATES,
  };
}

/** CSV is data-only. It has no reviewer signature, grade, PASS or FDA probability. */
function cell(value: string | number) {
  let safe = String(value).replace(/[\u0000-\u001f\u007f\u202a-\u202e\u2066-\u2069]+/gu," ");
  if (/^\s*[=+\-@]/u.test(safe)) safe="'"+safe;
  return '"' + safe.replaceAll('"','""') + '"';
}

export function buildPhase3EvidenceGapCsv(sourceCsv: string): string {
  const original=parsePhase3CensusCsv(sourceCsv);
  const summary=summarizePhase3EvidenceGaps(original);
  if (summary.qualifiedPipelineTotal!==null || summary.evidenceVerifiedComplete) fail();
  const headers=[
    "nct_id","ticker","company","clinicaltrials_status","registry_status_group",
    "clinicaltrials_source_url",
    ...PIPELINE_REVIEW_GATES.map(gate=>gate.id),
    "missing_independent_evidence_gates","full_pipeline_qualification",
    "fda_probability","review_next_action",
  ];
  const lines=[headers.map(cell).join(",")];
  for (const trial of original.rows) {
    const row=assessmentForPhase3CensusRow(trial);
    const values=[
      row.nctId,row.ticker,row.company,row.registryStatus,row.registryGroup,row.registrySource,
      ...PIPELINE_REVIEW_GATES.map(gate=>row.gates[gate.id]),
      row.missingEvidenceGateCount,"NOT_ESTABLISHED","NOT_AVAILABLE",
      "REVIEW_ORIGINAL_SOURCES_BEFORE_PIPELINE_QUALIFICATION",
    ];
    lines.push(values.map(cell).join(","));
  }
  if (lines.length!==PHASE3_CENSUS_EXPECTED_ROWS+1) fail();
  return lines.join("\r\n")+"\r\n";
}
