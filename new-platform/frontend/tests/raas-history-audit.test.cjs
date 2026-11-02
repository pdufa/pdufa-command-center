"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>{
 const code=fs.readFileSync(file,"utf8");
 const js=ts.transpileModule(code,{fileName:file,reportDiagnostics:true,compilerOptions:{
  module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022
 }}).outputText;
 mod._compile(js,file);
};
const audit=require("../lib/raas-history-audit.ts");
const topIntake=require("../lib/raas-top-retrospective-intake.ts");
const bottomIntake=require("../lib/raas-retrospective-intake.ts");
const rawTop=require("../data/raas-retrospective-top-cases.json");
const rawBottom=require("../data/raas-retrospective-source-cases.json");
const top=topIntake.parseTopRetrospective(rawTop);
const bottom=bottomIntake.parseRetrospectiveFeed(rawBottom);
const cases=audit.buildHistoricalResearchAudit(top,bottom);
test("audit distinguishes two pre-readout and four post-readout examples",()=>{
 const sum=audit.summarizeHistoricalResearch(cases);
 assert.equal(sum.topExamples,2);
 assert.equal(sum.bottomExamples,4);
 assert.equal(sum.totalExamples,6);
 assert.equal(sum.eligiblePredictions,0);
 assert.equal(sum.qualifiedMetricGrades,0);
 assert.ok(sum.openReviews>=6);
 assert.equal(new Set(cases.map(c=>c.id)).size,6);
});
test("each historic example has recorded dated source claims and explicit blocking reviews",()=>{
 for(const c of cases){
  assert.equal(c.eligibleForHistoricalTraining,false);
  assert.equal(c.eligibleForPredictiveValidation,false);
  assert.ok(c.grossPercent>-100);
  assert.ok(c.items.some(x=>x.id==="original-prediction"&&x.status==="NOT_AVAILABLE"));
  assert.ok(c.items.some(x=>x.id==="pricing-audit"&&x.status==="REQUIRES_RECONCILIATION"));
  assert.ok(c.items.some(x=>x.id==="sec-finance"&&x.status==="REQUIRES_RECONCILIATION"));
  assert.ok(c.items.some(x=>x.id==="clinical-peer"&&x.status==="REQUIRES_RECONCILIATION"));
  assert.ok(c.items.filter(x=>x.status==="RECORDED_NOT_INDEPENDENTLY_VERIFIED").every(x=>x.sourceUrl?.startsWith("https://")));
  assert.ok(c.criticalOutstandingCount>=1);
 }
});
test("program repeated in TOP and BOTTOM is two phase-specific reviews, not two forecasts",()=>{
 const gern=cases.filter(c=>c.ticker==="GERN");
 assert.equal(gern.length,2);
 assert.deepEqual(new Set(gern.map(x=>x.stage)),new Set(["pre","post"]));
 assert.ok(gern.every(x=>x.nctCount===1));
});
test("early Geron FDA approval is shown as later outcome, not an ex-ante forecast",()=>{
 const c=cases.find(x=>x.ticker==="GERN"&&x.stage==="post");
 assert.ok(c);
 const action=c.items.find(x=>x.id==="observed-action");
 assert.match(action.detail,/before the published target/);
 assert.equal(action.status,"RECORDED_NOT_INDEPENDENTLY_VERIFIED");
 assert.ok(c.items.some(x=>x.id==="pdufa-prior"));
 assert.ok(c.items.some(x=>x.id==="exit-cutoff"));
});
test("no case becomes RAAS-ready if someone edits a gross retrospective price",()=>{
 const altered={...bottom,records:bottom.records.map((r,i)=>i===0?{
  ...r,exit:{...r.exit,close:1000}
 }:r)};
 const rows=audit.buildHistoricalResearchAudit(top,altered);
 const changed=rows.find(x=>x.ticker===bottom.records[0].ticker&&x.stage==="post");
 assert.ok(changed.grossPercent>1000);
 assert.equal(changed.eligibleForPredictiveValidation,false);
 assert.ok(changed.items.find(x=>x.id==="original-prediction"));
});
test("historic audit source and Next page parse without TSX errors",()=>{
 const root=path.resolve(__dirname,"..");
 for(const f of ["lib/raas-history-audit.ts","app/raas-history/page.tsx"]){
  const result=ts.transpileModule(fs.readFileSync(path.join(root,f),"utf8"),{
   fileName:f,reportDiagnostics:true,compilerOptions:{
    module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX
   }});
  assert.deepEqual((result.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error)
    .map(x=>ts.flattenDiagnosticMessageText(x.messageText," ")),[],f);
 }
 const disclosure=fs.readFileSync(path.join(root,"app/TrialRaasDisclosure.tsx"),"utf8");
 assert.match(disclosure,/href="\/raas-history"/);
 const page=fs.readFileSync(path.join(root,"app/raas-history/page.tsx"),"utf8");
 assert.match(page,/research-only/i);
 assert.match(page,/eligiblePredictions/);
});
