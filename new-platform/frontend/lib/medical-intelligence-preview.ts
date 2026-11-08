/** Isolated medical intelligence preview. No scores, forecasts, or external ratings. */
export type TrialEvidence = {
  nct: string;
  title: string;
  conditions: string[];
  interventions: string[];
  phases: string[];
  status: string;
  allocation: string;
  masking: string;
  enrollment: number | null;
  primaryEndpoints: string[];
  secondaryEndpoints: string[];
  resultsPosted: boolean;
  lastUpdate: string;
};
export type InvestigationDomain = {
  id: string;
  title: string;
  scope: "Condition" | "Clinical trial" | "FDA application";
  question: string;
  fdaConsequence: string;
  evidenceNeeded: string;
};
export const FAILURE_INVESTIGATIONS: readonly InvestigationDomain[] = [
  {id:"disease",title:"Disease biology and clinical relevance",scope:"Condition",question:"Could disease heterogeneity, natural history, diagnostic error, or an unvalidated outcome undermine the evidence?",fdaConsequence:"Efficacy or benefit-risk deficiency",evidenceNeeded:"Natural-history data, clinical guidance, disease subtypes and endpoint validation"},
  {id:"mechanism",title:"Mechanism and pharmacology",scope:"Clinical trial",question:"Do target engagement, exposure, dose response, and mechanism support the claimed effect?",fdaConsequence:"Pharmacology or efficacy deficiency",evidenceNeeded:"PK/PD, dose-response, interaction studies and biological rationale"},
  {id:"design",title:"Trial design and patient selection",scope:"Clinical trial",question:"Could randomization, masking, comparators, protocol changes, or eligibility bias distort the result?",fdaConsequence:"Inadequate demonstration of effectiveness",evidenceNeeded:"Protocol, amendments, comparator rationale and randomized-arm details"},
  {id:"endpoint",title:"Primary and secondary endpoints",scope:"Clinical trial",question:"Were prespecified primary endpoints met, clinically meaningful, and accepted for the proposed indication?",fdaConsequence:"Clinical efficacy deficiency",evidenceNeeded:"Protocol-defined endpoints, full trial tables and FDA endpoint guidance"},
  {id:"statistics",title:"Statistical reliability",scope:"Clinical trial",question:"Are effect sizes robust to missing data, multiplicity, censoring and sensitivity analyses?",fdaConsequence:"Statistical deficiency",evidenceNeeded:"Statistical analysis plan, confidence intervals and prespecified sensitivity analyses"},
  {id:"subgroups",title:"Subgroup and cross-trial consistency",scope:"Clinical trial",question:"Do populations, sites, doses, and related pivotal trials show contradictory evidence?",fdaConsequence:"Population restriction or efficacy deficiency",evidenceNeeded:"Prespecified subgroup interactions, companion trials and pooled analyses"},
  {id:"safety",title:"Safety and integrated benefit-risk",scope:"Clinical trial",question:"Could deaths, serious adverse events, organ toxicity, or limited exposure outweigh benefit?",fdaConsequence:"Safety CRL, labeling restriction, or additional study",evidenceNeeded:"Adverse-event tables, integrated safety summaries, exposure and follow-up"},
  {id:"integrity",title:"Data integrity and site conduct",scope:"Clinical trial",question:"Could missing follow-up, protocol deviations, site problems, or data errors affect reliability?",fdaConsequence:"Inspection or study-integrity deficiency",evidenceNeeded:"Site audits, enrollment records, monitoring and FDA inspections"},
  {id:"competition",title:"Treatment comparators and unmet need",scope:"Condition",question:"Does the drug offer a meaningful benefit-risk profile relative to available therapy?",fdaConsequence:"Benefit-risk or labeling concern, depending on context",evidenceNeeded:"Current labeling, treatment guidance and comparable evidence"},
  {id:"prior",title:"FDA precedents and historical CRLs",scope:"FDA application",question:"What deficiencies occurred in genuinely comparable applications, and are they relevant here?",fdaConsequence:"Potential CRL mechanism requiring case-specific verification",evidenceNeeded:"FDA reviews, public CRLs, advisory materials and precedent distinctions"},
  {id:"cmc",title:"Manufacturing, chemistry and product quality",scope:"FDA application",question:"Are process validation, impurities, stability, specifications and supply controls acceptable?",fdaConsequence:"Potential quality/CMC CRL",evidenceNeeded:"Public sponsor disclosures, inspection reports and application information"},
  {id:"inspections",title:"Facility and clinical inspections",scope:"FDA application",question:"Are there documented unresolved facility or clinical-site compliance deficiencies?",fdaConsequence:"Potential inspection-based CRL or delay",evidenceNeeded:"FDA inspection records and verified company updates"},
  {id:"label",title:"Labeling, REMS and delivery system",scope:"FDA application",question:"Are intended claims, risk controls, formulation or device components unresolved?",fdaConsequence:"Approval restriction, CRL, or delay",evidenceNeeded:"Proposed labeling, public FDA discussions and device evidence"},
  {id:"timing",title:"Major amendment and review timing",scope:"FDA application",question:"Is a qualifying major amendment or documented FDA schedule change likely?",fdaConsequence:"Formal extension or missed review goal",evidenceNeeded:"FDA correspondence or dated sponsor disclosure of amendment and goal-date change"}
];
const object = (v: unknown): Record<string, unknown> =>
  v && typeof v === "object" && !Array.isArray(v) ? v as Record<string, unknown> : {};
