"use strict";

// Permanent retirement: no historical artifact writer may execute as a command.
if (require.main === module) { process.stderr.write("RAAS_PERMANENTLY_RETIRED: this archived command cannot run or modify historical records.\n"); process.exit(78); }

/** Read-only as-of FDA PASS/CRL/EXTENSION readiness artifact for the EXISTING
 * scheduled RAAS FDA accuracy workflow. Never adds hypothetical forecasts,
 * adjudicates an outcome, submits an order, or claims a live FDA lookup.
 */
const fs=require("node:fs"),path=require("node:path");
const {createHash}=require("node:crypto");
const ts=require("typescript");
const {compareNightlyReports}=require("./raas-fda-nightly-compare.cjs");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  esModuleInterop:true}}).outputText,file);
const {buildThreeWayFDAFreezePreflightPlan}=
 require("../lib/raas-fda-three-way-freeze-preflight.ts");
const {currentRaasFdaForecastFreezeReceiptAudit}=
 require("../lib/raas-fda-forecast-freeze-receipt-audit.ts");
const {currentRaasFdaOriginalGoalOutcomeAudit}=
 require("../lib/raas-fda-original-goal-outcome-audit.ts");
const {currentRaasFdaThreeWayResearchScorecard}=
 require("../lib/raas-fda-three-way-research-scorecard.ts");

const day=s=>/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 !Number.isNaN(Date.parse(s+"T00:00:00Z"))&&
 new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const days=(to,from)=>(Date.parse(to+"T00:00:00Z")-
 Date.parse(from+"T00:00:00Z"))/86400000;
const digest=o=>createHash("sha256").update(JSON.stringify(o)).digest("hex");
const ordered=x=>[...x].sort((a,b)=>a.caseKey.localeCompare(b.caseKey));

