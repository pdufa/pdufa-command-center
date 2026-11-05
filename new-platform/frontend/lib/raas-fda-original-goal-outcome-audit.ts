/** A quarantined FDA original-goal outcome evidence queue, NOT adjudicated labels.
 * Require exact FDA application/review-cycle identity and separately verify
 * outcome effective dates against the FIRST goal, even after a revised date.
 * Never feed these postdecision sources into a predecision RAAS forecast.
 */
import {buildThreeWayFDAFreezePreflightPlan,
 type ThreeWayFDAFreezePreflight} from "./raas-fda-three-way-freeze-preflight";
import {currentRaasFdaForecastFreezeReceiptAudit}
 from "./raas-fda-forecast-freeze-receipt-audit";
import saved from "../data/raas-fda-original-goal-outcome-candidates.json";

export type RaasFdaClaimedOriginalGoalOutcome="PASS"|"CRL"|"EXTENSION";
export type RaasFdaOutcomeCandidate={
 evidenceId:string;caseKey:string;sourceFingerprint:string;
 ticker:string;drug:string;indication:string;trialNctId:string|null;
 firstAnnouncedGoalDate:string;
 exactFdaApplicationNumber:string;exactReviewCycleId:string;
 claimedOriginalGoalOutcome:RaasFdaClaimedOriginalGoalOutcome;
 claimedActionEffectiveDate:string;sourcePublishedDate:string;capturedAt:string;
 sourceType:"FDA_PRIMARY"|"SEC_FILING"|"SPONSOR_DISCLOSURE";
 sourceUrl:string;sourceDocumentSha256:string;
 independentAdjudicationArchiveReference:string|null;
};
export type RaasFdaOutcomeCandidateFeed={
 schemaVersion:1;
 scope:"RAAS_FDA_ORIGINAL_GOAL_OUTCOME_EVIDENCE_CANDIDATES_UNADJUDICATED";
 note:string;records:RaasFdaOutcomeCandidate[];
};
export type RaasFdaOutcomeCaseAudit={
 caseKey:string;ticker:string;drug:string;indication:string;
 originalFirstGoalDate:string;listedTargetDate:string;
 stageEligibility:"PHASE3_SOURCE_ELIGIBLE"|"PHASE2_EXCLUDED"|"NOT_YET_VERIFIED";
 status:"NOT_SUBMITTED"|"BLOCKED_SOURCE_CANDIDATE"|
  "PENDING_INDEPENDENT_ADJUDICATION";
 pendingEvidenceIds:string[];blockers:string[];
 recordedEvidenceCount:number;
 verifiedOriginalGoalLabel:null;
 verifiedOriginalGoalActionDate:null;
 authenticatedPredecisionForecast:null;
 accuracyPairQualified:false;
};
export type RaasFdaOriginalGoalOutcomeAudit={
 scope:"RAAS_FDA_ORIGINAL_GOAL_OUTCOME_INDEPENDENT_ADJUDICATION_QUEUE";
 snapshotAsOf:string;
 exactReviewCycleResearchCases:number;
 pendingNoEvidence:number;
 blockedResearchCases:number;
 pendingIndependentAdjudication:number;
 submittedResearchEvidenceRecords:number;
 authenticatedPredecisionForecasts:0;
 independentlyAdjudicatedOriginalGoalLabels:0;
 qualifiedForecastOutcomePairs:0;
 independentThreeWayAccuracy:null;
 cases:RaasFdaOutcomeCaseAudit[];
 warning:string;
};
const day=(v:unknown):v is string=>
 typeof v==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&
 Number.isFinite(Date.parse(v+"T00:00:00Z"))&&
 new Date(v+"T00:00:00Z").toISOString().slice(0,10)===v;
const instant=(v:unknown):v is string=>
 typeof v==="string"&&
 /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$/.test(v)&&
 Number.isFinite(Date.parse(v));
const hex=(v:unknown):v is string=>
 typeof v==="string"&&/^[a-f0-9]{64}$/.test(v);
const valid=(v:unknown,min:number,max:number):v is string=>
 typeof v==="string"&&v.trim().length>=min&&v.length<=max&&
 !/[\u0000-\u001f\u007f]/.test(v);
const same=(a:unknown,b:string)=>typeof a==="string"&&
 a.trim().toLowerCase()===b.trim().toLowerCase();
const count=(xs:string[])=>xs.reduce((m,x)=>{
 m.set(x,(m.get(x)||0)+1);return m;
},new Map<string,number>());
const fdaPrimary=(value:unknown)=>
 typeof value==="string"&&
 /^https:\/\/(?:www\.|accessdata\.)fda\.gov\//i.test(value);
