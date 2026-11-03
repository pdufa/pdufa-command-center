"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}
).outputText,file);
const root=path.resolve(__dirname,"..");
const {parsePhase3CensusCsv}=require("../lib/phase3-census-rows.ts");
const {classifyPhase3Readouts}=require("../lib/phase3-public-readout.ts");
const {classifiedRaasTrials,summarizeBulkRaasSources}=
 require("../lib/raas-all-classified-source-review.ts");
const csv=fs.readFileSync(path.join(root,"public/phase3-census-2026-10-26.csv"),"utf8");
const census=parsePhase3CensusCsv(csv);
const release=require("../public/phase3-public-readout-evidence-2026-11-01.json");
const actual=classifyPhase3Readouts(release,census.rows);
const known=classifiedRaasTrials(actual);
test("All five real issuer-classified 741-census trials are present, remaining 736 unclassified",()=>{
 assert.equal(actual.total,741);
 assert.equal(actual.pre.length,2);
 assert.equal(actual.post.length,3);
 assert.equal(actual.unverified.length,736);
 assert.equal(known.length,5);
 assert.deepEqual(known.map(x=>x.ticker+"|"+x.stage).sort(),[
  "CLDX|post","CLDX|post","LBRX|pre","MLTX|post","TRVI|pre"
 ]);
 assert.equal(new Set(known.map(x=>x.nctId)).size,5);
 assert.ok(known.every(x=>x.evidenceDate<="2026-11-01"));
});
test("Summary is explicit that 0 of 5 have an approved overall RAAS score",()=>{
 const p=summarizeBulkRaasSources(actual,[]);
 assert.equal(p.totalCensus,741);
 assert.equal(p.classified,5);
 assert.equal(p.top,2);
 assert.equal(p.bottom,3);
 assert.equal(p.unverified,736);
 assert.equal(p.approvedRaasScores,0);
 assert.equal(p.complete,false);
 const rows=known.map(trial=>({trial,result:null,state:"SOURCE_UNAVAILABLE",
  problem:"No source available"}));
 const e=summarizeBulkRaasSources(actual,rows);
 assert.equal(e.failed,5);
 assert.equal(e.fetched,0);
 assert.equal(e.registryPosted,0);
 assert.equal(e.approvedRaasScores,0);
 assert.equal(e.complete,true);
});
test("Exact source identities and duplicate NCTs fail closed",()=>{
 const fake=structuredClone(actual);
 fake.pre[0].ticker="WRONG";
 assert.throws(()=>classifiedRaasTrials(fake),/RAAS_BULK_ISSUER_SOURCE_CLASSIFICATION_INVALID/);
 const dup=structuredClone(actual);
 dup.post[0].nctId=dup.pre[0].nctId;
 dup.post[0].evidence.nctId=dup.pre[0].nctId;
 assert.throws(()=>classifiedRaasTrials(dup),/RAAS_BULK_DUPLICATE_NCT/);
 const missing=structuredClone(actual);
 missing.unverified.pop();
 assert.throws(()=>classifiedRaasTrials(missing),/RAAS_BULK_CENSUS_INVALID/);
});
test("Cannot promote a wrong-NCT or unauthorized score into the bulk audit",()=>{
 const first=known[0];
 const good={trial:first,state:"READY",problem:null,result:{
  nctId:first.nctId,resultsPosted:true,primaryMeasurements:2,
  seriousAdverseEventTerms:1,seriousAdverseEventArms:2,
  preliminaryMetricLeads:["post-1-1","post-1-5"],sourceNotValidated:true
 }};
 const r=summarizeBulkRaasSources(actual,[good]);
 assert.equal(r.fetched,1);
 assert.equal(r.registryPosted,1);
 assert.equal(r.sourceLeadCount,2);
 assert.equal(r.approvedRaasScores,0);
 const wrong=structuredClone(good);wrong.result.nctId="NCT99999999";
 assert.throws(()=>summarizeBulkRaasSources(actual,[wrong]),/RAAS_BULK_INVALID_RESEARCH_ROW/);
 const claimed=structuredClone(good);claimed.result.sourceNotValidated=false;
 assert.throws(()=>summarizeBulkRaasSources(actual,[claimed]),/RAAS_BULK_INVALID_RESEARCH_ROW/);
 assert.throws(()=>summarizeBulkRaasSources(actual,[good,good]),/RAAS_BULK_INVALID_RESEARCH_ROW/);
});
test("Live scan runs automatically for all classified rows, retains source-only and missing grade labeling",()=>{
 const component=fs.readFileSync(path.join(root,"app/RaasAllClassifiedLiveReview.tsx"),"utf8");
 const sheets=fs.readFileSync(path.join(root,"app/Phase3ReadoutSheets.tsx"),"utf8");
 const markers=["data-raas-all-classified-bulk-scan","data-raas-all-classified-nct",
  "Promise.all(trials.map","/api/tools-trial-evidence?nct=",
  "auditLiveRegistryForRaas","setRevision","approved overall RAAS scores",
  "0–100 RAAS appreciation score","data.unverified.length"];
 for(const x of markers)assert.ok(component.includes(x),x);
 assert.ok(sheets.includes("<RaasAllClassifiedLiveReview data={data}/>"));
 for(const rel of ["lib/raas-all-classified-source-review.ts",
  "app/RaasAllClassifiedLiveReview.tsx","app/Phase3ReadoutSheets.tsx"]){
  const x=ts.transpileModule(fs.readFileSync(path.join(root,rel),"utf8"),{
   fileName:rel,reportDiagnostics:true,compilerOptions:{
    module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX
   }});
  assert.deepEqual((x.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error)
   .map(x=>ts.flattenDiagnosticMessageText(x.messageText," ")),[],rel);
 }
});
