/** Exact-identity FDA research queue. Readiness is not a three-way forecast.
 * Preserve Phase 2 exclusions and do not collapse applications sharing ticker.
 */
export type PredictionQueueStatus="ABSTAIN";
export type FDAQueueKind="ACCEPTED_NDA_SOURCE"|"ISSUER_GOAL_LEAD";
export type FDAQueueEligibility="PHASE3_SOURCE_ELIGIBLE"|"PHASE2_EXCLUDED"|"NOT_YET_VERIFIED";
export type FDAPredictionQueueItem={
  key:string;ticker:string;drug:string;indication:string;
  kind:FDAQueueKind;eligible:FDAQueueEligibility;
  targetDate:string;trialNctId:string|null;trialName:string|null;
  sourceUrl:string;outcomeEvidenceUrl:string|null;
  decision:PredictionQueueStatus;
  probabilities:{PASS:null;CRL:null;EXTENSION:null};
  blockers:readonly string[];
};
type Accepted={
  applicationKey:string;drug:string;indication:string;
  phaseOfPivotalEvidence:number;trialNctId:string;trialName:string;
  pdufaTargetDate:string;applicationAcceptedSourceUrl:string;outcomeEvidenceUrl:string;
};
type Lead={
  legacyCaseKey:string;ticker:string;drug:string;legacyGoalDate:string;
  firstCycleGoalDate:string;issuerSourceUrl:string;
  sourceDocumentLocated:boolean;applicationNumberIndependentlyVerified:boolean;
  exactReviewCycleIndependentlyVerified:boolean;
  prospectivelyFrozenThreeWayProbabilities:boolean;
  formalGoalRevision:null|{revisedGoalDate:string;sourceUrl:string};
};
const isDay=(x:string)=>/^\d{4}-\d{2}-\d{2}$/.test(x)&&
  !Number.isNaN(Date.parse(x+"T00:00:00Z"))&&new Date(x+"T00:00:00Z").toISOString().slice(0,10)===x;
const sourceUrl=(x:string)=>x.startsWith("https://")&&x.length<1200;
const baseline=()=>({PASS:null,CRL:null,EXTENSION:null} as const);
export function buildRaasPredictionQueue(
 accepted:readonly Accepted[], leads:readonly Lead[],cogentTicker="COGT"
):readonly FDAPredictionQueueItem[]{
 const rows:FDAPredictionQueueItem[]=[];
 const keys=new Set<string>();
 const add=(row:FDAPredictionQueueItem)=>{
   if(!row.key||keys.has(row.key)||!isDay(row.targetDate)||
      !sourceUrl(row.sourceUrl)||!row.ticker||!row.drug||
      (row.trialNctId!==null&&!/^NCT\d{8}$/.test(row.trialNctId))||
      row.probabilities.PASS!==null||row.probabilities.CRL!==null||
      row.probabilities.EXTENSION!==null)throw Error("RAAS_FDA_QUEUE_INVALID");
   keys.add(row.key);rows.push(row);
 };
 for(const a of accepted){
  const eligible=a.phaseOfPivotalEvidence>=3;
  add({key:a.applicationKey,ticker:cogentTicker,drug:a.drug,
   indication:a.indication,kind:"ACCEPTED_NDA_SOURCE",
   eligible:eligible?"PHASE3_SOURCE_ELIGIBLE":"PHASE2_EXCLUDED",
   targetDate:a.pdufaTargetDate,trialNctId:a.trialNctId,trialName:a.trialName,
   sourceUrl:a.applicationAcceptedSourceUrl,outcomeEvidenceUrl:a.outcomeEvidenceUrl,
   decision:"ABSTAIN",probabilities:baseline(),
   blockers:eligible?[
    "No independently validated complete 30/30 RAAS stage score",
    "No frozen, calibrated PASS / CRL / EXTENSION probabilities",
    "FDA review-cycle outcome, safety and manufacturing review not independently adjudicated"
   ]:[
    "Pivotal study is Phase 2; excluded by the minimum Phase 3 eligibility rule",
    "No frozen, validated three-way FDA prediction for this separate application"
   ]});
 }
 for(const a of leads){
  add({key:a.legacyCaseKey,ticker:a.ticker,drug:a.drug,
   indication:"Application-specific indication must be reconciled",kind:"ISSUER_GOAL_LEAD",
   eligible:"NOT_YET_VERIFIED",targetDate:a.legacyGoalDate,
   trialNctId:null,trialName:null,sourceUrl:a.issuerSourceUrl,
   outcomeEvidenceUrl:null,decision:"ABSTAIN",probabilities:baseline(),
   blockers:[
    ...(!a.sourceDocumentLocated?["Contemporaneous issuer goal source missing"]:[]),
    ...(!a.applicationNumberIndependentlyVerified?["Exact FDA application number not independently verified"]:[]),
    ...(!a.exactReviewCycleIndependentlyVerified?["Original review cycle not independently verified"]:[]),
    ...(!a.prospectivelyFrozenThreeWayProbabilities?["No independently frozen three-way forecast"]:[]),
    "Phase 3, current issuer capitalization and Pipeline eligibility not certified in this lead",
    ...(a.formalGoalRevision?[
      "A formal date revision exists; revised "+a.formalGoalRevision.revisedGoalDate+
      " must not be treated as a new original-cycle forecast"
    ]:[])
   ]});
 }
 return rows.sort((a,b)=>a.targetDate.localeCompare(b.targetDate)||a.ticker.localeCompare(b.ticker)||a.key.localeCompare(b.key));
}
export function summarizeRaasPredictionQueue(rows:readonly FDAPredictionQueueItem[]){
 return {total:rows.length,
  phase3SourceEligible:rows.filter(r=>r.eligible==="PHASE3_SOURCE_ELIGIBLE").length,
  phase2Excluded:rows.filter(r=>r.eligible==="PHASE2_EXCLUDED").length,
  researchLeadsUnverified:rows.filter(r=>r.eligible==="NOT_YET_VERIFIED").length,
  certifiedThreeWayForecasts:0 as const,
  allAbstain:rows.every(r=>r.decision==="ABSTAIN"&&
   r.probabilities.PASS===null&&r.probabilities.CRL===null&&r.probabilities.EXTENSION===null)};
}
