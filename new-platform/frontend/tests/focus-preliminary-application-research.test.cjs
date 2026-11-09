"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>{
 const js=ts.transpileModule(fs.readFileSync(file,"utf8"),{
   compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
     jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
 mod._compile(js.outputText,file);
};
const {FOCUS_PRELIMINARY_R39:d}=require("../lib/focus-preliminary-application-research.ts");
const focus=require("../data/p3PostDataActive.json");
test("29 FOCUS exact NCT rows map to exactly 23 unique provisional application cycles",()=>{
 assert.equal(d.schema,"MAIN_FOCUS_29_23_APP_RESEARCH_V1");
 assert.equal(d.asOf,"2026-11-09");
 assert.equal(d.trials.length,29);
 assert.equal(d.applications.length,23);
 assert.equal(new Set(d.trials.map(x=>x.nct)).size,29);
 assert.equal(new Set(d.applications.map(x=>x.id)).size,23);
 assert.deepEqual(d.trials.map(x=>x.nct),focus.records.map(x=>x.nct));
 for(const row of d.trials){
   assert.ok(row.applicationCycleIds.length>=1);
   assert.ok(row.applicationCycleIds.every(id=>d.applications.some(a=>a.id===id&&a.ncts.includes(row.nct))));
 }
 assert.deepEqual(d.trials.find(x=>x.nct==="NCT02500381").applicationCycleIds.sort(),
   ["srpt-casimersen","srpt-golodirsen"]);
});
test("all 23 groups have source-backed benefit, opposing evidence, and missing reviews",()=>{
 for(const a of d.applications){
   assert.ok(a.clinicalEvidence.observation.length>30,a.id);
   assert.ok(a.opposingEvidence.observation.length>30,a.id);
   assert.ok(a.regulatoryRisk.length>20,a.id);
   assert.ok(a.uncertaintyReasons.every(x=>x.length>10),a.id);
   assert.ok(a.sourceLinks.every(x=>x.url.startsWith("https://")),a.id);
   assert.ok(a.sourceDate<=d.asOf,a.id);
   assert.ok(a.reportedGoal===null||a.reportedGoal>d.asOf,a.id);
   assert.ok(a.methodVersion===d.schema);
   assert.ok(a.leanConfidence==="HIGH_UNQUANTIFIED_UNCERTAINTY");
   assert.equal(a.exactFdaDecisionCycleIndependentlyCertified,false);
   assert.equal(a.qualifiedReviewerSignoff,false);
   assert.equal(a.numericalFDAProbability,null);
   assert.equal(a.calibratedAccuracy,null);
   assert.ok(a.reviewDelayOrExtensionPrediction==="ABSTAIN"||a.reviewDelayOrExtensionPrediction==="NOT_APPLICABLE_ALREADY_OBSERVED");
 }
});
test("five explicitly preliminary approval leans and one concern-driven CRL lean are NOT official forecasts",()=>{
 assert.deepEqual(d.summary,{
   ncts:29,applicationCycles:23,sourceBasedPreliminaryResearchProfiles:23,
   researchLeanApprovals:5,researchLeanCrls:1,abstainResearchCalls:16,
   observedPastApprovals:1,qualifiedIndependentClinicalReviews:0,
   independentlyValidatedFDAForecasts:0,verifiedHistoricalBacktests:0,
   numericalPredictionsReleased:0
 });
 assert.equal(d.applications.filter(x=>x.releasedRegulatoryPrediction==="ABSTAIN").length,22);
 assert.equal(d.applications.filter(x=>x.releasedRegulatoryPrediction==="NOT_APPLICABLE_ALREADY_OBSERVED").length,1);
 assert.equal(d.releaseStatus,"ALL_FUTURE_APPLICATION_APPROVAL_CRL_AND_REVIEW_DELAY_FORECASTS_ABSTAIN");
});
test("MYQORZO oHCM approval observed December 2025; ACACIA NHCM remains separate proposed supplement",()=>{
 const old=d.applications.find(x=>x.id==="cytk-aficamten-ohcm");
 const next=d.applications.find(x=>x.id==="cytk-aficamten-nhcm");
 assert.equal(old.preliminaryResearchLean,"OBSERVED_APPROVAL");
 assert.equal(old.observedAction,"FDA_APPROVED_2025_12_19");
 assert.equal(old.reportedGoal,null);
 assert.ok(old.sourceLinks.some(s=>s.url.includes("fda.gov")));
 assert.equal(next.preliminaryResearchLean,"ABSTAIN");
 assert.equal(next.observedAction,null);
 assert.equal(next.originalStage,"PLANNED");
 assert.equal(next.reportedGoal,null);
 assert.deepEqual(old.ncts,["NCT05767346"]);
 assert.deepEqual(next.ncts,["NCT06081894"]);
});
test("old formal review extensions are not new prospective timing predictions",()=>{
 for(const id of ["capr-deramiocel","svra-molgramostim"]){
   const a=d.applications.find(x=>x.id===id);
   assert.equal(a.observedFormalReviewExtension,true);
   assert.equal(a.reviewDelayOrExtensionPrediction,"ABSTAIN");
   assert.match(a.reviewTimingStatus,/PRIOR_FORMAL_EXTENSION_DOCUMENTED/);
 }
 const other=d.applications.find(x=>x.id==="cogt-gist");
 assert.equal(other.observedFormalReviewExtension,false);
 assert.equal(other.reviewDelayOrExtensionPrediction,"ABSTAIN");
});
test("PREDICTIONS visibly renders 29/23 distinct assessments and separate outcome/timing",()=>{
 const ui=fs.readFileSync(path.join(root,"app/predictions/FocusPreliminaryApplicationBoard.tsx"),"utf8");
 const page=fs.readFileSync(path.join(root,"app/predictions/page.tsx"),"utf8");
 assert.match(ui,/29 FOCUS trials \/ 23 provisional FDA application assessments/);
 assert.match(ui,/23 application-specific evidence judgments/);
 assert.match(ui,/29-trial roster and application linkage/);
 assert.match(ui,/Counterevidence or limitations/);
 assert.match(ui,/Review delay\/extension prediction/);
 assert.match(ui,/Official FDA prediction/);
 assert.match(ui,/ABSTAIN/);
 assert.ok(page.includes("<FocusPreliminaryApplicationBoard/>"));
 assert.doesNotMatch(ui,/\bPOST\b|submitClinicalGrade|recordOfficialFDAForecast/);
});
