"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}
).outputText,file);
const {parseRegistryEvidenceIndex}=require("../lib/raas-registry-evidence.ts");
const {raasRegistryCoverage}=require("../lib/raas-stage-source-coverage.ts");
const raw=JSON.parse(fs.readFileSync(path.join(root,"public/raas-registry-evidence-index.json"),"utf8"));
const index=parseRegistryEvidenceIndex(raw);

test("exact-NCT 30-metric source coverage across every collected trial in both stages",()=>{
 assert.equal(index.records.length,762);
 let preWithEndpoint=0,posted=0,postWithAnalyses=0,withSafety=0;
 for(const e of index.records){
  const trial={nctId:e.nctId,ticker:e.ticker};
  const top=raasRegistryCoverage(trial,"pre",e);
  const bottom=raasRegistryCoverage(trial,"post",e);
  assert.ok(top);assert.ok(bottom);
  for(const c of [top,bottom]){
   assert.equal(c.totalMetrics,30);
   assert.equal(c.metricCount+c.unmappedMetricIds.length,30);
   assert.equal(c.mappedMetricIds.length,c.metricCount);
   assert.equal(new Set(c.mappedMetricIds).size,c.metricCount);
   assert.equal(c.overallRaasScore,null);
   assert.equal(c.kind,"PRIMARY_REGISTRY_LEAD_COVERAGE_NOT_RAAS");
   assert.ok(c.sourceWeightPct>=0&&c.sourceWeightPct<=100);
  }
  assert.ok([0,5].includes(top.sourceWeightPct));
  if(top.sourceWeightPct>0)preWithEndpoint++;
  if(e.postedResults){
   posted++;
   assert.equal(bottom.mappedMetricIds.includes("post-1-1"),true);
  }else{
   assert.equal(bottom.sourceWeightPct,0);
  }
  if(e.primaryResults.some(x=>x.analysisCount>0)){
   postWithAnalyses++;
   assert.equal(bottom.mappedMetricIds.includes("post-1-3"),true);
  }
  if(e.seriousAdverseEventTermCount>0){
   withSafety++;
   assert.equal(bottom.mappedMetricIds.includes("post-1-5"),true);
  }
 }
 assert.equal(preWithEndpoint,756);
 assert.equal(posted,337);
 assert.equal(postWithAnalyses,184);
 assert.equal(withSafety,306);
});

test("source coverage denies mismatched ticker/NCT and does not score uncollected trials",()=>{
 const x=index.records[0];
 assert.equal(raasRegistryCoverage({nctId:x.nctId,ticker:"WRONG"},"pre",x),null);
 assert.equal(raasRegistryCoverage({nctId:"NCT99999999",ticker:x.ticker},"post",x),null);
 assert.equal(raasRegistryCoverage({nctId:x.nctId,ticker:x.ticker},"pre",null),null);
});

test("visible TOP/BOTTOM source percentages must not be labeled predictive RAAS",()=>{
 const ui=fs.readFileSync(path.join(root,"app/RaasFullUniverseScores.tsx"),"utf8");
 assert.match(ui,/data-raas-top-source-coverage=\{x\.row\.nctId\}/);
 assert.match(ui,/data-raas-bottom-source-coverage=\{x\.row\.nctId\}/);
 assert.match(ui,/not clinical success probability/);
 assert.match(ui,/or a numerical overall RAAS grade/);
 const compiled=ts.transpileModule(ui,{fileName:"RaasFullUniverseScores.tsx",
 reportDiagnostics:true,compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}});
 assert.deepEqual((compiled.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error),[]);
});
