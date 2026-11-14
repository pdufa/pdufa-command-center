/** Six phase-first, source-bound owner research processors. No worker or FDA forecast. */
import {randomUUID} from "node:crypto";
import canonical from "../data/p3PostDataActive.json";
import collected from "../data/level16AssessmentEvidence.json";

export type Source={url:string;date:string|null;digest:string;kind:string};
export type Fact={text:string;value:unknown;locator:string;sourceUrl:string};
type Worksheet={level:number;facts:Fact[];interpretation:string;reasons:string[];questions:string[];limitations:string[];contradictions:string[];notYetExpected:string[]};
type Comparison={id:string;activeAbstinent:number;activeRandomized:number;activePct:number;placeboAbstinent:number;placeboRandomized:number;placeboPct:number;oddsRatioReported:number;ci95Reported:number[];locator:string};
export type EvidenceTrial={nct:string;ticker:string;company:string;indications:string[];population:string|null;phases:string[];registryStatus:string|null;registryUrl:string;registryDigest:string;registryVersionDate:string;retrievedAt:string;applicationMappingStatus:string;provisionalApplicationCycleIds:string[];protocolCollected:boolean;sapCollected:boolean;registryResultsPresent:boolean;reportedClinicalResultsPresent:boolean;design:Record<string,unknown>;primaryEndpoints:unknown[];sources:Source[];levels:Worksheet[];reportedComparisons:Comparison[];publishedSafety:unknown;statisticalChronology:Record<string,unknown>|null};
export type EvidencePackage={schemaVersion:number;kind:string;evidenceCutoffDate:string;rosterAsOf:string;historicalPredictionInputPermitted:false;ownerReviewStatus:string;externalVerificationRequired:false;trials:EvidenceTrial[]};
export type Check={id:string;label:string;state:"EVIDENCE_AVAILABLE"|"MISSING_EVIDENCE"|"CONFLICTING_EVIDENCE"|"OWNER_CHECK_REQUIRED"|"NOT_YET_EXPECTED";reason:string};
export type LevelResult=Worksheet&{checks:Check[];researchStatus:"EVIDENCE_TO_REVIEW"|"EVIDENCE_GAPS"|"CONFLICTS_TO_RECONCILE"|"PHASE_UNRESOLVED";ownerReviewStatus:"OWNER_NOT_REVIEWED";externalReviewerRequired:false;approvalProbability:null};
export type TrialResult={nct:string;ticker:string;company:string;indications:string[];phases:string[];registryStatus:string|null;applicationMappingStatus:string;provisionalApplicationCycleIds:string[];sources:Source[];levels:LevelResult[];publishedSafety:unknown;statisticalChronology:Record<string,unknown>|null;ownerReviewStatus:"OWNER_NOT_REVIEWED";approvalProbability:null};
export type AssessmentRun={schemaVersion:1;kind:"FOCUS_LEVEL16_OWNER_RESEARCH_RUN";runId:string;startedAt:string;completedAt:string;status:"COMPLETED";evidenceCutoffDate:string;sourceMode:"COLLECTED_EVIDENCE_NO_NEW_RETRIEVAL";historicalPredictionInputPermitted:false;ownerReviewStatus:"OWNER_NOT_REVIEWED";externalVerificationRequired:false;savedToDatabase:false;approvalProbability:null;summary:{trialsProcessed:number;levelsProcessed:number;levelsWithEvidenceGaps:number;levelsWithConflicts:number};trials:TrialResult[]};
export type RunRequest={scope:"ONE";nct:string}|{scope:"ALL"};
const evidence=collected as unknown as EvidencePackage;
const phases=new Set(["EARLY_PHASE1","PHASE1","PHASE2","PHASE3","PHASE4","NA"]);
const day=(s:string)=>/^\d{4}-\d{2}-\d{2}$/.test(s)&&Number.isFinite(Date.parse(s+"T00:00:00Z"))&&new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const https=(s:string)=>{try{const u=new URL(s);return u.protocol==="https:"&&!u.username&&!u.password;}catch{return false;}};

