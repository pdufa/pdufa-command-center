"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),os=require("node:os");
const {execFileSync}=require("node:child_process");
const {buildNightlyRaasFdaAudit:build,rowsCsv}=
 require("../scripts/raas-fda-nightly-evidence-report.cjs");

test("nightly as-of report reconciles all eleven research cycles without a fabricated forecast",()=>{
 const r=build("2026-11-05T05:30:00Z");
 assert.equal(r.scope,"RAAS_NIGHTLY_FDA_THREE_WAY_EVIDENCE_READINESS_RESEARCH_ONLY");
 assert.equal(r.counts.researchApplicationCycles,11);
 assert.equal(r.counts.phase2Excluded,2);
 assert.equal(r.counts.nonPhase2ResearchLeads,9);
 assert.equal(r.counts.originalGoalElapsedNonPhase2,1);
 assert.equal(r.counts.upcomingOriginalGoalsWithin30Days,4);
 assert.equal(r.counts.researchReceiptSubmissions,0);
 assert.equal(r.counts.independentlyAuthenticatedForecasts,0);
 assert.equal(r.counts.independentlyAdjudicatedOriginalGoalOutcomes,0);
 assert.equal(r.counts.qualifiedForecastOutcomePairs,0);
 assert.equal(r.counts.approvedTradingSignals,0);
 assert.equal(r.threeWayScorecard.researchStatistics,null);
 assert.equal(r.threeWayScorecard.independentValidatedAccuracyPct,null);
 assert.equal(r.threeWayScorecard.approvedPredictionModel,false);
 assert.equal(r.threeWayScorecard.evidenceGates.length,6);
 assert.equal(r.records.length,11);
 assert.equal(new Set(r.records.map(x=>x.caseKey)).size,11);
 assert.match(r.sourceSignature,/^[0-9a-f]{64}$/);
 assert.equal(r.sourceChangedSincePreviousRun,null);
 assert.ok(r.records.every(x=>x.decision==="ABSTAIN"&&
  x.claimedValidatedProbability===null&&
  x.independentlyAdjudicatedOutcome===null&&
  !x.forecastOutcomePairQualified));
});
test("expired first goal cannot become a prospective prediction after revised deadline",()=>{
 const r=build("2026-11-05T20:00:00Z");
 const capr=r.records.find(x=>x.ticker==="CAPR");
 assert.equal(capr.originalFirstGoalDate,"2026-08-22");
 assert.equal(capr.listedTargetDate,"2026-11-22");
 assert.equal(capr.daysUntilOriginalGoal,-75);
 assert.equal(capr.status,"ORIGINAL_GOAL_ELAPSED_NO_RETROACTIVE_FORECAST");
 assert.match(capr.nextAction,/do NOT create a late forecast/);
 assert.equal(capr.forecastOutcomePairQualified,false);
 const two=r.records.filter(x=>x.ticker==="COGT"&&
  x.status==="PHASE2_EXCLUDED");
 assert.equal(two.length,2);
 const peak=r.records.find(x=>x.caseKey==="COGT-BEZUCLASTINIB-GIST-2026");
 assert.equal(peak.trialNctId,"NCT05208047");
 assert.equal(peak.status,"STAGE3_SOURCE_ONLY_MODEL_UNVALIDATED");
});
test("nightly future dates mark original goal expiration and saved snapshot age, not FDA outcome",()=>{
 const first=build("2026-11-05T20:00:00Z");
 const late=build("2026-12-31T22:00:00Z");
 assert.equal(late.counts.originalGoalElapsedNonPhase2,9);
 assert.equal(late.counts.upcomingOriginalGoalsWithin30Days,0);
 assert.ok(late.records.every(x=>x.daysSinceSavedSnapshot>30));
 assert.ok(late.records.every(x=>x.savedSourceSnapshotStaleOver30Days));
 assert.equal(late.counts.independentlyAdjudicatedOriginalGoalOutcomes,0);
 assert.equal(late.counts.independentlyAuthenticatedForecasts,0);
 assert.notEqual(first.sourceSignature,late.sourceSignature);
 assert.equal(first.sourceChangeComparisonStatus,"NO_PREVIOUS_RUN_ARTIFACT_PROVIDED");
});
test("invalid time and backdating before saved snapshot fail closed",()=>{
 for(const val of ["","today","2026-11-05","2026-02-30T00:00:00Z",
  "2026-11-03T23:00:00Z","2026-11-05T13:00:00"]){
  assert.throws(()=>build(val),
   /RAAS_FDA_NIGHTLY_(EXPLICIT_UTC_INSTANT_REQUIRED|SNAPSHOT_FROM_FUTURE)/);
 }
});
test("CSV has one row per application with clear status and no probability",()=>{
 const r=build("2026-11-05T20:00:00Z");
 const csv=rowsCsv(r);
 const rows=csv.trimEnd().split("\n");
 assert.equal(rows.length,12);
 assert.match(rows[0],/caseKey,ticker,originalFirstGoalDate/);
 assert.match(csv,/CAPR/);
 assert.match(csv,/COGT-BEZUCLASTINIB-GIST-2026/);
 assert.doesNotMatch(csv,/0\.5,0\.3,0\.2/);
});
test("CLI writes nightly JSON and CSV artifacts with shared source signatures",()=>{
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),"raas-fda-nightly-"));
 try{
  const json=path.join(temp,"daily-report.json"),
   csv=path.join(temp,"daily-review.csv");
  const stdout=execFileSync(process.execPath,[
   path.join(__dirname,"../scripts/raas-fda-nightly-evidence-report.cjs")
  ],{env:{...process.env,RAAS_FDA_EVALUATION_AS_OF_UTC:"2026-11-05T20:00:00Z",
   RAAS_FDA_NIGHTLY_REPORT_JSON:json,RAAS_FDA_NIGHTLY_REPORT_CSV:csv
  },encoding:"utf8"});
  assert.match(stdout,/EVIDENCE_GAPS_REPORTED_NOT_VALIDATED/);
  const result=JSON.parse(fs.readFileSync(json,"utf8"));
  assert.equal(result.counts.researchApplicationCycles,11);
  assert.equal(result.counts.qualifiedForecastOutcomePairs,0);
  assert.equal(result.records.length,11);
  assert.equal(fs.readFileSync(csv,"utf8").trim().split("\n").length,12);
 }finally{fs.rmSync(temp,{recursive:true,force:true});}
});
