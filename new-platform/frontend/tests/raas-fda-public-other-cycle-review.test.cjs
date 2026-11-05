"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
 esModuleInterop:true,jsx:ts.JsxEmit.ReactJSX}}).outputText,file);
const saved=require("../data/raas-fda-historical-other-cycle-exclusions.json");
const {currentRaasFdaDocumentedOtherCycleExclusions:build}
 =require("../lib/raas-fda-public-other-cycle-review.ts");
const {buildThreeWayFDAFreezePreflightPlan}
 =require("../lib/raas-fda-three-way-freeze-preflight.ts");
test("two official prior/other-indication documents are not upcoming FDA outcomes",()=>{
 const result=build(),plan=buildThreeWayFDAFreezePreflightPlan();
 assert.equal(result.documentedOtherCycleExclusions,2);
 assert.equal(result.independentlyMatchedCurrentReviewCycles,0);
 assert.equal(result.independentlyAdjudicatedUpcomingFdaOutcomes,0);
 assert.equal(result.qualifiedForecastOutcomePairs,0);
 assert.equal(plan.records.length,11);
 assert.equal(new Set(result.records.map(r=>r.caseKey)).size,2);
 assert.equal(saved.records.length,2);
 for(const row of result.records){
  const target=plan.records.find(r=>r.caseKey===row.caseKey);
  assert.equal(row.ticker,target.ticker);
  assert.equal(row.originalFirstGoalDate,target.originalFirstGoalDate);
  assert.ok(row.historicalFdaActionDate<row.originalFirstGoalDate);
  assert.equal(row.validHistoricalActionForTargetCycle,false);
  assert.equal(row.targetOriginalGoalDispositionIndependentlyAdjudicated,false);
  assert.equal(row.exactPendingReviewCycleIndependentlyVerified,false);
  assert.equal(row.verifiedThreeWayPrediction,false);
  assert.equal(row.pendingReviewCycleOutcome,"UNVERIFIED");
  assert.equal(row.raasForecastRelease,"ABSTAIN");
  assert.ok(row.historicalFdaSourceUrl.startsWith("https://www.fda.gov/"));
 }
});
test("CYTK is prior original oHCM NDA, not its 2026 MAPLE efficacy supplement",()=>{
 const r=build().records.find(x=>x.ticker==="CYTK");
 assert.equal(r.publiclyIndexedApplicationNumber,"NDA219083");
 assert.equal(r.historicalFdaActionDate,"2025-12-19");
 assert.equal(r.originalFirstGoalDate,"2026-11-14");
 assert.equal(r.classification,"PARENT_ORIGINAL_NDA_NOT_PENDING_EFFICACY_SUPPLEMENT");
 assert.match(r.publicHistoricalIndication,/obstructive hypertrophic/i);
 assert.match(r.researchTargetCycle,/MAPLE-HCM supplemental NDA/);
 assert.equal(r.validHistoricalActionForTargetCycle,false);
});
test("CORT ovarian cancer NDA is not 2026 Cushing syndrome resubmission",()=>{
 const r=build().records.find(x=>x.ticker==="CORT");
 assert.equal(r.caseKey,"RELACORILANT_CUSHINGS_US_20261217");
 assert.equal(r.publiclyIndexedApplicationNumber,"NDA220641");
 assert.equal(r.historicalFdaActionDate,"2026-03-25");
 assert.equal(r.originalFirstGoalDate,"2026-12-17");
 assert.match(r.publicHistoricalIndication,/ovarian/);
 assert.match(r.researchTargetCycle,/Cushing/);
 assert.equal(r.classification,"DIFFERENT_INDICATION_ORIGINAL_APPROVAL_NOT_CUSHINGS_RESUBMISSION");
 assert.equal(r.validHistoricalActionForTargetCycle,false);
});
test("predictions page visibly flags two FDA lookalikes globally and per case",()=>{
 const page=fs.readFileSync(path.join(root,"app/predictions/page.tsx"),"utf8");
 for(const x of ["data-raas-fda-historical-other-cycle-source-guards",
  "data-raas-fda-other-cycle-document-guard",
  "data-raas-fda-per-case-other-cycle-exclusion",
  "currentRaasFdaDocumentedOtherCycleExclusions",
  "historicalFdaSourceUrl","targetCycleIssuerSourceUrl",
  "is not","not independently"]){
  assert.ok(page.includes(x),"Missing: "+x);
 }
 const result=ts.transpileModule(page,{fileName:"predictions.tsx",
  reportDiagnostics:true,compilerOptions:{
   target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,
   jsx:ts.JsxEmit.ReactJSX
  }});
 assert.equal((result.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error).length,0);
});