export function validateEvidence(data:EvidencePackage):void{
 if(data.schemaVersion!==1||data.kind!=="FOCUS_LEVEL16_COLLECTED_EVIDENCE_OWNER_RESEARCH"||!day(data.evidenceCutoffDate)||data.historicalPredictionInputPermitted!==false||data.ownerReviewStatus!=="OWNER_NOT_REVIEWED"||data.externalVerificationRequired!==false)throw Error("INVALID_RESEARCH_PACKAGE");
 if(data.trials.length!==canonical.records.length||data.trials.length!==32)throw Error("EXACT_FOCUS_COHORT_REQUIRED");
 const seen=new Set<string>();
 for(const t of data.trials){
  const row=canonical.records.find(r=>r.nct===t.nct);
  if(!row||row.ticker!==t.ticker||row.company!==t.company||seen.has(t.nct))throw Error("TRIAL_IDENTITY_MISMATCH");seen.add(t.nct);
  if(t.registryUrl!=="https://clinicaltrials.gov/api/v2/studies/"+t.nct||!/^[a-f0-9]{64}$/.test(t.registryDigest)||!day(t.registryVersionDate)||t.registryVersionDate>data.evidenceCutoffDate||!/(Z|[+-]\d{2}:\d{2})$/.test(t.retrievedAt)||!Number.isFinite(Date.parse(t.retrievedAt))||new Date(t.retrievedAt).toISOString().slice(0,10)>data.evidenceCutoffDate)throw Error("SOURCE_IDENTITY_VERSION_OR_CUTOFF_MISMATCH");
  if(!Array.isArray(t.phases)||t.phases.some(p=>!phases.has(p)))throw Error("INVALID_PHASE");
  const unmapped=["NCT05031780","NCT06747468","NCT06553768"].includes(t.nct);
  if(unmapped?(t.applicationMappingStatus!=="NOT_MAPPED_APPLICATION_CYCLE"||t.provisionalApplicationCycleIds.length!==0):(t.applicationMappingStatus!=="PROVISIONAL_NOT_VERIFIED"||t.provisionalApplicationCycleIds.length===0))throw Error("APPLICATION_MAPPING_CHANGED");
  const urls=new Set<string>();
  for(const s of t.sources){
   if(!https(s.url)||!/^[a-f0-9]{64}$/.test(s.digest)||urls.has(s.url)||(s.date&&day(s.date)&&s.date>data.evidenceCutoffDate))throw Error("INVALID_SOURCE_REFERENCE");urls.add(s.url);
  }
  if(t.levels.length!==6||t.levels.some((l,i)=>l.level!==i+1||!l.interpretation||!l.questions.length||l.facts.some(f=>!urls.has(f.sourceUrl)||!f.locator)))throw Error("UNBOUND_SIX_LEVEL_RESEARCH");
 }
}
export function parseRunRequest(input:unknown):RunRequest{
 if(!input||typeof input!=="object"||Array.isArray(input))throw Error("Choose one FOCUS trial or all FOCUS trials");
 const v=input as Record<string,unknown>;
 if(v.scope==="ALL"&&Object.keys(v).length===1)return {scope:"ALL"};
 if(v.scope==="ONE"&&Object.keys(v).length===2&&typeof v.nct==="string"&&canonical.records.some(r=>r.nct===v.nct))return {scope:"ONE",nct:v.nct};
 throw Error("Exact current FOCUS NCT required; review claims and extra fields are not accepted");
}
function check(id:string,label:string,present:boolean,reason:string):Check{return {id,label,state:present?"EVIDENCE_AVAILABLE":"MISSING_EVIDENCE",reason};}
function comparisons(t:EvidenceTrial):Check[]{return t.reportedComparisons.map(c=>{
 const numeric=[c.activeAbstinent,c.activeRandomized,c.activePct,c.placeboAbstinent,c.placeboRandomized,c.placeboPct];
 const consistent=numeric.every(Number.isFinite)&&c.activeRandomized>0&&c.placeboRandomized>0&&c.activeAbstinent>=0&&c.activeAbstinent<=c.activeRandomized&&c.placeboAbstinent>=0&&c.placeboAbstinent<=c.placeboRandomized&&Math.abs(100*c.activeAbstinent/c.activeRandomized-c.activePct)<0.051&&Math.abs(100*c.placeboAbstinent/c.placeboRandomized-c.placeboPct)<0.051;
 return {id:c.id,label:"Published counts and rounded percentages",state:consistent?"EVIDENCE_AVAILABLE":"CONFLICTING_EVIDENCE",reason:c.locator+"; numerical consistency only, not an efficacy or significance judgment"};
 });}
