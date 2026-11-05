/** Published FDA records for a parent NDA or another indication do not
 * prove the exact current PDUFA application cycle or disposition.
 * Historical action documentation is distinct from independent adjudication.
 */
import saved from "../data/raas-fda-historical-other-cycle-exclusions.json";
import {buildThreeWayFDAFreezePreflightPlan}
 from "./raas-fda-three-way-freeze-preflight";

export function currentRaasFdaDocumentedOtherCycleExclusions(){
 const plan=buildThreeWayFDAFreezePreflightPlan();
 if(saved.schemaVersion!==1||
  saved.scope!=="RAAS_FDA_DOCUMENTED_OTHER_INDICATION_OR_PRIOR_CYCLE_RESEARCH_EXCLUSIONS"||
  saved.records.length!==2)
  throw Error("RAAS_FDA_HISTORICAL_OTHER_CYCLE_SCHEMA_INVALID");
 const preflight=new Map(plan.records.map(x=>[x.caseKey,x]));
 const keys=new Set<string>();
 const records=saved.records.map(x=>{
  const row=preflight.get(x.caseKey);
  if(!row||keys.has(x.caseKey)||row.ticker!==x.ticker||
   row.originalFirstGoalDate!==x.originalFirstGoalDate||
   x.historicalFdaActionDate>=x.originalFirstGoalDate||
   !x.historicalFdaSourceUrl.startsWith("https://www.fda.gov/")||
   !x.targetCycleIssuerSourceUrl.startsWith("https://")||
   x.exactPendingReviewCycleIndependentlyVerified!==false||
   x.targetOriginalGoalDispositionIndependentlyAdjudicated!==false||
   x.verifiedThreeWayPrediction!==false||
   x.validHistoricalActionForTargetCycle!==false)
   throw Error("RAAS_FDA_HISTORICAL_OTHER_CYCLE_IDENTITY_MISMATCH");
  keys.add(x.caseKey);
  return {...x,originalGoalResearchSourceAsOf:plan.snapshotAsOf,
   pendingReviewCycleOutcome:"UNVERIFIED" as const,
   raasForecastRelease:"ABSTAIN" as const};
 });
 if(!keys.has("CYTK|MYQORZO_HCM_20261114")||
  !keys.has("RELACORILANT_CUSHINGS_US_20261217"))
  throw Error("RAAS_FDA_HISTORICAL_OTHER_CYCLE_EXPECTED_CASES_MISSING");
 return {
  scope:"RAAS_FDA_DOCUMENTED_OTHER_CYCLE_EXCLUSIONS_NOT_APPROVED_OUTCOMES" as const,
  historicalSourceReviewedAsOf:saved.sourceReviewedAsOf,
  documentedOtherCycleExclusions:records.length,
  independentlyMatchedCurrentReviewCycles:0,
  independentlyAdjudicatedUpcomingFdaOutcomes:0,
  qualifiedForecastOutcomePairs:0,
  records,
  warning:"A published FDA approval for another indication or the parent original NDA cannot verify a later review, pending supplement, extension or future PDUFA disposition. Historical evidence is not prospective FDA prediction evidence."
 };
}