const secPrimary=(value:unknown)=>
 typeof value==="string"&&
 /^https:\/\/(?:www\.)?sec\.gov\//i.test(value);
/** Structural intake only. A real independent outcome review must separately
 * inspect official FDA letters, action dates, amendment chronology, and cycle.
 */
export function auditRaasFdaOriginalGoalOutcomes(
 raw:unknown,
 plan=buildThreeWayFDAFreezePreflightPlan()
):RaasFdaOriginalGoalOutcomeAudit{
 const feed=raw as RaasFdaOutcomeCandidateFeed;
 if(!feed||feed.schemaVersion!==1||
  feed.scope!=="RAAS_FDA_ORIGINAL_GOAL_OUTCOME_EVIDENCE_CANDIDATES_UNADJUDICATED"||
  !valid(feed.note,30,4000)||!Array.isArray(feed.records)||
  feed.records.length>50000||plan.records.length!==plan.total||
  new Set(plan.records.map(x=>x.caseKey)).size!==plan.total)
  throw Error("RAAS_FDA_ORIGINAL_GOAL_OUTCOME_FEED_INVALID");
 const byCase=new Map<string,ThreeWayFDAFreezePreflight>(
  plan.records.map(x=>[x.caseKey,x]));
 const idCount=count(feed.records.map(x=>typeof x?.evidenceId==="string"?
  x.evidenceId:""));
 const byKey=new Map<string,RaasFdaOutcomeCandidate[]>();
 for(const r of feed.records){
  const key=typeof r?.caseKey==="string"?r.caseKey:"";
  const rows=byKey.get(key)??[];rows.push(r);byKey.set(key,rows);
 }
 const cases=plan.records.map((item):RaasFdaOutcomeCaseAudit=>{
  const records=byKey.get(item.caseKey)??[];
  const blockers:string[]=[];
  if(item.eligibility==="PHASE2_EXCLUDED")
   blockers.push("PHASE2_EXCLUDED_FROM_PHASE3_PIPELINE");
  if(item.eligibility==="NOT_YET_VERIFIED")
   blockers.push("UNVERIFIED_APPLICATION_CYCLE_AND_PIPELINE_ELIGIBILITY");
  if(!records.length)blockers.push("NO_ORIGINAL_GOAL_OUTCOME_EVIDENCE_SUBMITTED");
  if(records.length>1)blockers.push("MULTIPLE_OUTCOME_CANDIDATES_REQUIRE_CYCLE_RECONCILIATION");
  for(const r of records){
   if(!r||!valid(r.evidenceId,8,150)||idCount.get(r.evidenceId)!==1)
    blockers.push("INVALID_OR_DUPLICATE_EVIDENCE_ID");
   if(r?.sourceFingerprint!==item.sourceFingerprint||
    !same(r?.ticker,item.ticker)||!same(r?.drug,item.drug)||
    !same(r?.indication,item.indication)||
    r?.trialNctId!==item.trialNctId||
    r?.firstAnnouncedGoalDate!==item.originalFirstGoalDate)
    blockers.push("EXACT_APPLICATION_SOURCE_OR_ORIGINAL_GOAL_MISMATCH");
   if(!valid(r?.exactFdaApplicationNumber,5,120)||
      !valid(r?.exactReviewCycleId,5,120))
    blockers.push("EXACT_FDA_APPLICATION_OR_REVIEW_CYCLE_UNVERIFIED");
   if(!["PASS","CRL","EXTENSION"].includes(r?.claimedOriginalGoalOutcome))
    blockers.push("INVALID_FDA_ORIGINAL_GOAL_LABEL");
   if(!day(r?.claimedActionEffectiveDate)||!day(r?.sourcePublishedDate)||
      !instant(r?.capturedAt))
    blockers.push("INVALID_ACTION_OR_EVIDENCE_TIMING");
   else {
    if(r.claimedActionEffectiveDate>r.sourcePublishedDate||
       Date.parse(r.capturedAt)<Date.parse(r.sourcePublishedDate+"T00:00:00Z"))
     blockers.push("ACTION_SOURCE_OR_CAPTURE_CHRONOLOGY_INCONSISTENT");
    if(r.claimedActionEffectiveDate>item.originalFirstGoalDate)
     blockers.push("AFTER_ORIGINAL_GOAL_ACTION_NOT_AUTOMATIC_ORIGINAL_DISPOSITION");
    if(r.claimedOriginalGoalOutcome==="EXTENSION"&&
       r.claimedActionEffectiveDate>item.originalFirstGoalDate)
     blockers.push("EXTENSION_NOT_CONFIRMED_BEFORE_ORIGINAL_GOAL");
   }
   if(r?.sourceType==="FDA_PRIMARY"){
    if(!fdaPrimary(r?.sourceUrl))
     blockers.push("FDA_PRIMARY_SOURCE_HOST_MISMATCH");
   }else if(r?.sourceType==="SEC_FILING"){
    if(!secPrimary(r?.sourceUrl))
     blockers.push("SEC_FILING_SOURCE_HOST_MISMATCH");
    blockers.push("SEC_FILING_NEEDS_INDEPENDENT_FDA_CYCLE_CONFIRMATION");
   }else if(r?.sourceType==="SPONSOR_DISCLOSURE"){
    if(!valid(r?.sourceUrl,12,1200)||
       !r.sourceUrl.startsWith("https://"))
     blockers.push("INVALID_SPONSOR_SOURCE_URL");
    blockers.push("SPONSOR_CLAIM_NEEDS_PRIMARY_FDA_CYCLE_CONFIRMATION");
   }else blockers.push("UNRECOGNIZED_FDA_SOURCE_TYPE");
   if(!hex(r?.sourceDocumentSha256))
    blockers.push("MISSING_OR_INVALID_SOURCE_DOCUMENT_SHA256");
   if(r?.independentAdjudicationArchiveReference!==null&&
      !valid(r?.independentAdjudicationArchiveReference,16,500))
    blockers.push("INVALID_PRIVATE_ADJUDICATION_ARCHIVE_REFERENCE");
  }
  const uniq=[...new Set(blockers)];
  // The presence of any submission never automatically verifies an outcome.
  const status:RaasFdaOutcomeCaseAudit["status"]=!records.length?
   "NOT_SUBMITTED":uniq.length?"BLOCKED_SOURCE_CANDIDATE":
   "PENDING_INDEPENDENT_ADJUDICATION";
  return {caseKey:item.caseKey,ticker:item.ticker,drug:item.drug,
   indication:item.indication,originalFirstGoalDate:item.originalFirstGoalDate,
   listedTargetDate:item.listedTargetDate,stageEligibility:item.eligibility,
   status,pendingEvidenceIds:records.map(r=>r?.evidenceId??"INVALID"),
   blockers:uniq,recordedEvidenceCount:records.length,
   verifiedOriginalGoalLabel:null,verifiedOriginalGoalActionDate:null,
   authenticatedPredecisionForecast:null,accuracyPairQualified:false};
 });
 // Unknown/orphaned rows must fail globally, never disappear off the board.
 const unknown=[...byKey.keys()].filter(key=>!byCase.has(key));
 if(unknown.length)throw Error("RAAS_FDA_ORIGINAL_GOAL_UNKNOWN_CASE_REFERENCE");
 const receiptAudit=currentRaasFdaForecastFreezeReceiptAudit();
 if(receiptAudit.independentlyAuthenticatedForecasts!==0)
  throw Error("RAAS_FDA_OUTCOME_PROSPECTIVE_AUTHENTICATION_SOURCE_UNEXPECTED");
 return {scope:"RAAS_FDA_ORIGINAL_GOAL_OUTCOME_INDEPENDENT_ADJUDICATION_QUEUE",
  snapshotAsOf:plan.snapshotAsOf,exactReviewCycleResearchCases:cases.length,
  pendingNoEvidence:cases.filter(x=>x.status==="NOT_SUBMITTED").length,
  blockedResearchCases:cases.filter(x=>x.status==="BLOCKED_SOURCE_CANDIDATE").length,
  pendingIndependentAdjudication:cases.filter(x=>x.status==="PENDING_INDEPENDENT_ADJUDICATION").length,
  submittedResearchEvidenceRecords:feed.records.length,
  authenticatedPredecisionForecasts:0,independentlyAdjudicatedOriginalGoalLabels:0,
  qualifiedForecastOutcomePairs:0,independentThreeWayAccuracy:null,cases,
  warning:"This saved research audit does not verify that FDA took an action, certify an original-goal outcome, prove a prospective forecast freeze, or validate three-way accuracy. A later eventual approval is not retroactively a PASS at the original goal."};
}
export function currentRaasFdaOriginalGoalOutcomeAudit(){
 return auditRaasFdaOriginalGoalOutcomes(saved);
}
