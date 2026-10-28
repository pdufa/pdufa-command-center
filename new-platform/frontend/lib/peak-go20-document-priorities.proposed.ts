/** PEAK evidence acquisition priorities; review-only, not an FDA forecast. */
export const PEAK_GO20_DOCUMENT_PRIORITIES = [
  {rank:1, document:"Final statistical analysis plan and endpoint hierarchy", assessmentIds:["S06","S07","S08","S09","S10"], rationale:"Verify multiplicity, estimands, censoring, missing data and sensitivity analyses", status:"NOT_INDEPENDENTLY_REVIEWED", availability:"UNKNOWN"},
  {rank:2, document:"Full protocol, amendments, deviations and randomization documentation", assessmentIds:["S11","S12","S13","S14","S15"], rationale:"Assess design integrity, selection bias and protocol changes", status:"NOT_INDEPENDENTLY_REVIEWED", availability:"UNKNOWN"},
  {rank:3, document:"Integrated clinical study report and patient-level efficacy tables", assessmentIds:["S01","S02","S03","S04","S05"], rationale:"Confirm endpoint results, subgroup consistency, follow-up and durability", status:"NOT_INDEPENDENTLY_REVIEWED", availability:"UNKNOWN"},
  {rank:4, document:"Integrated safety summary, SAE narratives and exposure tables", assessmentIds:["S16","S17","S18","S19","S20"], rationale:"Evaluate hepatic risk, discontinuations, causality and benefit-risk", status:"NOT_INDEPENDENTLY_REVIEWED", availability:"UNKNOWN"},
  {rank:5, document:"FDA application correspondence, review pathway and deficiency records", assessmentIds:["S26","S27","S28","S29","S30"], rationale:"Confirm application identity, review status and unresolved regulatory issues", status:"NOT_INDEPENDENTLY_REVIEWED", availability:"UNKNOWN"},
  {rank:6, document:"CMC validation, stability, facilities and quality records", assessmentIds:["S31","S32","S33","S34","S35"], rationale:"Identify manufacturing or inspection risks not established by efficacy results", status:"NOT_INDEPENDENTLY_REVIEWED", availability:"UNKNOWN"},
  {rank:7, document:"Independent source reconciliation and trial audit records", assessmentIds:["S21","S22","S23","S24","S25"], rationale:"Cross-check registry, abstracts, disclosures and potential inconsistencies", status:"NOT_INDEPENDENTLY_REVIEWED", availability:"UNKNOWN"},
  {rank:8, document:"Population transferability, comparator and historical cohort dossier", assessmentIds:["S36","S37","S38","S39","S40"], rationale:"Assess generalizability and prevent invalid historical approval calibration", status:"NOT_INDEPENDENTLY_REVIEWED", availability:"UNKNOWN"},
] as const;
export const PEAK_GO20_ACQUISITION_STATUS = {
  trialId:"NCT05208047",
  documentsPrioritized:PEAK_GO20_DOCUMENT_PRIORITIES.length,
  reviewedDocuments:0,
  independentlyVerifiedAssessments:0,
  readiness:"INSUFFICIENT_EVIDENCE",
  approvalProbability:null,
} as const;