function buildNightlyRaasFdaAudit(asOfInstant){
 if(typeof asOfInstant!=="string"||
  !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$/.test(asOfInstant)||
  !Number.isFinite(Date.parse(asOfInstant)))
  throw Error("RAAS_FDA_NIGHTLY_EXPLICIT_UTC_INSTANT_REQUIRED");
 const instant=new Date(asOfInstant).toISOString();
 const asOfDay=instant.slice(0,10);
 const plan=buildThreeWayFDAFreezePreflightPlan();
 if(!day(plan.snapshotAsOf)||asOfDay<plan.snapshotAsOf)
  throw Error("RAAS_FDA_NIGHTLY_SNAPSHOT_FROM_FUTURE");
 const forecast=currentRaasFdaForecastFreezeReceiptAudit();
 const outcome=currentRaasFdaOriginalGoalOutcomeAudit();
 const score=currentRaasFdaThreeWayResearchScorecard();
 const byOutcome=new Map(outcome.cases.map(x=>[x.caseKey,x]));
 if(plan.total!==outcome.exactReviewCycleResearchCases||
  plan.records.length!==outcome.cases.length||
  plan.total!==score.researchRosterCases+plan.phase2Excluded||
  score.researchPairedCases!==outcome.qualifiedForecastOutcomePairs||
  forecast.independentlyAuthenticatedForecasts!==0||
  outcome.independentlyAdjudicatedOriginalGoalLabels!==0||
  score.independentValidatedAccuracyPct!==null||
  score.approvedPredictionModel!==false)
  throw Error("RAAS_FDA_NIGHTLY_RECONCILIATION_FAILED");
 const receiptChecks=new Map();
 for(const check of forecast.checks){
  const arr=receiptChecks.get(check.caseKey)||[];
  receiptChecks.set(check.caseKey,[...arr,check]);
 }
 const records=ordered(plan.records).map(row=>{
  const review=byOutcome.get(row.caseKey);
  if(!review||review.originalFirstGoalDate!==row.originalFirstGoalDate||
   review.stageEligibility!==row.eligibility)
   throw Error("RAAS_FDA_NIGHTLY_CASE_IDENTITY_MISMATCH");
  const daysUntilOriginalGoal=days(row.originalFirstGoalDate,asOfDay);
  const daysSinceSavedSnapshot=days(asOfDay,row.snapshotAsOf);
  const originalGoalElapsed=daysUntilOriginalGoal<=0;
  const phase2Excluded=row.eligibility==="PHASE2_EXCLUDED";
  const reviewBlocked=row.eligibility==="NOT_YET_VERIFIED";
  const receipts=receiptChecks.get(row.caseKey)||[];
  const status=phase2Excluded?"PHASE2_EXCLUDED":
   originalGoalElapsed?"ORIGINAL_GOAL_ELAPSED_NO_RETROACTIVE_FORECAST":
   reviewBlocked?"EXACT_FDA_REVIEW_CYCLE_UNVERIFIED":
   "STAGE3_SOURCE_ONLY_MODEL_UNVALIDATED";
  const requiredProofMissing=row.requiredProof.filter(x=>
   x.status!=="VERIFIED").map(x=>x.id);
  return {
   caseKey:row.caseKey,ticker:row.ticker,drug:row.drug,
   indication:row.indication,trialNctId:row.trialNctId,
   phase3SourceEligibility:row.eligibility,
   originalFirstGoalDate:row.originalFirstGoalDate,
   listedTargetDate:row.listedTargetDate,
   formalGoalRevisionPresent:row.goalHasFormalRevision,
   daysUntilOriginalGoal,
   savedSnapshotAsOf:row.snapshotAsOf,
   daysSinceSavedSnapshot,
   savedSourceSnapshotStaleOver30Days:daysSinceSavedSnapshot>30,
   sourceFingerprint:row.sourceFingerprint,
   sourceUrl:row.primaryIssuerSourceUrl,
   status,
   decision:"ABSTAIN",
   claimedValidatedProbability:null,
   verifiedPredecisionForecast:null,
   independentlyAdjudicatedOutcome:null,
   researchReceiptCount:receipts.length,
   structurallyCompleteReceiptCount:receipts.filter(x=>x.status===
    "INTAKE_COMPLETE_PENDING_INDEPENDENT_AUTHENTICATION").length,
   blockedReceiptCount:receipts.filter(x=>x.status==="BLOCKED").length,
   outcomeSourceCandidateCount:review.recordedEvidenceCount,
   outcomeReviewState:review.status,
   outstandingEvidenceProofIds:requiredProofMissing,
   forecastOutcomePairQualified:false,
   nextAction:phase2Excluded?
    "Keep excluded: pivotal evidence is Phase 2, below Phase 3 minimum.":
    originalGoalElapsed?
    "Reconcile original FDA goal from primary sources; do NOT create a late forecast.":
    reviewBlocked?
    "Verify exact numbered NDA/BLA/supplement and original goal; authenticate independent source before a forecast is possible.":
    "Independently verify FDA cycle and source clocks; complete and validate 30/30 stage scores and prospective model before issuing probabilities."
  };
 });
 const total=records.length;
 const sha=digest(records.map(r=>({
  caseKey:r.caseKey,sourceFingerprint:r.sourceFingerprint,
  originalFirstGoalDate:r.originalFirstGoalDate,listedTargetDate:r.listedTargetDate,
  status:r.status,receiptCount:r.researchReceiptCount,
  outcomeCandidates:r.outcomeSourceCandidateCount
 })));
 return compareNightlyReports({
  schemaVersion:1,
  scope:"RAAS_NIGHTLY_FDA_THREE_WAY_EVIDENCE_READINESS_RESEARCH_ONLY",
  runAtUtc:instant,
  savedInputAsOf:plan.snapshotAsOf,
  auditStateFingerprint:sha,
  sourceChangedSincePreviousRun:null,
  sourceChangeComparisonStatus:"NO_PREVIOUS_RUN_ARTIFACT_PROVIDED",
  note:"Existing scheduled RAAS FDA audit, not a new scan. This report reads saved source snapshots, not live regulator data. A run success, identical hash, or lack of source candidates cannot establish actual FDA source freshness. SHA fingerprint is not a third-party timestamp or verified prediction.",
  counts:{
   researchApplicationCycles:total,
   phase2Excluded:records.filter(x=>x.status==="PHASE2_EXCLUDED").length,
   nonPhase2ResearchLeads:records.filter(x=>x.phase3SourceEligibility!=="PHASE2_EXCLUDED").length,
   originalGoalElapsedNonPhase2:records.filter(x=>x.phase3SourceEligibility!=="PHASE2_EXCLUDED"&&x.daysUntilOriginalGoal<=0).length,
   upcomingOriginalGoalsWithin30Days:records.filter(x=>x.phase3SourceEligibility!=="PHASE2_EXCLUDED"&&x.daysUntilOriginalGoal>0&&x.daysUntilOriginalGoal<=30).length,
   researchReceiptSubmissions:forecast.submitted,
   pendingIndependentAuthentication:forecast.pendingIndependentAuthentication,
   blockedReceipts:forecast.blocked,
   outcomeSourceCandidateSubmissions:outcome.submittedResearchEvidenceRecords,
   independentlyAuthenticatedForecasts:0,
   independentlyAdjudicatedOriginalGoalOutcomes:0,
   qualifiedForecastOutcomePairs:0,
   approvedTradingSignals:0
  },
  threeWayScorecard:{
   status:score.status,
   researchRosterCases:score.researchRosterCases,
   evidenceGates:score.readinessGates,
   researchStatistics:score.researchStatistics,
   independentValidatedAccuracyPct:null,
   approvedPredictionModel:false
  },
  records
 },null);
}
function csvEscape(x){
 const s=String(x??"");
 return /[",\r\n]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s;
}
function rowsCsv(report){
 const keys=["caseKey","ticker","originalFirstGoalDate","listedTargetDate",
  "daysUntilOriginalGoal","phase3SourceEligibility","status","savedSnapshotAsOf",
  "daysSinceSavedSnapshot","sourceFingerprint","researchReceiptCount",
  "outcomeSourceCandidateCount","outcomeReviewState","forecastOutcomePairQualified",
  "nextAction"];
 return [keys.join(","),...report.records.map(r=>
  keys.map(k=>csvEscape(r[k])).join(","))].join("\n")+"\n";
}
function main(){
 const out=process.env.RAAS_FDA_NIGHTLY_REPORT_JSON;
 const csv=process.env.RAAS_FDA_NIGHTLY_REPORT_CSV;
 if(!out||!csv||path.resolve(out)===path.resolve(csv))
  throw Error("RAAS_FDA_NIGHTLY_REPORT_DESTINATIONS_REQUIRED");
 let report=buildNightlyRaasFdaAudit(
  process.env.RAAS_FDA_EVALUATION_AS_OF_UTC||new Date().toISOString());
 const previousPath=process.env.RAAS_FDA_NIGHTLY_PREVIOUS_JSON;
 if(previousPath){
  try{
   if(fs.statSync(previousPath).size>3_000_000)
    throw Error("PREVIOUS_RESEARCH_REPORT_TOO_LARGE");
   const previous=JSON.parse(fs.readFileSync(previousPath,"utf8"));
   report=compareNightlyReports(report,previous);
  }catch(error){
   if(error.code!=="ENOENT")
    report=compareNightlyReports(report,{});
  }
 }
 for(const file of [out,csv])fs.mkdirSync(path.dirname(file),{recursive:true});
 fs.writeFileSync(out,JSON.stringify(report,null,2)+"\n");
 fs.writeFileSync(csv,rowsCsv(report));
 process.stdout.write(JSON.stringify({
  status:"EVIDENCE_GAPS_REPORTED_NOT_VALIDATED",
  asOf:report.runAtUtc,counts:report.counts,
  auditStateFingerprint:report.auditStateFingerprint,
  savedSourceEvidenceFingerprint:report.savedSourceEvidenceFingerprint,
  comparisonStatus:report.sourceChangeComparisonStatus,
  changedSavedSourceCases:report.savedSourceChanges?.length??null,
  calendarDeadlineTransitions:report.calendarDeadlineTransitions?.length??null,
  accuracy:report.threeWayScorecard.independentValidatedAccuracyPct
 })+"\n");
}
if(require.main===module)main();
module.exports={buildNightlyRaasFdaAudit,rowsCsv};
