"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
 module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,file);
const engine=require("../lib/raas-historical-backtest.ts");
const metric=require("../lib/raas-metric-backtest.ts");
const productionEvents=require("../data/raas-historical-cases.json");
const productionScores=require("../data/raas-historical-metric-snapshots.json");
// All following examples are entirely synthetic and never saved to production evidence files.
const sourceDate="2025-05-05";
const price=(date,adjustedClose)=>({date,adjustedClose,currency:"USD",
 sourceUrl:"https://example.org/synthetic-price",sourcePublishedAt:sourceDate});
const caseA={
 caseId:"synthetic-a",nctIds:["NCT12345678"],ticker:"TEST",drug:"LAB-1",indication:"Test disorder",
 stage:"pre",marketCapUsdMillions:600,marketCapSourceUrl:"https://example.org/cap",
 marketCapSourcePublishedAt:"2025-01-08",
 featureAsOf:"2025-01-09",predictionPublishedAt:"2025-01-09",
 entryDate:"2025-01-10",exitDate:"2025-02-03",
 phase3ReadoutDate:"2025-02-10",phase3ReadoutSourceUrl:"https://example.org/readout",
 phase3ReadoutSourcePublishedAt:"2025-02-10",
 entryPrice:price("2025-01-10",10),exitPrice:price("2025-02-03",15),
 predictedRaas:null,predictedReturnPercent:null,roundTripCostsPercent:1,
 featureSources:[{sourceUrl:"https://example.org/synthetic-research",publishedAt:"2025-01-08"}]
};
const rating=(overrides={})=>({
 caseId:"synthetic-a",nctId:"NCT12345678",ticker:"TEST",drug:"LAB-1",indication:"Test disorder",
 stage:"pre",metricId:"pre-1-1",score:75,benchmarkId:"synthetic-bench",
 ruleVersion:"synthetic-v1",assessedAt:"2025-01-09",
 sourceUrl:"https://example.org/synthetic-research",
 sourcePublishedAt:"2025-01-08",method:"synthetic only",...overrides
});
const back=(cases)=>engine.parseHistoricalFeed({...productionEvents,sourceAsOf:sourceDate,cases});
const grade=(records)=>metric.parseMetricHistory({...productionScores,sourceAsOf:sourceDate,records});
test("No fabricated metric or stock cases are passed off as calibrated history",()=>{
 const h=back([]),r=grade([]);
 const report=metric.evaluateMetricHistory(h,engine.evaluateHistoricalFeed(h),r);
 assert.equal(report.length,60);
 assert.ok(report.every(x=>x.independentPrograms===0&&x.status==="INSUFFICIENT_EVIDENCE"));
});
test("Exact pre-entry metric grade joins to source-supported historical outcome, not a certified RAAS score",()=>{
 const h=back([caseA]);
 const report=metric.evaluateMetricHistory(h,engine.evaluateHistoricalFeed(h),grade([rating()]));
 const a=report.find(x=>x.metricId==="pre-1-1");
 assert.equal(a.independentPrograms,1);
 assert.equal(a.observedReturnPairs,1);
 assert.equal(a.positiveReturnRateHigh,100);
 assert.equal(a.spearmanScoreToReturn,null);
 assert.equal(a.status,"INSUFFICIENT_EVIDENCE");
});
test("Future scores, future sources, wrong NCT, or wrong drug are rejected",()=>{
 const candidates=[
  rating({sourcePublishedAt:"2025-02-11",assessedAt:"2025-02-11"}),
  rating({assessedAt:"2025-02-11"}),
  rating({nctId:"NCT00000000"}),
  rating({drug:"other treatment"})
 ];
 for(const r of candidates){
  const h=back([caseA]);
  const out=metric.evaluateMetricHistory(h,engine.evaluateHistoricalFeed(h),grade([r]));
  assert.equal(out.find(x=>x.metricId==="pre-1-1").independentPrograms,0);
 }
});
test("Multiple NCTs of same drug program count once",()=>{
 const b={...caseA,caseId:"synthetic-b",nctIds:["NCT87654321"],
  entryDate:"2025-01-13",featureAsOf:"2025-01-10",
  predictionPublishedAt:"2025-01-10",entryPrice:price("2025-01-13",11)};
 const h=back([caseA,b]);
 const r=grade([rating(),rating({caseId:"synthetic-b",nctId:"NCT87654321",assessedAt:"2025-01-10"})]);
 const report=metric.evaluateMetricHistory(h,engine.evaluateHistoricalFeed(h),r);
 assert.equal(report.find(x=>x.metricId==="pre-1-1").independentPrograms,1);
});
test("Metric backtest TypeScript parses cleanly",()=>{
 const source=fs.readFileSync(path.join(__dirname,"../lib/raas-metric-backtest.ts"),"utf8");
 const out=ts.transpileModule(source,{fileName:"raas-metric-backtest.ts",reportDiagnostics:true,
 compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}});
 assert.equal((out.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error).length,0);
});
