"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
const status=require("../data/raas-registry-evidence-change-status.json");
const history=require("../data/raas-registry-evidence-change-history.json");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  esModuleInterop:true,jsx:ts.JsxEmit.ReactJSX}}).outputText,file);
test("seed correctly states no nightly change comparison has been performed",()=>{
 assert.equal(history.schemaVersion,1);
 assert.equal(history.scope,"RAAS_EXACT_NCT_REGISTRY_SOURCE_CHANGE_HISTORY_UNGRADED");
 assert.deepEqual(history.events,[]);
 assert.equal(status.scope,"RAAS_NIGHTLY_REGISTRY_CHANGE_AUDIT_RESEARCH_ONLY");
 assert.equal(status.auditState,"AWAITING_FIRST_COMPARATIVE_SCAN");
 assert.equal(status.trackedResearchNcts,762);
 assert.equal(status.recordedAt,null);
 assert.equal(status.approvedRaasScoreUpdates,0);
 assert.equal(status.calibratedFdaForecastUpdates,0);
});
test("CSV export is guarded from spreadsheet formulas and labels both scores N/A",async()=>{
 const {GET}=require("../app/api/raas-registry-evidence-changes/route.ts");
 const response=GET();
 assert.equal(response.status,200);
 assert.match(response.headers.get("Content-Type"),/text\/csv/);
 assert.equal(response.headers.get("Cache-Control"),"no-store");
 const csv=await response.text();
 assert.ok(csv.includes("eventId,observedAt,nctId,ticker"));
 assert.ok(csv.includes("approvedRaasScore,calibratedFdaProbability"));
 const api=fs.readFileSync(path.join(root,
  "app/api/raas-registry-evidence-changes/route.ts"),"utf8");
 assert.match(api,/\^\\s\*\[=\+@-\]/);
 assert.match(api,/"N\/A","N\/A"/);
});
test("nightly source changes are displayed per-NCT and link back to review workbench",()=>{
 const view=fs.readFileSync(path.join(root,
  "app/raas-evidence-changes/page.tsx"),"utf8");
 const queue=fs.readFileSync(path.join(root,
  "app/raas-evidence-backlog/page.tsx"),"utf8");
 const review=fs.readFileSync(path.join(root,
  "app/raas-trial-review/page.tsx"),"utf8");
 assert.match(view,/data-raas-registry-source-change-history/);
 assert.match(view,/event\.previousSourceHash/);
 assert.match(view,/event\.newSourceHash/);
 assert.match(view,/event\.changeCategories/);
 assert.match(view,/data-raas-source-revision-nct/);
 assert.match(view,/raas-trial-review\?/);
 assert.match(view,/NCT ID/);
 assert.match(view,/Ticker/);
 assert.match(view,/Independent review needed/);
 assert.match(view,/Zero new events is/);
 assert.match(queue,/href="\/raas-evidence-changes"/);
 assert.match(review,/href="\/raas-evidence-changes"/);
 const pages=["app/raas-evidence-changes/page.tsx",
  "app/raas-evidence-backlog/page.tsx","app/raas-trial-review/page.tsx",
  "app/api/raas-registry-evidence-changes/route.ts"];
 for(const file of pages){
  const source=fs.readFileSync(path.join(root,file),"utf8");
  const compiled=ts.transpileModule(source,{
   fileName:file,reportDiagnostics:true,compilerOptions:{
    target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,
    jsx:ts.JsxEmit.ReactJSX
   }});
  assert.equal((compiled.diagnostics||[]).filter(x=>
   x.category===ts.DiagnosticCategory.Error).length,0);
 }
});
