/**
 * User-selected PDUFA Pipeline policy (2026-11-06).
 * Research census is NOT a verified live Pipeline eligibility result.
 * PASS/FAIL/UNKNOWN are per-source audit classifications, not FDA predictions.
 * Never delete historical NCT rows or rewrite old RAAS scores.
 */
export type TrialLifecycle = "ACTIVE" | "HISTORICAL" | "VERIFY";
export type AuditVerdict = "PASS" | "FAIL" | "UNKNOWN";
export type ControlKind = "GATE" | "CLASSIFICATION" | "WORKFLOW";
export type PolicyRule = {
  id: string; label: string; detail: string; enabled: boolean; kind: ControlKind;
};
export const ACTIVE_REGISTRY_STATUSES = [
 "RECRUITING","ACTIVE_NOT_RECRUITING","ENROLLING_BY_INVITATION","NOT_YET_RECRUITING"
] as const;
export const HISTORICAL_REGISTRY_STATUSES = ["COMPLETED","TERMINATED","WITHDRAWN"] as const;

export function trialLifecycle(status: string | null | undefined): TrialLifecycle {
 const s = (status || "").trim().toUpperCase();
 if ((ACTIVE_REGISTRY_STATUSES as readonly string[]).includes(s)) return "ACTIVE";
 if ((HISTORICAL_REGISTRY_STATUSES as readonly string[]).includes(s)) return "HISTORICAL";
 // SUSPENDED and UNKNOWN are queued, not called completed or active.
 return "VERIFY";
}
export const ENABLED_POLICY: readonly PolicyRule[] = [
 {id:"public",label:"Publicly traded issuer",detail:"Verify an active public listing, associated developer and exact drug-program rights.",enabled:true,kind:"GATE"},
 {id:"cap",label:"Market capitalization $300M–$10B",detail:"Inclusive range; verify separately at program entry and at current date. Historical census membership is not a fresh quote.",enabled:true,kind:"GATE"},
 {id:"phase",label:"Phase 3 or post-Phase 3",detail:"Require verified individual-trial Phase 3 or a linked regulatory-stage drug program; preserve earlier-stage studies in research.",enabled:true,kind:"GATE"},
 {id:"fda",label:"US FDA drug or biologic pathway",detail:"Require source-backed US FDA relevance for the drug and indication.",enabled:true,kind:"GATE"},
 {id:"activeprog",label:"Continuing drug-development program",detail:"An ongoing trial supports development activity, but completion of a single trial does not establish program termination.",enabled:true,kind:"GATE"},
 {id:"identity",label:"Exact drug, indication, sponsor and issuer",detail:"Reconcile NCT, indication, sponsor, current developer and commercial rights, not ticker alone.",enabled:true,kind:"GATE"},
 {id:"sources",label:"Retain original documentary sources",detail:"Store registry, issuer, SEC, FDA and published evidence, with dates and scope; missing evidence is UNKNOWN.",enabled:true,kind:"GATE"},
 {id:"purpose",label:"Identify pivotal or supportive trial purpose",detail:"Classify pivotal efficacy, safety-primary, extension, supportive and postmarketing roles before requiring results.",enabled:true,kind:"CLASSIFICATION"},
 {id:"activeview",label:"Exclude closed studies from Active Phase View",detail:"Hide completed, terminated and withdrawn NCTs only from active-study monitoring; never delete them.",enabled:true,kind:"GATE"},
 {id:"pdufa-retain",label:"Keep eligible completed studies in PDUFA monitoring",detail:"A completed pivotal trial may support an NDA/BLA and upcoming FDA decision; require exact drug-indication regulatory linkage.",enabled:true,kind:"WORKFLOW"},
 {id:"stage",label:"Track complete FDA application lifecycle",detail:"Distinguish ongoing Phase 3, awaiting filing, submitted, accepted, scheduled PDUFA, approved, CRL and other outcomes.",enabled:true,kind:"CLASSIFICATION"},
 {id:"rights",label:"Verify rights and licensing",detail:"Require current indication- and territory-specific development/commercial rights to the product.",enabled:true,kind:"GATE"},
 {id:"dedup",label:"One FDA application per decision",detail:"Do not infer application identity from NCT or ticker. Deduplicate only verified application/review-cycle IDs while preserving each trial.",enabled:true,kind:"WORKFLOW"},
 {id:"unknown",label:"Queue unknown or stale trial status",detail:"Unverified, unknown, suspended or stale statuses require review, not automatic exclusion.",enabled:true,kind:"CLASSIFICATION"},
 {id:"phasefirst",label:"Phase-first evidence requirements",detail:"Determine trial phase and purpose, then require only data expected at that stage.",enabled:true,kind:"CLASSIFICATION"},
 {id:"outcome",label:"Classify actual outcomes",detail:"Keep MET, NOT_MET, pending, descriptive, exploratory and safety-only outcomes distinct.",enabled:true,kind:"CLASSIFICATION"},
 {id:"missingness",label:"Phase-correct missing-data denominator",detail:"Count genuinely missing expected evidence; exclude pending, not-yet-expected and inapplicable requirements.",enabled:true,kind:"WORKFLOW"},
 {id:"ratings",label:"Preserve five clinical research ratings",detail:"Keep validated source-backed grades and N/A values. Missing grade must never become zero.",enabled:true,kind:"WORKFLOW"},
 {id:"history",label:"Preserve RAAS history and benchmarks",detail:"Do not delete legacy ratings, FDA outcome histories, prediction freezes or supporting historical evidence.",enabled:true,kind:"WORKFLOW"},
 {id:"freshness",label:"Monitor source freshness",detail:"Recheck registry, issuer and FDA status and date-stamp snapshots; stale data is a verification task.",enabled:true,kind:"CLASSIFICATION"},
 {id:"capdate",label:"Keep immutable entry and current cap observations",detail:"Do not overwrite the entry-date quote with a current quote; retain source, checked time and basis.",enabled:true,kind:"WORKFLOW"},
 {id:"counts",label:"Show pass, fail and unknown by rule",detail:"Audit each source-qualified restriction independently; a PASS is not the same as full PIPELINE eligibility.",enabled:true,kind:"WORKFLOW"},
 {id:"gem",label:"Keep GEM / GEM JR retired",detail:"No GEM or GEM JR active Pipeline eligibility or scoring path; preserve historical records.",enabled:true,kind:"WORKFLOW"}
];
export const DISABLED_POLICY: readonly PolicyRule[] = [
 {id:"runway",label:"Minimum 12-month cash runway",detail:"Optional; OFF.",enabled:false,kind:"GATE"},
 {id:"window",label:"PDUFA date within 730 days",detail:"Optional; OFF.",enabled:false,kind:"GATE"},
 {id:"hold",label:"Exclude unresolved clinical holds",detail:"Optional; OFF.",enabled:false,kind:"GATE"},
 {id:"dilution",label:"Financing and dilution",detail:"Optional; OFF.",enabled:false,kind:"GATE"},
 {id:"liquidity",label:"Trading liquidity and volume",detail:"Optional; OFF.",enabled:false,kind:"GATE"},
 {id:"technical",label:"Price and technical indicators",detail:"Optional; OFF.",enabled:false,kind:"GATE"},
 {id:"designations",label:"FDA special designations",detail:"Optional; OFF.",enabled:false,kind:"GATE"}
];
export type PolicyTrial = {
 nctId:string; ticker:string; company:string; registryStatus:string;
 registryAsOf?:string|null;registrySourceUrl?:string|null;
 drug?:string|null;indication?:string|null;fdaApplicationStatus?:string|null;
 pdufaGoalDate?:string|null;readoutOutcome?:string|null;
};
export type RuleAudit = {status:AuditVerdict; reason:string};

