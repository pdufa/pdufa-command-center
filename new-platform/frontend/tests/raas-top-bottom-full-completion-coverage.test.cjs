"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{module:ts.ModuleKind.CommonJS,
  target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText,file);
const {parsePhase3CensusCsv}=require("../lib/phase3-census-rows.ts");
const {classifyPhase3Readouts}=require("../lib/phase3-public-readout.ts");
const {buildRaasTopBottomCompletion:build}
 =require("../lib/raas-top-bottom-completion.ts");
const census=fs.readFileSync(path.join(root,"public/phase3-census-2026-10-26.csv"),"utf8");
const evidence=JSON.parse(fs.readFileSync(path.join(root,
 "public/phase3-public-readout-evidence-2026-11-01.json"),"utf8"));
const classified=classifyPhase3Readouts(evidence,parsePhase3CensusCsv(census).rows);
test("all five exact TOP/BOTTOM NCTs reconcile 150 metric statuses: 16 rated, 134 absent",()=>{
 const result=build(classified),s=result.summary;
 assert.equal(s.scoredScope,"SOURCE_CLASSIFIED_TOP_BOTTOM_ONLY");
 assert.equal(s.researchSourceCensus,741);
 assert.equal(s.unclassifiedResearchRows,736);
 assert.equal(s.classifiedTrialRows,5);
 assert.equal(s.topTrials,2);
 assert.equal(s.bottomTrials,3);
 assert.equal(s.topMetricSlots,60);
 assert.equal(s.bottomMetricSlots,90);
 assert.equal(s.allMetricSlots,150);
 assert.equal(s.provisionalMetricGrades,16);
 assert.equal(s.missingMetricGrades,134);
 assert.equal(s.independentFullScores,0);
 assert.equal(s.calibratedFdaProbabilities,0);
 assert.equal(s.gradingSetupReady,true);
 assert.equal(s.allNumericGradesFinished,false);
 assert.equal(result.tasks.length,150);
 assert.equal(result.trials.length,5);
 assert.deepEqual(Object.fromEntries(result.trials.map(x=>[x.nctId,[x.reviewed,x.missing]])),{
  NCT06445023:[3,27],NCT06455202:[3,27],
  NCT06641076:[0,30],NCT07363577:[5,25],NCT07671911:[5,25]
 });
 assert.equal(new Set(result.tasks.map(t=>t.nctId+"|"+t.stage+"|"+t.metricId)).size,150);
 assert.equal(result.tasks.filter(x=>x.status==="SOURCE_CHECKED_PROVISIONAL_ONLY").length,16);
 assert.equal(result.tasks.filter(x=>x.status==="NO_SOURCE_REVIEWED_GRADE").length,134);
 assert.ok(result.tasks.every(t=>t.independentValidationStatus==="NOT_COMPLETED"&&
  t.approvedOverallScore===null&&t.calibratedFdaApprovalProbability===null));
});
test("each missing source task carries exact-trial issuer, registry, metric comparator and no fake values",()=>{
 const plan=build(classified);
 for(const task of plan.tasks.filter(x=>x.numericProvisionalGrade===null)){
  assert.match(task.nctId,/^NCT\d{8}$/);
  assert.ok(["TOP","BOTTOM"].includes(task.stage));
  assert.match(task.metricId,/^(pre|post)-[1-6]-[1-5]$/);
  assert.ok(task.metricName);
  assert.ok(task.requiredSourceEvidence.length>10);
  assert.ok(task.requiredIndependentBenchmark.length>5);
  assert.ok(task.criticalRisk.length>5);
  assert.ok(task.nextAction.includes("independent reviewer"));
  assert.match(task.issuerDisclosureUrl,/^https:\/\//);
  assert.equal(task.registrySourceUrl,"https://clinicaltrials.gov/study/"+task.nctId);
  assert.equal(task.reviewedPrimarySourceUrl,null);
  assert.equal(task.reviewedComparatorSourceUrl,null);
  assert.equal(task.reviewAssessedAt,null);
  assert.equal(task.primarySourceDated,null);
 }
 const reviewed=plan.tasks.filter(x=>x.numericProvisionalGrade!==null);
 assert.ok(reviewed.every(x=>[0,25,50,75,100].includes(x.numericProvisionalGrade)));
 assert.ok(reviewed.every(x=>x.reviewedPrimarySourceUrl?.startsWith("https://")));
 assert.ok(reviewed.every(x=>x.reviewedComparatorSourceUrl?.startsWith("https://")));
 const all=plan.allCsv.trimEnd().split("\r\n");
 const missing=plan.missingOnlyCsv.trimEnd().split("\r\n");
 assert.equal(all.length,151);
 assert.equal(missing.length,135);
 assert.equal(missing[0],all[0]);
 assert.ok(missing.slice(1).every(x=>x.includes("NO_SOURCE_REVIEWED_GRADE")));
 assert.ok(!plan.allCsv.includes("NCT00000000"));
});
test("unverified inventory and duplicate/incorrect stage data fail closed rather than receiving ratings",()=>{
 assert.throws(()=>build({...classified,
  pre:[...classified.pre,classified.pre[0]],total:742}),
  /RAAS_TOP_BOTTOM_DUPLICATE_CLASSIFIED_NCT/);
 assert.throws(()=>build({...classified,
  post:[...classified.post,classified.pre[0]],total:742}),
  /RAAS_TOP_BOTTOM_DUPLICATE_CLASSIFIED_NCT/);
 assert.throws(()=>build({...classified,
  pre:[...classified.pre,classified.unverified[0]],
  unverified:classified.unverified.slice(1)}),
  /RAAS_CLASSIFIED_COMPONENT_EXACT_ISSUER_SOURCE_REQUIRED/);
 assert.throws(()=>build({...classified,
  post:[...classified.post,classified.unverified[0]],
  unverified:classified.unverified.slice(1)}),
  /RAAS_CLASSIFIED_COMPONENT_EXACT_ISSUER_SOURCE_REQUIRED/);
 assert.throws(()=>build({...classified,total:11000}),
  /RAAS_TOP_BOTTOM_COMPLETION_INVALID_CLASSIFICATION/);
 assert.throws(()=>build({...classified,total:762}),
  /RAAS_TOP_BOTTOM_COMPLETION_INVALID_CLASSIFICATION/);
});
test("iPhone TOP/BOTTOM UI shows full coverage and exports without scoring the unverified queue",()=>{
 const page=fs.readFileSync(path.join(root,"app/Phase3ReadoutSheets.tsx"),"utf8");
 const panel=fs.readFileSync(path.join(root,"app/RaasTopBottomCompletionPanel.tsx"),"utf8");
 const module=fs.readFileSync(path.join(root,"lib/raas-top-bottom-completion.ts"),"utf8");
 assert.match(page,/<RaasTopBottomCompletionPanel data=\{data\}\/>/);
 assert.match(panel,/data-raas-top-bottom-metric-completion/);
 assert.match(panel,/data-raas-missing-review-csv/);
 assert.match(panel,/data-raas-all-150-score-status-csv/);
 assert.match(panel,/data-raas-missing-tasks-expand/);
 assert.match(panel,/source-backed|source-classified|source review/i);
 assert.match(panel,/showAll\|\|t\.numericProvisionalGrade===null/);
 assert.match(panel,/task\.numericProvisionalGrade===null\?"Grade N\/A/);
 assert.match(panel,/role="status"/);
 assert.match(module,/buildRaasTopBottomCompletion/);
 assert.match(module,/RAAS_TOP_BOTTOM_UNVERIFIED_LEAKED_INTO_CLASSIFIED/);
 const compiled=ts.transpileModule(panel,{
  fileName:"RaasTopBottomCompletionPanel.tsx",reportDiagnostics:true,
  compilerOptions:{module:ts.ModuleKind.ESNext,
   target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}
 });
 assert.equal((compiled.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error).length,0);
});
