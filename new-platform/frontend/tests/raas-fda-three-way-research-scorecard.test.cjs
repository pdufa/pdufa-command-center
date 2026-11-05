"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  esModuleInterop:true,jsx:ts.JsxEmit.ReactJSX
 }}).outputText,file);
const src=require("../data/raas-fda-three-way-scorecard-pairs.json");
const {scoreThreeWayFdaResearchCohort:score,
 currentRaasFdaThreeWayResearchScorecard:current}=
 require("../lib/raas-fda-three-way-research-scorecard.ts");
const {GET}=require("../app/api/raas-fda-threeway-scorecard/route.ts");
const labels=["PASS","CRL","EXTENSION"];
const probs=(label)=>Object.fromEntries(labels.map(x=>[x,x===label?0.8:0.1]));
const example=(i)=>({
 caseKey:"TEST-CASE-"+i,
 issuer:"HOLDOUT-"+i,
 sourceFingerprint:"f".repeat(64),
 exactFdaApplicationNumber:"NDA-TEST-"+i,
 exactReviewCycleId:"CYCLE-TEST-"+i,
 originalFirstGoalDate:"2026-11-30",
 forecastFrozenAt:"2026-11-04T09:00:00Z",
 probabilities:probs(labels[i%3]),
 actualOriginalGoalDisposition:labels[i%3],
 actionEffectiveDate:"2026-11-20",
 outcomeEvidencePublishedDate:"2026-11-21"
});
const make=(n=45)=>({
 sourceAsOf:"2026-12-15",
 cohortCaseKeys:Array.from({length:n},(_,i)=>"TEST-CASE-"+i),
 unpairedCaseKeys:[],
 trainingIssuerKeys:Array.from({length:30},(_,i)=>"TRAIN-"+i),
 declaredCohortComplete:true,
 holdoutProtocolPrecommitted:true,
 pairs:Array.from({length:n},(_,i)=>example(i))
});
const throws=(fn,re)=>assert.throws(fn,re);
test("current live scorecard never fabricates a three-way accuracy percentage",async()=>{
 assert.equal(src.records.length,0);
 const result=current();
 assert.equal(result.researchRosterCases,9);
 assert.equal(result.researchPairedCases,0);
 assert.equal(result.unpairedCases,9);
 assert.equal(result.forecastCoveragePct,0);
 assert.equal(result.status,"NO_VERIFIED_PAIRS");
 assert.equal(result.researchStatistics,null);
 assert.equal(result.independentValidatedAccuracyPct,null);
 assert.equal(result.independentValidatedCalibration,null);
 assert.equal(result.approvedPredictionModel,false);
 assert.equal(result.automatedTradingSignals,0);
 assert.equal(result.readinessGates.length,6);
 assert.equal(result.readinessGates.filter(x=>x.passed).length,0);
 const response=GET();
 assert.equal(response.status,200);
 assert.equal(response.headers.get("Cache-Control"),"no-store");
 const api=await response.json();
 assert.equal(api.researchStatistics,null);
 assert.equal(api.researchPairedCases,0);
});
test("45 independent synthetic completed test cases calculate correct research-only multi-class metrics",()=>{
 const x=score(make());
 assert.equal(x.status,"RESEARCH_DIAGNOSTIC_ONLY_INDEPENDENT_AUDIT_REQUIRED");
 assert.equal(x.researchRosterCases,45);
 assert.equal(x.holdoutIssuers,45);
 assert.equal(x.trainingIssuers,30);
 assert.equal(x.forecastCoveragePct,100);
 assert.equal(x.readinessGates.filter(y=>y.passed).length,6);
 assert.equal(x.researchStatistics.topClassAccuracyPct,100);
 assert.equal(x.researchStatistics.balancedAccuracyPct,100);
 assert.equal(x.researchStatistics.alwaysPassBaselineAccuracyPct,33.33);
 assert.equal(x.researchStatistics.multiclassBrier,0.06);
 assert.equal(x.researchStatistics.multiclassLogLoss,0.2231);
 assert.equal(x.researchStatistics.expectedCalibrationErrorPct,20);
 assert.equal(x.researchStatistics.confusionMatrix.PASS.PASS,15);
 assert.equal(x.researchStatistics.confusionMatrix.CRL.CRL,15);
 assert.equal(x.researchStatistics.confusionMatrix.EXTENSION.EXTENSION,15);
 assert.deepEqual(x.researchStatistics.perClassRecallPct,
  {PASS:100,CRL:100,EXTENSION:100});
 assert.ok(x.researchStatistics.accuracyWilson95Pct[0]>90);
 assert.equal(x.researchStatistics.accuracyWilson95Pct[1],100);
 assert.equal(x.independentValidatedAccuracyPct,null);
 assert.equal(x.approvedPredictionModel,false);
});
test("small or unbalanced samples suppress ALL headline diagnostic scores",()=>{
 for(const data of [
  make(15),
  {...make(),declaredCohortComplete:false},
  {...make(),holdoutProtocolPrecommitted:false},
  {...make(),trainingIssuerKeys:["ONE-ISSUER"]},
  {...make(),pairs:make().pairs.map((x,i)=>i<15?
   {...x,actualOriginalGoalDisposition:"PASS",probabilities:probs("PASS")}:
   {...x,actualOriginalGoalDisposition:"CRL",probabilities:probs("CRL")})}
 ]){
  const r=score(data);
  assert.equal(r.researchStatistics,null);
  assert.equal(r.status,"INSUFFICIENT_RESEARCH_VALIDATION");
  assert.equal(r.independentValidatedAccuracyPct,null);
 }
});
test("duplicate cases, unknown cases, omitted abstentions, and leaked training issuer are guarded",()=>{
 const a=make();
 throws(()=>score({...a,pairs:[...a.pairs,a.pairs[0]]}),/PAIR_INVALID/);
 throws(()=>score({...a,cohortCaseKeys:a.cohortCaseKeys.slice(1)}),/PAIR_INVALID/);
 throws(()=>score({...a,cohortCaseKeys:[...a.cohortCaseKeys,a.cohortCaseKeys[0]]}),/COHORT_INPUT_INVALID/);
 throws(()=>score({...a,unpairedCaseKeys:["TEST-CASE-0"]}),/DENOMINATOR_MISMATCH/);
 const overlapping=score({...a,trainingIssuerKeys:[...a.trainingIssuerKeys.slice(1),"HOLDOUT-0"]});
 assert.equal(overlapping.researchStatistics,null);
 assert.equal(overlapping.readinessGates.find(x=>x.id==="issuer-disjoint-training").passed,false);
 const partial=score({
  ...a,pairs:a.pairs.slice(0,44),unpairedCaseKeys:["TEST-CASE-44"]
 });
 assert.equal(partial.researchRosterCases,45);
 assert.equal(partial.unpairedCases,1);
 assert.equal(partial.forecastCoveragePct,97.78);
});
test("late freeze, source leakage, post-original-goal outcome, or invalid timestamps are rejected",()=>{
 const a=make();
 for(const patch of [
  {forecastFrozenAt:"2026-11-30T00:00:00Z"},
  {forecastFrozenAt:"2026-11-20T00:01:00Z"},
  {forecastFrozenAt:"2026-11-04T09:00:00"},
  {actionEffectiveDate:"2026-12-01"},
  {outcomeEvidencePublishedDate:"2026-11-19"},
  {outcomeEvidencePublishedDate:"2026-12-16"}
 ]){
  const b={...a,pairs:[{...a.pairs[0],...patch},...a.pairs.slice(1)]};
  throws(()=>score(b),/TEMPORAL_LOOKAHEAD_OR_GOAL_MISMATCH|PAIR_INVALID/);
 }
});
test("invalid probabilities and duplicate identity cannot enter even provisional scorecard",()=>{
 const a=make();
 for(const patch of [
  {probabilities:{PASS:0.5,CRL:0.5,EXTENSION:0.5}},
  {probabilities:{PASS:-0.1,CRL:0.5,EXTENSION:0.6}},
  {probabilities:{PASS:0.2,CRL:0.3,EXTENSION:NaN}},
  {probabilities:{PASS:0.2,CRL:0.3,EXTENSION:0.5,OTHER:0}},
  {sourceFingerprint:"bad"},
  {exactReviewCycleId:""},
  {actualOriginalGoalDisposition:"APPROVED"}
 ]){
  const b={...a,pairs:[{...a.pairs[0],...patch},...a.pairs.slice(1)]};
  throws(()=>score(b),/PAIR_INVALID/);
 }
});
test("confusion matrix preserves actual row labels and fixed predicted tie order",()=>{
 const a=make();
 const mixed=a.pairs.map((x,i)=>i%3===0?
  {...x,probabilities:{PASS:0.1,CRL:0.8,EXTENSION:0.1}}:x);
 const r=score({...a,pairs:mixed}).researchStatistics;
 assert.equal(r.confusionMatrix.PASS.CRL,15);
 assert.equal(r.confusionMatrix.PASS.PASS,0);
 assert.equal(r.topClassAccuracyPct,66.67);
 assert.equal(r.perClassRecallPct.PASS,0);
 assert.equal(r.perClassRecallPct.CRL,100);
 assert.equal(r.perClassRecallPct.EXTENSION,100);
 assert.equal(r.balancedAccuracyPct,66.67);
 assert.equal(r.alwaysPassBaselineAccuracyPct,33.33);
});
test("Predictions page visibly labels missing accuracy and contains gate descriptions",()=>{
 const page=fs.readFileSync(path.join(root,"app/predictions/page.tsx"),"utf8");
 assert.match(page,/data-raas-fda-threeway-scorecard/);
 assert.match(page,/currentRaasFdaThreeWayResearchScorecard/);
 assert.match(page,/Not measurable/);
 assert.match(page,/threeWayScorecard\.readinessGates/);
 assert.match(page,/raas-fda-threeway-scorecard/);
 assert.match(page,/never automatically certified/);
 const diagnostics=ts.transpileModule(page,{fileName:"predictions.tsx",
  reportDiagnostics:true,compilerOptions:{
   target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,
   jsx:ts.JsxEmit.ReactJSX
  }});
 assert.equal(diagnostics.diagnostics?.filter(x=>
  x.category===ts.DiagnosticCategory.Error).length??0,0);
});