// Each processor is independently testable. Phase is resolved before dispatch.
export function processLevel(level:number,t:EvidenceTrial):Check[]{
 const early=t.phases.length>0&&t.phases.every(p=>["EARLY_PHASE1","PHASE1","PHASE2"].includes(p));
 const expectation:Check[]=(early&&(level===3||level===5))?[{id:"future-phase3",label:"Future Phase 3 package",state:"NOT_YET_EXPECTED",reason:"Do not require confirmatory Phase 3 results from an earlier-phase trial"}]:[];
 switch(level){
  case 1:return [check("identity","Exact-NCT registry receipt",t.registryUrl==="https://clinicaltrials.gov/api/v2/studies/"+t.nct&&/^[a-f0-9]{64}$/.test(t.registryDigest),"Receipt identifies "+t.nct+"; digest records byte consistency, not source authentication"),check("cutoff","Dated source version",!!t.registryVersionDate,"Registry version "+t.registryVersionDate+"; retrieved "+t.retrievedAt)];
  case 2:return [check("phase","Registry-listed phase",t.phases.length>0,t.phases.join(", ")||"Phase missing: abstain from phase-specific interpretation"),check("status","Registry-listed status",!!t.registryStatus,t.registryStatus||"Registry status missing"),check("indication","Indication and population",t.indications.length>0&&!!t.population,t.indications.join("; ")),{id:"application",label:"FDA application relationship",state:"OWNER_CHECK_REQUIRED",reason:t.applicationMappingStatus==="NOT_MAPPED_APPLICATION_CYCLE"?"Unmapped trial remains visible; no application cycle inferred":"Provisional cycle links require owner reconciliation; not FDA-verified"}];
  case 3:return [check("results","Reported current-phase clinical results",t.reportedClinicalResultsPresent||t.reportedComparisons.length>0,"Registered endpoints alone are planned measures, not demonstrated efficacy"),...comparisons(t),...expectation];
  case 4:return [check("protocol","Original protocol collected",t.protocolCollected,"Amendment completeness and actual execution still need owner checking"),check("design","Registered design and population",Object.values(t.design).some(v=>v!==null)&&!!t.population,"Compare allocation, controls, masking and population against originals")];
  case 5:return [check("sap","Original SAP collected",t.sapCollected,"A collected SAP does not establish prespecification before unblinding"),...(t.statisticalChronology?.protocolReferenceMismatch?[{id:"protocol-reference",label:"Protocol/SAP reference mismatch",state:"CONFLICTING_EVIDENCE" as const,reason:"SAP references protocol v3; the collected protocol is v4. Reconcile versions; dates alone establish no post-hoc deficiency."}]:[]),...t.reportedComparisons.map(c=>({id:c.id+"-ci",label:"Reported odds-ratio interval consistency",state:(c.ci95Reported.length===2&&c.ci95Reported.every(Number.isFinite)&&c.ci95Reported[0]>0&&c.ci95Reported[0]<=c.oddsRatioReported&&c.oddsRatioReported<=c.ci95Reported[1]?"EVIDENCE_AVAILABLE":"CONFLICTING_EVIDENCE") as Check["state"],reason:c.locator+"; no significance or multiplicity adequacy inferred"})),{id:"prespecification",label:"SAP timing, multiplicity and missing data",state:"OWNER_CHECK_REQUIRED",reason:t.statisticalChronology?"Database lock/unblinding remain unresolved; protocol v3/v4 reference mismatch requires reconciliation":"Compare SAP versions, estimands, alpha allocation, missing data and sensitivity analyses"},...expectation];
  case 6:return [check("endpoints","Registered primary endpoint descriptions",t.primaryEndpoints.length>0,"Endpoint descriptions do not establish medical benefit"),{id:"importance",label:"Disease-specific clinical importance",state:"OWNER_CHECK_REQUIRED",reason:"Assess meaningful magnitude, durability, patient population, harms and disease standards"}];
  default:throw Error("Assessment level must be 1–6");
 }
}
export function assessTrial(t:EvidenceTrial):TrialResult{
 const phaseKnown=t.phases.length>0&&!t.phases.includes("NA");
 const levels=t.levels.map(w=>{
  const checks=phaseKnown||w.level<=2?processLevel(w.level,t):[{id:"phase-first",label:"Current phase unresolved",state:"MISSING_EVIDENCE" as const,reason:"Resolve the current phase before applying evidence requirements"}];
  const conflicts=checks.some(c=>c.state==="CONFLICTING_EVIDENCE");
  const researchStatus:LevelResult["researchStatus"]=!phaseKnown&&w.level>=3?"PHASE_UNRESOLVED":conflicts?"CONFLICTS_TO_RECONCILE":checks.some(c=>c.state==="MISSING_EVIDENCE")?"EVIDENCE_GAPS":"EVIDENCE_TO_REVIEW";
  return {...w,checks,researchStatus,ownerReviewStatus:"OWNER_NOT_REVIEWED" as const,externalReviewerRequired:false as const,approvalProbability:null};
 });
 return {nct:t.nct,ticker:t.ticker,company:t.company,indications:t.indications,phases:t.phases,registryStatus:t.registryStatus,applicationMappingStatus:t.applicationMappingStatus,provisionalApplicationCycleIds:t.provisionalApplicationCycleIds,sources:t.sources,levels,publishedSafety:t.publishedSafety,statisticalChronology:t.statisticalChronology,ownerReviewStatus:"OWNER_NOT_REVIEWED",approvalProbability:null};
}
export function runAssessment(input:unknown,data:EvidencePackage=evidence):AssessmentRun{
 const request=parseRunRequest(input);validateEvidence(data);
 const startedAt=new Date().toISOString();
 const rows=request.scope==="ALL"?data.trials:data.trials.filter(t=>t.nct===request.nct);
 const trials=rows.map(assessTrial);const levels=trials.flatMap(t=>t.levels);
 return {schemaVersion:1,kind:"FOCUS_LEVEL16_OWNER_RESEARCH_RUN",runId:randomUUID(),startedAt,completedAt:new Date().toISOString(),status:"COMPLETED",evidenceCutoffDate:data.evidenceCutoffDate,sourceMode:"COLLECTED_EVIDENCE_NO_NEW_RETRIEVAL",historicalPredictionInputPermitted:false,ownerReviewStatus:"OWNER_NOT_REVIEWED",externalVerificationRequired:false,savedToDatabase:false,approvalProbability:null,summary:{trialsProcessed:trials.length,levelsProcessed:levels.length,levelsWithEvidenceGaps:levels.filter(l=>["EVIDENCE_GAPS","PHASE_UNRESOLVED"].includes(l.researchStatus)).length,levelsWithConflicts:levels.filter(l=>l.researchStatus==="CONFLICTS_TO_RECONCILE").length},trials};
}
export function assessmentOptions(){validateEvidence(evidence);return {evidenceCutoffDate:evidence.evidenceCutoffDate,trials:evidence.trials.map(t=>({nct:t.nct,ticker:t.ticker,company:t.company,indication:t.indications.join("; ")}))};}
