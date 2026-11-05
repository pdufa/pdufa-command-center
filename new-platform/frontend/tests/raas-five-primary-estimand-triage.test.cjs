"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  esModuleInterop:true,jsx:ts.JsxEmit.ReactJSX}}).outputText,file);
const index=require("../public/raas-registry-evidence-index.json");
const five=require("../data/raas-primary-estimand-five-case-triage.json");
const {buildPrimaryContrastReconciliationLedger}=
 require("../lib/raas-primary-arm-reconciliation.ts");
const report=buildPrimaryContrastReconciliationLedger(index);
const one=(nct,oi=0,ci=0)=>{
 const x=report.records.find(r=>r.nctId===nct&&r.outcomeIndex===oi&&r.comparisonIndex===ci);
 assert.ok(x,"Missing exact source comparison "+nct+" "+oi);
 return x;
};
test("reconciles same fixed 290 original source comparisons and never approves clinical outcomes",()=>{
 assert.equal(report.scope,"RAAS_EXACT_NCT_PRIMARY_ARM_RECONCILIATION_UNGRADED");
 assert.equal(report.registryNcts,762);
 assert.equal(report.comparisons,290);
 assert.equal(report.trialsWithComparisons,170);
 assert.equal(report.rawArmDiscrepancies,1);
 assert.equal(report.approvedRaasScores,0);
 assert.equal(report.independentHumanReviews,0);
 assert.equal(report.calibratedFdaPredictions,0);
 assert.ok(report.repeatedGroupOutcomes>=2);
 assert.ok(report.countProportionIncompatibilities>=1);
 assert.ok(report.roundingCompatible>=1);
 assert.ok(report.records.every(x=>x.approvedMetricGrade===null&&
  x.approvedRaasScore===null&&x.calibratedFdaProbability===null));
});
test("PTCT ataluren stays open for exact modeled estimand review",()=>{
 const x=one("NCT00803205",1,0);
 assert.equal(x.ticker,"PTCT");
 assert.equal(x.groupValues[0],-2.534);
 assert.equal(x.groupValues[1],-5.5);
 assert.equal(x.observedFirstMinusSecond,2.966);
 assert.equal(x.reportedStatistic,2.754);
 assert.equal(x.signal,"ARM_DELTA_DISCREPANCY_NEEDS_ESTIMAND_REVIEW");
 assert.equal(x.absoluteGapToEitherDirection,0.212);
});
test("KMDA responder counts must not be subtracted to reconstruct the difference in proportions",()=>{
 const x=one("NCT02040090");
 assert.equal(x.outcomeUnit,"Participants");
 assert.deepEqual(x.groupValues,[55,58]);
 assert.equal(x.reportedStatistic,-0.018);
 assert.equal(x.signal,"COUNT_ENDPOINT_REQUIRES_PROPORTION_DENOMINATORS");
 assert.equal(x.rawDifferenceEligible,false);
 assert.equal(x.observedFirstMinusSecond,null);
 assert.equal(x.absoluteGapToEitherDirection,null);
 // FDA study review reports 55/56 vs 58/58; count-difference -3 was a false alert.
 assert.ok(Math.abs((55/56-58/58)-(-0.018))<0.001);
});
test("NKTR rounded tenths account for 0.05 mean-difference discrepancy",()=>{
 const x=one("NCT02362672");
 assert.deepEqual(x.groupValues,[0.9,1.5]);
 assert.equal(x.reportedStatistic,-0.55);
 assert.equal(x.observedFirstMinusSecond,-0.6);
 assert.equal(x.absoluteGapToEitherDirection,0.05);
 assert.ok(x.roundingUncertainty>=0.1);
 assert.equal(x.signal,"ROUNDING_COMPATIBLE_MEAN_DIFFERENCE_STILL_UNREVIEWED");
 assert.equal(x.approvedMetricGrade,null);
});
test("ACRS repeated wart-class measurements must never overwrite earlier OG measurements",()=>{
 const x=one("NCT03687372");
 assert.deepEqual(x.groupMeasurementSeries[0],["40","33","2","2","3"]);
 assert.deepEqual(x.groupMeasurementSeries[1],["13","10","1","1","1"]);
 assert.equal(x.armValueMultiplicity,"MULTIPLE_UNRESOLVED_VALUES");
 assert.deepEqual(x.groupValues,[null,null]);
 assert.equal(x.observedFirstMinusSecond,null);
 assert.equal(x.signal,"AMBIGUOUS_MULTIPLE_GROUP_MEASUREMENTS");
});
test("ALEC repeated 96-week class/time measurements are not a single last-arm pair",()=>{
 const x=one("NCT04374136");
 assert.deepEqual(x.groupMeasurementSeries[0],["9.686","6.765","4.477"]);
 assert.deepEqual(x.groupMeasurementSeries[1],["8.177","5.771","4.628"]);
 assert.equal(x.reportedStatistic,1.509);
 assert.ok(Math.abs((9.686-8.177)-1.509)<1e-9,
  "First recorded pair is an arithmetic lead, not documented estimand identity");
 assert.deepEqual(x.groupValues,[null,null]);
 assert.equal(x.observedFirstMinusSecond,null);
 assert.equal(x.signal,"AMBIGUOUS_MULTIPLE_GROUP_MEASUREMENTS");
 assert.equal(x.approvedMetricGrade,null);
});
test("five-case investigation is tied to exact source hashes and never a human signoff",()=>{
 assert.equal(five.schemaVersion,1);
 assert.equal(five.cases.length,5);
 assert.equal(five.sourceAsOf,index.sourceAsOf);
 assert.equal(five.disposition,"AUTOMATED_SCIENTIFIC_SOURCE_REVIEW_ONLY_PENDING_HUMAN_VALIDATION");
 const expected=new Set(["NCT00803205","NCT02040090","NCT02362672",
  "NCT03687372","NCT04374136"]);
 assert.deepEqual(new Set(five.cases.map(x=>x.nctId)),expected);
 for(const item of five.cases){
  const x=one(item.nctId,item.outcomeIndex,item.comparisonIndex);
  assert.equal(item.ticker,x.ticker);
  assert.equal(item.sourceHash,x.sourceHash);
  assert.equal(item.sourceUrl,x.sourceUrl);
  assert.ok(item.rawObservation.length>70);
  assert.ok(item.interpretation.length>70);
  assert.ok(item.neededBeforeClosure.length>70);
  assert.equal(x.independentHumanReview,"NOT_COMPLETED");
 }
});
test("CSV preserves original group series and reclassified signals on exact 290 rows",async()=>{
 const {GET}=require("../app/api/raas-primary-arm-reconciliation/route.ts");
 const res=GET();assert.equal(res.status,200);
 const t=await res.text();
 assert.match(t,/groupMeasurementSeries,armValueMultiplicity,roundingUncertainty/);
 assert.match(t,/AMBIGUOUS_MULTIPLE_GROUP_MEASUREMENTS/);
 assert.match(t,/COUNT_ENDPOINT_REQUIRES_PROPORTION_DENOMINATORS/);
 assert.match(t,/ROUNDING_COMPATIBLE_MEAN_DIFFERENCE_STILL_UNREVIEWED/);
 assert.equal(t.split("\r\n").length-2,290);
});
test("mobile site shows five source interpretation investigations and safe reconstructions",()=>{
 const ui=read("app/raas-evidence-backlog/PrimaryFiveCaseTriage.tsx");
 const trial=read("app/raas-evidence-backlog/TrialPrimaryArmReconciliations.tsx");
 const page=read("app/raas-evidence-backlog/EvidenceBacklogClient.tsx");
 assert.match(page,/PrimaryFiveCaseTriage/);
 assert.match(ui,/data-raas-five-case-estimand-triage/);
 assert.match(ui,/sourceHash===x.sourceHash/);
 assert.match(ui,/No independent statistician/);
 assert.match(trial,/MULTIPLE_UNRESOLVED_VALUES|groupMeasurementSeries/);
 assert.match(trial,/COUNT_ENDPOINT_REQUIRES_PROPORTION_DENOMINATORS/);
 assert.match(trial,/ROUNDING_COMPATIBLE_MEAN_DIFFERENCE_STILL_UNREVIEWED/);
 for(const [name,source] of [["PrimaryFiveCaseTriage.tsx",ui],
  ["TrialPrimaryArmReconciliations.tsx",trial],["EvidenceBacklogClient.tsx",page]]){
  const d=ts.transpileModule(source,{fileName:name,reportDiagnostics:true,
   compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,
    jsx:ts.JsxEmit.ReactJSX}});
  assert.deepEqual((d.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error),[]);
 }
});