/** For unavailable fields, do not turn absence into a FAIL or fabricated PASS. */
export function auditPolicyRule(ruleId:string,trial:PolicyTrial,asOf:string):RuleAudit {
 const lifecycle=trialLifecycle(trial.registryStatus);
 const validNct=/^NCT\d{8}$/.test(trial.nctId);
 const registrySource=(trial.registrySourceUrl||"") === "https://clinicaltrials.gov/study/"+trial.nctId;
 const asOfMs=Date.parse(asOf+"T00:00:00Z");
 const checked=Date.parse(trial.registryAsOf||"");
 const fresh=Number.isFinite(checked)&&Number.isFinite(asOfMs)&&checked<=asOfMs+86400000&&asOfMs-checked<=30*86400000;
 switch(ruleId){
  case "phase":return validNct&&registrySource
   ? {status:"PASS",reason:"Exact NCT is in the dated Phase 3 research census; current phase must still be rechecked for live qualification."}
   : {status:"UNKNOWN",reason:"Individual study Phase 3 status requires registry verification."};
  case "activeview":return lifecycle==="ACTIVE"
   ? {status:"PASS",reason:"Ongoing-study row is visible in Active Phase View."}
   : lifecycle==="HISTORICAL"
   ? {status:"FAIL",reason:"Closed-study row is hidden only from Active Phase View, retained in historical and PDUFA review."}
   : {status:"UNKNOWN",reason:"Registry status needs review; not assumed active or closed."};
  case "activeprog":return lifecycle==="ACTIVE"&&fresh
   ? {status:"PASS",reason:"Recent registry snapshot supports ongoing study activity; verify the sponsor's current program separately."}
   : {status:"UNKNOWN",reason:"Closed/uncertain study status does not determine whether the overall drug program continues."};
  case "sources":return validNct&&registrySource
   ? {status:"PASS",reason:"An exact-NCT registry source URL is recorded; other required sources remain separately reviewable."}
   : {status:"UNKNOWN",reason:"Exact original registry source needs verification."};
  case "unknown":
  case "freshness":return lifecycle!=="VERIFY"&&fresh
   ? {status:"PASS",reason:"Known registry status recorded within 30 days of the audit; not a live response."}
   : {status:"UNKNOWN",reason:"Uncertain or stale registry status requires an exact-NCT refresh."};
  case "outcome":return ["PRIMARY_ENDPOINT_MET","PRIMARY_ENDPOINT_NOT_MET","NO_BINARY_PASS_FAIL"].includes(trial.readoutOutcome||"")
   ? {status:"PASS",reason:"A historical endpoint category is recorded. PASS refers only to documented classification, not trial success."}
   : {status:"UNKNOWN",reason:"No source-adjudicated outcome category here; results may be pending or safety/descriptive."};
  // Current listing, cap, sponsor/rights, FDA application identity and phase-based
  // scientific grades cannot be verified from the dated census alone.
  default:return {status:"UNKNOWN",reason:"Requires a separately source-verified exact-program fact or a workflow-specific audit; no exclusion or zero score inferred."};
 }
}
export function auditCensus(trials:readonly PolicyTrial[],asOf:string){
 const ids=new Set<string>();
 for(const trial of trials){
  if(!/^NCT\d{8}$/.test(trial.nctId)||ids.has(trial.nctId))throw Error("CENSUS_IDENTITY_NOT_UNIQUE");
  ids.add(trial.nctId);
 }
 const lifecycle={ACTIVE:0,HISTORICAL:0,VERIFY:0};
 for(const trial of trials)lifecycle[trialLifecycle(trial.registryStatus)]++;
 const rules=ENABLED_POLICY.map(rule=>{
  const count:{PASS:number;FAIL:number;UNKNOWN:number}={PASS:0,FAIL:0,UNKNOWN:0};
  for(const trial of trials)count[auditPolicyRule(rule.id,trial,asOf).status]++;
  if(count.PASS+count.FAIL+count.UNKNOWN!==trials.length)throw Error("RULE_COUNTS_INVALID");
  return {id:rule.id,label:rule.label,detail:rule.detail,kind:rule.kind,counts:count,
   automaticGate:rule.id==="activeview",
   note:rule.kind==="GATE"?"Evidence readiness audit, not automatic live PIPELINE qualification.":"Classification or preservation control; UNKNOWN means a per-trial result is not established."};
 });
 return {asOf,trialCount:trials.length,lifecycle,rules,disabled:DISABLED_POLICY,
  qualification:"NOT_VERIFIED" as const,
  retainedHistorical: lifecycle.HISTORICAL,
  notes:["All exact NCTs stay in the source universe and RAAS history.","A completed trial can still support a live NDA/BLA or PDUFA application.","Only activeview is a UI exclusion here; other audit PASS entries are not an admission to PIPELINE.","Original entry-time market-cap snapshots and application deduplication require verified source data before full enforcement."]};
}
export type MarketCapSnapshot={nctId:string;ticker:string;usd:number;basis:"ENTRY"|"CURRENT";observedAt:string;sourceUrl:string};
/** Strict immutable append helper. An unverified quote cannot silently replace historical cap. */
export function appendCapSnapshot(previous:readonly MarketCapSnapshot[],next:MarketCapSnapshot){
 if(!/^NCT\d{8}$/.test(next.nctId)||!next.ticker||!Number.isFinite(next.usd)||next.usd<=0||
    !/^\d{4}-\d{2}-\d{2}(T.*)?$/.test(next.observedAt)||!Number.isFinite(Date.parse(next.observedAt))||
    !/^https:\/\//.test(next.sourceUrl))throw Error("CAP_SOURCE_INVALID");
 if(previous.some(p=>p.nctId===next.nctId&&p.basis===next.basis&&p.observedAt===next.observedAt))
   throw Error("IMMUTABLE_CAP_OBSERVATION_ALREADY_EXISTS");
 return [...previous,next];
}
