/** Read-only, unauthenticated forecast-freeze receipt *intake* audit.
 * A well-formed receipt is NOT a verified predecision freeze or calibrated
 * FDA forecast: the claimed timestamp, issuer, review cycle, source, model
 * independence and signed artifact require external verification.
 *
 * Never turn candidate receipt probability fields into trading guidance or
 * validated accuracy measurements. A public repository is not a witness.
 */
import {buildThreeWayFDAFreezePreflightPlan,
 type ThreeWayFDAFreezePreflight} from "./raas-fda-three-way-freeze-preflight";
import receiptData from "../data/raas-fda-forecast-freeze-receipts.json";

export type RaasFdaForecastFreezeReceipt={
 receiptId:string;caseKey:string;sourceFingerprint:string;
 ticker:string;drug:string;indication:string;
 trialNctId:string|null;firstAnnouncedGoalDate:string;
 sourceSnapshotAsOf:string;
 exactFdaApplicationNumber:string;exactReviewCycleId:string;
 forecastFrozenAt:string;independentWitnessRecordedAt:string;
 witnessArchiveReference:string;signedArtifactSha256:string;
 modelVersion:string;calibrationReportReference:string;
 independentSourceAuditReference:string;
 probabilities:{PASS:number;CRL:number;EXTENSION:number};
};
export type RaasFdaForecastFreezeFeed={
 schemaVersion:1;
 scope:"RAAS_FDA_FORECAST_FREEZE_RECEIPTS_UNAUTHENTICATED_INTAKE";
 note:string;
 records:RaasFdaForecastFreezeReceipt[];
};
export type RaasFdaForecastFreezeReceiptCheck={
 receiptId:string;caseKey:string;
 status:"INTAKE_COMPLETE_PENDING_INDEPENDENT_AUTHENTICATION"|"BLOCKED";
 reasons:string[];
};
export type RaasFdaForecastFreezeReceiptAudit={
 scope:"RAAS_FDA_THREE_WAY_FREEZE_RECEIPT_INTAKE_AUDIT";
 eligibleResearchCaseLeads:number;
 submitted:number;
 pendingIndependentAuthentication:number;
 blocked:number;
 duplicateCaseReceipts:number;
 independentlyAuthenticatedForecasts:0;
 validatedFdaThreeWayAccuracy:null;
 approvedTradingSignals:0;
 checks:RaasFdaForecastFreezeReceiptCheck[];
 note:string;
};
const sha=(x:unknown):x is string=>
 typeof x==="string"&&/^[a-f0-9]{64}$/.test(x);
const nonempty=(x:unknown,min=1,max=1000)=>
 typeof x==="string"&&x.trim().length>=min&&x.length<=max;
const iso=(d:unknown):d is string=>
 typeof d==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(d)&&
 !Number.isNaN(Date.parse(d+"T00:00:00Z"))&&
 new Date(d+"T00:00:00Z").toISOString().slice(0,10)===d;
/** An absolute instant with an explicit timezone, never a loose local date. */
const instant=(v:unknown):v is string=>
 typeof v==="string"&&
 /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$/.test(v)&&
 Number.isFinite(Date.parse(v));
const equal=(x:unknown,y:string)=>
 typeof x==="string"&&x.trim().toLowerCase()===y.trim().toLowerCase();
const finiteProbability=(n:unknown):n is number=>
 typeof n==="number"&&Number.isFinite(n)&&n>=0&&n<=1;
