"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}
).outputText,file);
const {buildRaasMetricValidationWorklist,raasDocumentedTrialOptions}=
 require("../lib/raas-metric-validation-worklist.ts");
const pilot=require("../data/raas-pilot-observations.json");
test("All sixty TOP/BOTTOM metric worklist entries preserve exact catalog IDs and never invent a grade",()=>{
 const report=buildRaasMetricValidationWorklist();
 assert.equal(report.scope,"RAAS_60_METRIC_TRIAL_VALIDATION_WORKLIST_READ_ONLY");
 assert.equal(report.totalMetrics,60);
 assert.equal(report.items.length,60);
 assert.equal(report.byStage.pre.total,30);
 assert.equal(report.byStage.post.total,30);
 assert.equal(new Set(report.items.map(m=>m.stage+"|"+m.id)).size,60);
 assert.equal(report.approvedCalibrations,0);
 assert.equal(report.approvedTrialMetricGrades,0);
 assert.equal(report.displayedContext,"GLOBAL_RESEARCH_SOURCES");
 assert.ok(report.items.some(m=>m.sourceCount>0));
 for(const m of report.items){
  assert.equal(m.trialMetricApproved,false);
  assert.equal(m.calibrationApproved,false);
  assert.ok(m.requiredEvidence&&m.scoreRule&&m.criticalRisk&&m.missingRequirements.length>=3);
  assert.equal(m.historicalReviewEligible,false);
 }
});
test("Exact TOP trial returns its own sourced metrics only, never a 0–100 prediction",()=>{
 const report=buildRaasMetricValidationWorklist({nctId:"NCT07363577",ticker:"LBRX",
  drug:"LB-102 (100 mg tablet) | LB-102 (50 mg tablet)",indication:"Schizophrenia"});
 assert.equal(report.byStage.pre.mapped,5);
 assert.equal(report.byStage.post.mapped,0);
 assert.equal(report.sourceMappedMetrics,5);
 assert.equal(report.displayedContext,"EXACT_TRIAL_SOURCE_LEADS");
 for(const item of report.items){
  for(const lead of item.sourceLeads){
   assert.equal(lead.nctId,"NCT07363577");assert.equal(lead.ticker,"LBRX");
   assert.ok(lead.date<=report.sourceAsOf);
   assert.match(lead.sourceUrl,/^https:\/\//);
  }
 }
 const timing=report.items.find(m=>m.id==="pre-4-1");
 assert.ok(timing&&timing.sourceCount>0);
 assert.equal(timing.trialMetricApproved,false);
 assert.equal(timing.evidenceState,"RESEARCH_SOURCE_LEADS_NOT_GRADED");
});
test("BOTTOM trial sources never get misassigned to TOP, or another NCT of the same listed company",()=>{
 const r=buildRaasMetricValidationWorklist({nctId:"NCT06445023",ticker:"CLDX",
  drug:"barzolvolimab",indication:"chronic spontaneous urticaria"});
 assert.equal(r.byStage.pre.mapped,0);
 assert.equal(r.byStage.post.mapped,3);
 assert.ok(r.items.filter(m=>m.sourceCount>0).every(m=>m.stage==="post"));
 assert.ok(r.items.flatMap(m=>m.sourceLeads).every(l=>l.nctId==="NCT06445023"));
 const m=buildRaasMetricValidationWorklist({nctId:"NCT06641076",ticker:"MLTX"});
 assert.equal(m.byStage.post.mapped,3);
 assert.ok(m.items.flatMap(x=>x.sourceLeads).every(l=>l.ticker==="MLTX"));
});
test("Missing, wrong issuer, wrong drug and unrecorded NCT do not inherit another trial's sources",()=>{
 for(const input of [
  {nctId:"NCT07363577",ticker:"CLDX"},
  {nctId:"NCT07363577",ticker:"LBRX",drug:"wrong medicine"},
  {nctId:"NCT07363577",ticker:"LBRX",indication:"wrong disease"},
  {nctId:"NCT99999999",ticker:"LBRX"}
 ]){
  const r=buildRaasMetricValidationWorklist(input);
  assert.equal(r.sourceMappedMetrics,0);
  assert.ok(r.items.every(x=>x.sourceCount===0));
  assert.ok(r.items.every(x=>x.missingRequirements.some(y=>y.includes("exact-NCT"))));
 }
});
test("Reject invalid or path-injection trial identifiers instead of granting source links",()=>{
 for(const t of [
  {nctId:"NCT1234",ticker:"LBRX"},
  {nctId:"NCT07363577",ticker:"../CLDX"},
  {nctId:"NCT07363577",ticker:"LBRX",stage:"unknown"}
 ]){
  assert.throws(()=>buildRaasMetricValidationWorklist(t),/RAAS_WORKLIST_INVALID_TRIAL_CONTEXT/);
 }
});
test("Documented trial picker is deduplicated by issuer, NCT, stage and exact therapy identity",()=>{
 const options=raasDocumentedTrialOptions();
 assert.ok(options.length>=5);
 assert.equal(new Set(options.map(x=>x.stage+"|"+x.nctId+"|"+x.ticker)).size,options.length);
 assert.ok(options.some(x=>x.nctId==="NCT07363577"&&x.stage==="pre"));
 assert.ok(options.some(x=>x.nctId==="NCT06445023"&&x.stage==="post"));
 assert.ok(options.every(x=>x.drug&&x.indication));
});
test("Real TOP/BOTTOM spreadsheets and individual RAAS cells link to worklist and route keeps disclosure details",()=>{
 const root=path.join(__dirname,"..");
 for(const rel of ["app/Phase3ReadoutSheets.tsx","app/TrialRaasDisclosure.tsx",
  "app/RaasSpreadsheetStatus.tsx","app/raas-scan/page.tsx"]){
  const code=fs.readFileSync(path.join(root,rel),"utf8");
  assert.match(code,/raas-worklist/);
 }
 const page=fs.readFileSync(path.join(root,"app/raas-worklist/page.tsx"),"utf8");
 for(const text of ["TOP-RAAS","BOTTOM-RAAS","sourceLeads","requiredEvidence",
  "scoreRule","criticalRisk","missingRequirements","calibrationApproved",
  "historicalHoldoutIssuers","data-raas-validation-metric","#raas-"]){
  assert.ok(page.includes(text),"Missing worklist UI "+text);
 }
 const compile=ts.transpileModule(page,{fileName:"page.tsx",reportDiagnostics:true,
  compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}});
 assert.deepEqual((compile.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error),[]);
});