const objAt = (v: unknown, key: string) => object(object(v)[key]);
const arr = (v: unknown) => Array.isArray(v) ? v : [];
const str = (v: unknown) => typeof v === "string" ? v : "";
const strings = (v: unknown) => arr(v).filter((x): x is string => typeof x === "string");
const endpointTitles = (v: unknown) => arr(v).map(x => str(object(x).measure)).filter(Boolean);
/** A registry observation is not an FDA assessment. Enforce exact NCT matching. */
export function summarizeRegistryStudy(payload: unknown, expectedNct: string): TrialEvidence {
  if (!/^NCT\d{8}$/.test(expectedNct)) throw Error("Invalid NCT");
  const protocol = objAt(payload, "protocolSection");
  const identification = objAt(protocol, "identificationModule");
  const nct = str(identification.nctId);
  if (nct !== expectedNct) throw Error("Registry NCT mismatch");
  const design = objAt(protocol, "designModule");
  const status = objAt(protocol, "statusModule");
  const outcomes = objAt(protocol, "outcomesModule");
  const interventions = objAt(protocol, "armsInterventionsModule");
  const results = objAt(payload, "resultsSection");
  return {
    nct, title:str(identification.briefTitle),
    conditions:strings(objAt(protocol,"conditionsModule").conditions),
    interventions:arr(interventions.interventions).map(x=>str(object(x).name)).filter(Boolean),
    phases:strings(design.phases),
    status:str(status.overallStatus),
    allocation:str(objAt(design,"designInfo").allocation),
    masking:str(objAt(objAt(design,"designInfo"),"maskingInfo").masking),
    enrollment:typeof objAt(design,"enrollmentInfo").count==="number"?objAt(design,"enrollmentInfo").count as number:null,
    primaryEndpoints:endpointTitles(outcomes.primaryOutcomes),
    secondaryEndpoints:endpointTitles(outcomes.secondaryOutcomes),
    resultsPosted:Object.keys(results).length>0,
    lastUpdate:str(objAt(status,"studyFirstPostDateStruct").date) || str(objAt(status,"studyFirstPostDateStruct").type)
  };
}
export const INITIAL_DECISION = {
  applicationOutcome:"Indeterminate — no FDA approval/CRL judgment established",
  timingOutcome:"Indeterminate — no extension/delay judgment established",
  confidence:"Not assessed",
  adjudicatedBlockers:0,
  note:"All investigations begin as unresolved research questions. No concern is confirmed solely from a missing public record or company/registry pointer."
} as const;

export type RegistryBatchAudit={
  byNct:Record<string,TrialEvidence>;
  requestedNcts:string[];
  missingNcts:string[];
  unexpectedNcts:string[];
  duplicateNcts:string[];
  responseCount:number;
};
/** Exact-ID batch reconciliation: registry absence is a data gap, not a trial failure. */
export function reconcileRegistryBatch(payload:unknown,requested:readonly string[]):RegistryBatchAudit{
  const ids=[...new Set(requested)];
  if(!ids.length||ids.length>100||ids.some(id=>!/^NCT\d{8}$/.test(id)))throw Error("Invalid batch NCTs");
  const allowed=new Set(ids);
  const byNct:Record<string,TrialEvidence>={};
  const unexpectedNcts:string[]=[];
  const duplicateNcts:string[]=[];
  const studies=arr(object(payload).studies);
  for(const study of studies){
    const nct=str(objAt(objAt(study,"protocolSection"),"identificationModule").nctId);
    if(!allowed.has(nct)){unexpectedNcts.push(nct||"INVALID");continue;}
    if(byNct[nct]){duplicateNcts.push(nct);continue;}
    try{byNct[nct]=summarizeRegistryStudy(study,nct);}
    catch{unexpectedNcts.push(nct+"-INVALID-PAYLOAD");}
  }
  return {byNct,requestedNcts:ids,missingNcts:ids.filter(id=>!byNct[id]),unexpectedNcts,duplicateNcts,responseCount:studies.length};
}