const count=(values:readonly string[]):Map<string,number>=>{
 const out=new Map<string,number>();
 for(const value of values)out.set(value,(out.get(value)??0)+1);
 return out;
};
export function auditRaasFdaForecastFreezeReceipts(
 feed:unknown,
 plan=buildThreeWayFDAFreezePreflightPlan()
):RaasFdaForecastFreezeReceiptAudit{
 const doc=feed as RaasFdaForecastFreezeFeed;
 if(!doc||doc.schemaVersion!==1||
  doc.scope!=="RAAS_FDA_FORECAST_FREEZE_RECEIPTS_UNAUTHENTICATED_INTAKE"||
  !Array.isArray(doc.records)||doc.records.length>50000||
  !nonempty(doc.note,20,4000)||
  plan.records.length!==plan.total||
  new Set(plan.records.map(r=>r.caseKey)).size!==plan.total)
  throw Error("RAAS_FDA_FREEZE_RECEIPT_LEDGER_INVALID");
 const byCase=new Map<string,ThreeWayFDAFreezePreflight>(
  plan.records.map(r=>[r.caseKey,r]));
 const idCounts=count(doc.records.map(r=>typeof r?.receiptId==="string"?
  r.receiptId:""));
 const caseCounts=count(doc.records.map(r=>typeof r?.caseKey==="string"?
  r.caseKey:""));
 const checks:RaasFdaForecastFreezeReceiptCheck[]=doc.records.map((r,i)=>{
  const reasons:string[]=[];
  const receiptId=typeof r?.receiptId==="string"?r.receiptId:"INVALID-"+i;
  const caseKey=typeof r?.caseKey==="string"?r.caseKey:"";
  const item=byCase.get(caseKey);
  if(!nonempty(receiptId,8,160)||idCounts.get(receiptId)!==1)
   reasons.push("DUPLICATE_OR_INVALID_RECEIPT_ID");
  if(caseCounts.get(caseKey)!==1)
   reasons.push("DUPLICATE_FORECAST_FOR_EXACT_CASE");
  if(!item)reasons.push("UNKNOWN_EXACT_FDA_CASE");
  else{
   if(item.eligibility==="PHASE2_EXCLUDED")
    reasons.push("PHASE2_NOT_ELIGIBLE_FOR_PHASE3_PIPELINE");
   if(item.goalHasFormalRevision&&
    item.originalFirstGoalDate!==item.listedTargetDate){
    // Original goal is authoritative for chronology even if listed date
    // was subsequently moved. Never rebase the test to the revised target.
    if(r?.firstAnnouncedGoalDate!==item.originalFirstGoalDate)
     reasons.push("REVISED_GOAL_SUBSTITUTED_FOR_ORIGINAL");
   }
   if(r?.sourceFingerprint!==item.sourceFingerprint||
     r?.sourceSnapshotAsOf!==item.snapshotAsOf)
    reasons.push("SOURCE_FINGERPRINT_OR_SNAPSHOT_MISMATCH");
   if(!equal(r?.ticker,item.ticker)||
      !equal(r?.drug,item.drug)||
      !equal(r?.indication,item.indication)||
      r?.trialNctId!==item.trialNctId||
      r?.firstAnnouncedGoalDate!==item.originalFirstGoalDate)
    reasons.push("EXACT_APPLICATION_PROGRAM_OR_ORIGINAL_GOAL_MISMATCH");
  }
  if(!nonempty(r?.exactFdaApplicationNumber,5,100)||
     !nonempty(r?.exactReviewCycleId,5,120))
   reasons.push("MISSING_VERIFIABLE_FDA_APPLICATION_AND_REVIEW_CYCLE");
  if(!iso(r?.sourceSnapshotAsOf)||!instant(r?.forecastFrozenAt)||
    !instant(r?.independentWitnessRecordedAt))
   reasons.push("INVALID_EXPLICIT_DATE_OR_WITNESS_TIMESTAMPS");
  else if(item){
   const freezeTime=Date.parse(r.forecastFrozenAt);
   const witnessedTime=Date.parse(r.independentWitnessRecordedAt);
   // Conservatively require the freeze strictly before the start of the
   // original goal DATE, not a later amended/revised deadline.
   const originalGoalStart=Date.parse(item.originalFirstGoalDate+"T00:00:00Z");
   const sourceDayStart=Date.parse(item.snapshotAsOf+"T00:00:00Z");
   if(freezeTime>=originalGoalStart||
      witnessedTime>=originalGoalStart||
      witnessedTime<freezeTime||
      freezeTime<sourceDayStart)
    reasons.push("FORECAST_OR_WITNESS_NOT_PRE_ORIGINAL_GOAL");
  }
  if(!nonempty(r?.witnessArchiveReference,16,400)||
     !sha(r?.signedArtifactSha256))
   reasons.push("MISSING_SIGNED_FORECAST_ARTIFACT_OR_INDEPENDENT_WITNESS_REFERENCE");
  if(!nonempty(r?.modelVersion,5,180)||
     !nonempty(r?.calibrationReportReference,16,500)||
     !nonempty(r?.independentSourceAuditReference,16,500))
   reasons.push("MISSING_MODEL_CALIBRATION_OR_SOURCE_AUDIT_REFERENCE");
  const probs=r?.probabilities;
  if(!probs||typeof probs!=="object"||Array.isArray(probs)||
     Object.keys(probs).sort().join("|")!=="CRL|EXTENSION|PASS"||
     !finiteProbability(probs.PASS)||
     !finiteProbability(probs.CRL)||
     !finiteProbability(probs.EXTENSION)||
     Math.abs(probs.PASS+probs.CRL+probs.EXTENSION-1)>1e-9)
   reasons.push("INVALID_THREE_CLASS_PROBABILITIES");
  return {receiptId,caseKey,
   status:reasons.length?"BLOCKED" as const:
    "INTAKE_COMPLETE_PENDING_INDEPENDENT_AUTHENTICATION" as const,
   reasons};
 });
 return {
  scope:"RAAS_FDA_THREE_WAY_FREEZE_RECEIPT_INTAKE_AUDIT",
  eligibleResearchCaseLeads:plan.records.filter(r=>
   r.eligibility!=="PHASE2_EXCLUDED").length,
  submitted:checks.length,
  pendingIndependentAuthentication:checks.filter(r=>
   r.status==="INTAKE_COMPLETE_PENDING_INDEPENDENT_AUTHENTICATION").length,
  blocked:checks.filter(r=>r.status==="BLOCKED").length,
  duplicateCaseReceipts:checks.filter(r=>
   r.reasons.includes("DUPLICATE_FORECAST_FOR_EXACT_CASE")).length,
  independentlyAuthenticatedForecasts:0,validatedFdaThreeWayAccuracy:null,
  approvedTradingSignals:0,checks,
  note:"Structural and chronology lint only. A metadata timestamp, signed digest or URL does not prove independent attestation or historical publication. No FDA forecast or model accuracy is certified here."
 };
}
export function currentRaasFdaForecastFreezeReceiptAudit(){
 return auditRaasFdaForecastFreezeReceipts(receiptData);
}
