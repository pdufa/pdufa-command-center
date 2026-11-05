/** Unsigned, exact-application FDA PASS / CRL / EXTENSION forecast preflight.
 * This is a candidate intake plan, never an authenticated forecast, a
 * backdated prediction, a calibrated probability, or an order to trade.
 */
import {createHash} from "node:crypto";
import {buildRaasPredictionQueue,type FDAPredictionQueueItem}
 from "./raas-prediction-queue";
import accepted from "../data/raas-current-accepted-fda-applications.json";
import leads from "../data/raas-v2-top8-2026-source-intake.json";
import accuracy from "../data/raas-fda-three-way-accuracy-site-snapshot.json";

type Status="PHASE2_OUT_OF_SCOPE"|"ORIGINAL_GOAL_ALREADY_ELAPSED"|
 "UNVERIFIED_APPLICATION_OR_REVIEW_CYCLE"|"EXACT_CYCLE_AND_CALIBRATION_NOT_VERIFIED";
type EvidenceRequirement={
 id:string;label:string;status:"SOURCE_LEAD_NOT_CERTIFIED"|"MISSING"|"OUT_OF_SCOPE";
 note:string
};
export type ThreeWayFDAFreezePreflight={
 schemaVersion:1;
 scope:"RAAS_FDA_ORIGINAL_GOAL_THREE_WAY_FREEZE_PREFLIGHT_UNSIGNED";
 caseKey:string;ticker:string;drug:string;indication:string;
 kind:FDAPredictionQueueItem["kind"];
 eligibility:FDAPredictionQueueItem["eligible"];
 snapshotAsOf:string;
 originalFirstGoalDate:string;listedTargetDate:string;
 goalHasFormalRevision:boolean;
 formalRevisedGoalDate:string|null;
 trialNctId:string|null;trialName:string|null;
 primaryIssuerSourceUrl:string;
 preflightStatus:Status;
 requiredProof:EvidenceRequirement[];
 sourceFingerprint:string;
 forecastReceiptDraft:{
  sourceFingerprint:string;exactApplicationNumber:null;reviewCycleId:null;
  sourceSnapshotAsOf:string;forecastFrozenAt:null;
  firstAnnouncedGoalDate:string;exactNctId:string|null;
  probabilities:{PASS:null;CRL:null;EXTENSION:null};
  modelVersion:null;calibrationReportReference:null;
  independentSourceAuditReference:null;
  signedFreezeReceiptDigest:null;
 };
 verifiedThreeWayForecast:null;approvedRaasGrade:null;
 releaseStatus:"ABSTAIN_NO_FORECAST_FROZEN";
 warnings:string[];
};
export type ThreeWayFDAFreezePreflightPlan={
 scope:"RAAS_UNAPPROVED_FDA_THREE_WAY_FREEZE_HANDOFF_PLAN";
 snapshotAsOf:string;total:number;phase2Excluded:number;
 originalGoalElapsed:number;unverifiedApplicationOrCycle:number;
 needsExactCycleAndCalibration:number;
 frozenVerifiedThreeWayForecasts:0;certifiedThreeWayAccuracy:null;
 records:ThreeWayFDAFreezePreflight[];
};
const iso=(d:string)=>/^\d{4}-\d{2}-\d{2}$/.test(d)&&
 !Number.isNaN(Date.parse(d+"T00:00:00Z"))&&
 new Date(d+"T00:00:00Z").toISOString().slice(0,10)===d;
const sha256=(s:string)=>createHash("sha256").update(s,"utf8").digest("hex");

