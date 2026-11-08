"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(module,file)=>module._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  esModuleInterop:true,jsx:ts.JsxEmit.ReactJSX
 }}).outputText,file);
const registry=require("../public/raas-registry-evidence-index.json");
const {GET}=require("../app/api/raas-unsigned-review-worksheet/route.ts");
const headers=[
 "nctId","ticker","registrySourceHash","registrySnapshotAsOf","stage",
 "metricId","metricName","category","metricWeightPercent",
 "requiredEvidence","criticalRisk","registeredRegistrySource",
 "registrySourceLeads","registryNumericLeads","provisionalResearchFinding",
 "provisionalResearchBandNotApproved","provisionalSourceUrl","provisionalBenchmarkUrl",
 "reviewerStatus","reviewerProposedBandNotApproved","reviewerPrimarySourceUrl",
 "reviewerSourceDate","reviewerBenchmarkSourceUrl","reviewerBenchmarkContext",
 "reviewerObservedFinding","reviewerUncertaintyReview","reviewerCriticalRiskReview",
 "reviewerMethodNotes","externalIndependentAuthenticationRequired"
];
test("source-frozen 60-row worksheet for exact NCT offers all review inputs without approval",async()=>{
 const row=registry.records.find(x=>x.nctId==="NCT05208047");
 assert.ok(row);
 const url="https://pdufa.example/api/raas-unsigned-review-worksheet?";
 const response=GET(new Request(url+new URLSearchParams({
  nctId:row.nctId,ticker:row.ticker})));
 assert.equal(response.status,200);
 assert.match(response.headers.get("content-type"),/text\/csv/);
 assert.match(response.headers.get("content-disposition"),/NCT05208047/);
 const data=(await response.text()).replace(/^\uFEFF/,"");
 const lines=data.trimEnd().split("\r\n");
 assert.equal(lines.length,61);
 assert.deepEqual(lines[0].split(","),headers);
 const all=lines.slice(1);
 assert.equal(all.filter(x=>x.includes('"pre-')).length,30);
 assert.equal(all.filter(x=>x.includes('"post-')).length,30);
 assert.ok(all.every(x=>x.includes(row.nctId)&&x.includes(row.sourceHash)));
 assert.ok(all.every(x=>x.includes("NOT_STARTED")));
 assert.ok(all.every(x=>x.includes("EXTERNAL_AUTHENTICATION_REQUIRED")));
 assert.ok(!headers.some(x=>/approvedRaasScore|certifiedHumanReview|fdaProbability/i.test(x)));
 for(const line of all){
  const fields=[...line.matchAll(/"(?:[^"]|"")*"(?=,|$)/g)];
  assert.equal(fields.length,headers.length,"Each row must match header columns");
 }
});
test("worksheet route fails closed on invalid trial, wrong ticker, unknown NCT",()=>{
 const url="https://pdufa.example/api/raas-unsigned-review-worksheet?";
 const query=(nctId,ticker)=>GET(new Request(url+new URLSearchParams({nctId,ticker}))).status;
 assert.equal(query("NCT05208047","COGT"),200);
 assert.equal(query("NCT05208047","FAKE"),404);
 assert.equal(query("NCT99999999","COGT"),404);
 assert.equal(query("not-an-nct","COGT"),400);
});
test("review route is linked from exact NCT with explicit no-autosignoff warning",()=>{
 const page=fs.readFileSync(path.join(root,"app/raas-trial-review/page.tsx"),"utf8");
 const csv=fs.readFileSync(path.join(root,"app/api/raas-unsigned-review-worksheet/route.ts"),"utf8");
 assert.match(page,/data-raas-expert-review-worksheet/);
 assert.match(page,/data-raas-review-worksheet-download/);
 assert.match(page,/not an authenticated expert sign-off/);
 assert.match(csv,/Content-Disposition/);
 assert.match(csv,/EXTERNAL_AUTHENTICATION_REQUIRED/);
 assert.match(csv,/^\s*\/\*\* Download a fillable reviewer worksheet/m);
});
