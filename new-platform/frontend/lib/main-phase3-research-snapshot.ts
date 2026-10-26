/** Archive of one verified MAIN Phase 3 research run; never live candidate membership. */
export const MANDATORY_PHASE3_GATES = [
  "registry_identity", "ticker_drug_indication_identity",
  "current_commercial_rights", "active_phase3_development",
  "public_listing", "market_cap_300m_10b",
  "us_fda_pathway", "verified_pdufa", "original_source_freshness",
] as const;

export type Phase3Gate = (typeof MANDATORY_PHASE3_GATES)[number];
export type Phase3GateCounts = {gate:Phase3Gate;pass:number;fail:number;review:number};
export type PinnedResearchSnapshot = {
  schemaVersion:1;
  reportType:"MAIN_PHASE3_QUALIFICATION_PROGRESS_SCORECARD_RESEARCH_ONLY";
  captureMode:"PINNED_VERIFIED_GITHUB_ACTIONS_RUN_NOT_LIVE";
  sourceRunId:number;sourceRunUrl:string;sourceBranchHead:string;sourcePacificDate:string;
  historicalTrialCount:741;issuerResearchPointerCount:130;
  gateChecksDenominator:6669;gateChecksPass:741;gateChecksFail:0;gateChecksReview:5928;
  trialsWithProvisionalRegisteredDrug:729;secIssuerIndexesFetched:130;
  secPrimaryDocumentsSelected:20;secPrimaryDocumentsAttempted:0;
  secPrimaryDocumentsNotAttemptedMissingContact:20;secPrimaryDocumentsFetched:0;
  trialIssuerTextAvailable:0;rightsReviewChecklistSlots:4446;
  rightsSlotsWithSubmissions:0;rightsSlotsWithReviewerReports:0;
  trialsWithAnySubmissions:0;independentlyVerifiedCurrentRightsTrials:0;
  qualifiedPipelineCount:null;mandatoryGates:Phase3GateCounts[];limitations:string;
};

const record=(x:unknown):x is Record<string,unknown> =>
  x!==null && typeof x==="object" && !Array.isArray(x);
const exactly=(x:Record<string,unknown>,expected:readonly string[]) =>
  Object.keys(x).length===expected.length && expected.every(k=>Object.hasOwn(x,k));
const keys=[
  "schemaVersion","reportType","captureMode","sourceRunId","sourceRunUrl",
  "sourceBranchHead","sourcePacificDate","historicalTrialCount",
  "issuerResearchPointerCount","gateChecksDenominator","gateChecksPass",
  "gateChecksFail","gateChecksReview","trialsWithProvisionalRegisteredDrug",
  "secIssuerIndexesFetched","secPrimaryDocumentsSelected",
  "secPrimaryDocumentsAttempted","secPrimaryDocumentsNotAttemptedMissingContact",
  "secPrimaryDocumentsFetched","trialIssuerTextAvailable",
  "rightsReviewChecklistSlots","rightsSlotsWithSubmissions",
  "rightsSlotsWithReviewerReports","trialsWithAnySubmissions",
  "independentlyVerifiedCurrentRightsTrials","qualifiedPipelineCount",
  "mandatoryGates","limitations",
] as const;
function bad():never {throw new Error("MAIN historical research scorecard integrity is not verified");}

/** Strictly ties displayed metrics to verified GitHub run 40387212933. */
export function parsePinnedResearchSnapshot(raw:unknown):PinnedResearchSnapshot {
  if (!record(raw) || !exactly(raw,keys)
    || raw.schemaVersion!==1
    || raw.reportType!=="MAIN_PHASE3_QUALIFICATION_PROGRESS_SCORECARD_RESEARCH_ONLY"
    || raw.captureMode!=="PINNED_VERIFIED_GITHUB_ACTIONS_RUN_NOT_LIVE"
    || raw.sourceRunId!==40387212933
    || raw.sourceRunUrl!=="https://github.com/pdufa/pdufa-command-center/actions/runs/40387212933"
    || raw.sourceBranchHead!=="e236618ff2b289ed357b72a6994ad2cecfb09e20"
    || raw.sourcePacificDate!=="2026-10-26"
    || raw.historicalTrialCount!==741 || raw.issuerResearchPointerCount!==130
    || raw.gateChecksDenominator!==6669 || raw.gateChecksPass!==741
    || raw.gateChecksFail!==0 || raw.gateChecksReview!==5928
    || raw.trialsWithProvisionalRegisteredDrug!==729
    || raw.secIssuerIndexesFetched!==130
    || raw.secPrimaryDocumentsSelected!==20
    || raw.secPrimaryDocumentsAttempted!==0
    || raw.secPrimaryDocumentsNotAttemptedMissingContact!==20
    || raw.secPrimaryDocumentsFetched!==0 || raw.trialIssuerTextAvailable!==0
    || raw.rightsReviewChecklistSlots!==4446 || raw.rightsSlotsWithSubmissions!==0
    || raw.rightsSlotsWithReviewerReports!==0 || raw.trialsWithAnySubmissions!==0
    || raw.independentlyVerifiedCurrentRightsTrials!==0
    || raw.qualifiedPipelineCount!==null
    || typeof raw.limitations!=="string" || raw.limitations.length<50
    || !Array.isArray(raw.mandatoryGates)
    || raw.mandatoryGates.length!==MANDATORY_PHASE3_GATES.length) bad();
  let passed=0,failed=0,review=0;
  for (const [i,gate] of raw.mandatoryGates.entries()) {
    if (!record(gate) || !exactly(gate,["gate","pass","fail","review"])
      || gate.gate!==MANDATORY_PHASE3_GATES[i]
      || !Number.isSafeInteger(gate.pass) || !Number.isSafeInteger(gate.fail)
      || !Number.isSafeInteger(gate.review)
      || (gate.pass as number)<0 || (gate.fail as number)<0
      || (gate.review as number)<0
      || (gate.pass as number)+(gate.fail as number)+(gate.review as number)!==741
      || gate.pass!==(i===0?741:0)
      || gate.fail!==0 || gate.review!==(i===0?0:741)) bad();
    passed+=gate.pass as number; failed+=gate.fail as number; review+=gate.review as number;
  }
  if (passed!==raw.gateChecksPass || failed!==raw.gateChecksFail
    || review!==raw.gateChecksReview || passed+failed+review!==raw.gateChecksDenominator
    || (raw.secPrimaryDocumentsAttempted as number)+(raw.secPrimaryDocumentsNotAttemptedMissingContact as number)!==raw.secPrimaryDocumentsSelected) bad();
  return raw as PinnedResearchSnapshot;
}