export function buildThreeWayFDAFreezePreflightPlan(
 sourceAsOf=accepted.sourceAsOf
):ThreeWayFDAFreezePreflightPlan{
 if(!iso(sourceAsOf)||sourceAsOf<accepted.sourceAsOf||
  sourceAsOf<leads.asOf||accuracy.scope!==
   "RAAS_FDA_THREE_WAY_DECISION_ACCURACY_SITE_SNAPSHOT"||
  accuracy.predecisionThreeWayIndependentlyVerifiedForecasts!==0||
  accuracy.approvedRaasMetricCalibrations!==0)
  throw Error("RAAS_FDA_PREFLIGHT_BASELINE_NOT_VERIFIED");
 const queue=buildRaasPredictionQueue(
  accepted.applications,leads.records,accepted.issuer.ticker);
 const sourceKeys=new Set<string>();
 const acceptedByKey=new Map(accepted.applications.map(x=>[x.applicationKey,x]));
 const leadsByKey=new Map(leads.records.map(x=>[x.legacyCaseKey,x]));
 const records=queue.map((row):ThreeWayFDAFreezePreflight=>{
  if(sourceKeys.has(row.key))throw Error("RAAS_FDA_PREFLIGHT_DUPLICATE_CASE");
  sourceKeys.add(row.key);
  const a=acceptedByKey.get(row.key),l=leadsByKey.get(row.key);
  if(!!a===!!l||a&&row.kind!=="ACCEPTED_NDA_SOURCE"||
   l&&row.kind!=="ISSUER_GOAL_LEAD")
   throw Error("RAAS_FDA_PREFLIGHT_AMBIGUOUS_CASE_ORIGIN");
  const originalGoal=a?.pdufaTargetDate??l!.firstCycleGoalDate;
  const formalRevision=l?.formalGoalRevision??null;
  if(!iso(originalGoal)||formalRevision&&
   (!iso(formalRevision.revisedGoalDate)||
    !iso(formalRevision.firstPublicDate)||
    formalRevision.revisedGoalDate!==l!.legacyGoalDate||
    formalRevision.revisedGoalDate<=originalGoal)||
   row.decision!=="ABSTAIN"||
   Object.values(row.probabilities).some(x=>x!==null))
   throw Error("RAAS_FDA_PREFLIGHT_FORECAST_OR_DATE_INCONSISTENT");
  const deadlineElapsed=originalGoal<=sourceAsOf;
  const originalDateStatus:EvidenceRequirement["status"]=
   deadlineElapsed?"OUT_OF_SCOPE":"SOURCE_LEAD_NOT_CERTIFIED";
  const requiredProof:EvidenceRequirement[]=[
   {id:"original-goal",
    label:"First publicly announced original PDUFA goal preserved, never replaced by revision",
    status:originalDateStatus,
    note:deadlineElapsed?
     "The original goal already elapsed by the saved source date; prospective freeze now would be look-ahead / backdating.":
     "Verify the earliest contemporaneous goal announcement and its exact FDA review cycle."},
   {id:"exact-fda-application-cycle",
    label:"Regulator-matched application number, indication, sponsor and exact review cycle",
    status:"MISSING",
    note:"Sponsor acceptance or internal applicationKey is not independently verified FDA NDA/BLA/supplement identity."},
   {id:"minimum-phase3-evidence",
    label:"Independently source the user's minimum Phase 3 program eligibility",
    status:row.eligible==="PHASE2_EXCLUDED"?"OUT_OF_SCOPE":
     row.eligible==="PHASE3_SOURCE_ELIGIBLE"?"SOURCE_LEAD_NOT_CERTIFIED":"MISSING",
    note:row.eligible==="PHASE2_EXCLUDED"?
     "Phase 2 pivotal record excluded; do not treat acceptance as Phase 3.":
     "Phase 3 source alone does not establish current market-cap or accepted FDA cycle."},
   {id:"30-authenticated-stage-metrics",
    label:"Complete 30 of 30 independently authenticated stage metrics",
    status:"MISSING",
    note:"Partial source-reviewed research ratings are not validated final RAAS metrics."},
   {id:"approved-three-way-model",
    label:"Independent chronologically held-out PASS/CRL/EXTENSION calibration",
    status:"MISSING",
    note:"Require outcomes including extensions, predeclared classes, baseline comparisons, and independent metrics."},
   {id:"immutable-predecision-receipt",
    label:"Timestamped, externally attributable three-class probability freeze before original deadline",
    status:deadlineElapsed?"OUT_OF_SCOPE":"MISSING",
    note:"No probabilities or signature are available; never reconstruct them after a decision."},
   {id:"independent-original-goal-outcome",
    label:"Independently adjudicated original-goal outcome for later scoring",
    status:"MISSING",
    note:"Outcome requires separate official evidence; not a preforecast input."}
  ];
  const preflightStatus:Status=row.eligible==="PHASE2_EXCLUDED"?
   "PHASE2_OUT_OF_SCOPE":deadlineElapsed?
   "ORIGINAL_GOAL_ALREADY_ELAPSED":
   row.eligible==="NOT_YET_VERIFIED"?
   "UNVERIFIED_APPLICATION_OR_REVIEW_CYCLE":
   "EXACT_CYCLE_AND_CALIBRATION_NOT_VERIFIED";
  const identity={
   version:"raas-fda-original-goal-preflight-2026-11-04-v1",
   key:row.key,ticker:row.ticker,drug:row.drug,indication:row.indication,
   kind:row.kind,eligible:row.eligible,trialNctId:row.trialNctId,
   firstGoal:originalGoal,listedTarget:row.targetDate,
   formalRevision:formalRevision?.revisedGoalDate??null,
   issuerSource:row.sourceUrl,snapshotAsOf:sourceAsOf,
   requiredProof
  };
  const fingerprint=sha256(JSON.stringify(identity));
  return {
   schemaVersion:1,scope:"RAAS_FDA_ORIGINAL_GOAL_THREE_WAY_FREEZE_PREFLIGHT_UNSIGNED",
   caseKey:row.key,ticker:row.ticker,drug:row.drug,indication:row.indication,
   kind:row.kind,eligibility:row.eligible,
   snapshotAsOf:sourceAsOf,originalFirstGoalDate:originalGoal,
   listedTargetDate:row.targetDate,
   goalHasFormalRevision:formalRevision!==null,
   formalRevisedGoalDate:formalRevision?.revisedGoalDate??null,
   trialNctId:row.trialNctId,trialName:row.trialName,
   primaryIssuerSourceUrl:row.sourceUrl,
   preflightStatus,requiredProof,sourceFingerprint:fingerprint,
   forecastReceiptDraft:{
    sourceFingerprint:fingerprint,exactApplicationNumber:null,reviewCycleId:null,
    sourceSnapshotAsOf:sourceAsOf,forecastFrozenAt:null,
    firstAnnouncedGoalDate:originalGoal,exactNctId:row.trialNctId,
    probabilities:{PASS:null,CRL:null,EXTENSION:null},
    modelVersion:null,calibrationReportReference:null,
    independentSourceAuditReference:null,signedFreezeReceiptDigest:null
   },
   verifiedThreeWayForecast:null,approvedRaasGrade:null,
   releaseStatus:"ABSTAIN_NO_FORECAST_FROZEN",
   warnings:[
    ...row.blockers,
    "This handoff is an unsigned evidence checklist, not an externally stored or verified prospective forecast.",
    "No numerical FDA PASS/CRL/EXTENSION probability or investment decision is authorized."
   ]
  };
 });
 if(records.length!==accepted.applications.length+leads.records.length||
  records.some(r=>r.requiredProof.length!==7))
  throw Error("RAAS_FDA_PREFLIGHT_ROSTER_MISMATCH");
 return {scope:"RAAS_UNAPPROVED_FDA_THREE_WAY_FREEZE_HANDOFF_PLAN",
  snapshotAsOf:sourceAsOf,total:records.length,
  phase2Excluded:records.filter(r=>r.preflightStatus==="PHASE2_OUT_OF_SCOPE").length,
  originalGoalElapsed:records.filter(r=>
   r.preflightStatus==="ORIGINAL_GOAL_ALREADY_ELAPSED").length,
  unverifiedApplicationOrCycle:records.filter(r=>
   r.preflightStatus==="UNVERIFIED_APPLICATION_OR_REVIEW_CYCLE").length,
  needsExactCycleAndCalibration:records.filter(r=>
   r.preflightStatus==="EXACT_CYCLE_AND_CALIBRATION_NOT_VERIFIED").length,
  frozenVerifiedThreeWayForecasts:0,certifiedThreeWayAccuracy:null,records
 };
}
