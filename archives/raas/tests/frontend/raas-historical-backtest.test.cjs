"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>{
 const src=fs.readFileSync(file,"utf8");
 mod._compile(ts.transpileModule(src,{fileName:file,compilerOptions:{
  module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022
 }}).outputText,file);
};
const b=require("../lib/raas-historical-backtest.ts");
const empty=require("../data/raas-historical-cases.json");
const source=(date)=>({sourceUrl:"https://example.org/synthetic-evidence",publishedAt:date});
const price=(date,adjustedClose)=>({date,adjustedClose,currency:"USD",sourceUrl:"https://example.org/synthetic-prices",sourcePublishedAt:"2025-05-05"});
// SYNTHETIC test-only stock/event records. None are uploaded as real performance evidence.
function top(overrides={}){
 return {caseId:"test-top-a",nctIds:["NCT00000001"],ticker:"DEMO",drug:"TEST-1",indication:"Example disease",stage:"pre",
  marketCapUsdMillions:500,marketCapSourceUrl:"https://example.org/cap",marketCapSourcePublishedAt:"2025-01-07",
  featureAsOf:"2025-01-09",predictionPublishedAt:"2025-01-09",entryDate:"2025-01-10",exitDate:"2025-02-03",
  phase3ReadoutDate:"2025-02-10",phase3ReadoutSourceUrl:"https://example.org/readout",phase3ReadoutSourcePublishedAt:"2025-02-10",
  entryPrice:price("2025-01-10",10),exitPrice:price("2025-02-03",14),
  predictedRaas:80,predictedReturnPercent:35,predictedScenarioSourceUrl:"https://example.org/model",
  roundTripCostsPercent:1,featureSources:[source("2025-01-08")],...overrides};
}
function bottom(overrides={}){
 return {caseId:"test-bottom-a",nctIds:["NCT00000002"],ticker:"POST",drug:"TEST-P",indication:"Other disease",stage:"post",
  marketCapUsdMillions:600,marketCapSourceUrl:"https://example.org/cap",marketCapSourcePublishedAt:"2025-03-05",
  featureAsOf:"2025-03-06",predictionPublishedAt:"2025-03-06",entryDate:"2025-03-07",exitDate:"2025-04-16",
  phase3ReadoutDate:"2025-03-01",phase3ReadoutSourceUrl:"https://example.org/readout",phase3ReadoutSourcePublishedAt:"2025-03-01",
  pdufaDate:"2025-04-20",pdufaSourceUrl:"https://example.org/fda",pdufaSourcePublishedAt:"2025-03-04",
  entryPrice:price("2025-03-07",20),exitPrice:price("2025-04-16",24),
  predictedRaas:70,predictedReturnPercent:20,predictedScenarioSourceUrl:"https://example.org/model",
  roundTripCostsPercent:1,featureSources:[source("2025-03-01")],...overrides};
}
const feed=(cases)=>({...empty,sourceAsOf:"2025-05-05",cases});
test("real historical registry starts empty and does not assert retroactive stock returns",()=>{
 const parsed=b.parseHistoricalFeed(empty);
 const result=b.evaluateHistoricalFeed(parsed);
 assert.equal(parsed.cases.length,0);
 assert.equal(result.accepted.length,0);
 assert.equal(result.excluded.length,0);
 assert.equal(result.byStage.length,2);
 assert.ok(result.byStage.every(x=>!x.calibrationReady&&x.independentPrograms===0));
});
test("TOP and BOTTOM synthetic exact-window returns are measured net of costs",()=>{
 const v=b.evaluateHistoricalFeed(b.parseHistoricalFeed(feed([top(),bottom()])));
 assert.equal(v.accepted.length,2);
 assert.equal(v.accepted[0].realizedReturnPercent,39);
 assert.equal(v.accepted[0].returnErrorPercent,-4);
 assert.equal(v.accepted[1].realizedReturnPercent,19);
 assert.equal(v.accepted[1].returnErrorPercent,1);
 assert.ok(v.byStage.every(x=>!x.calibrationReady));
});
test("future features and retroactive source dates are rejected before calculating ROI",()=>{
 const cases=[
  top({caseId:"lookahead-signal",featureAsOf:"2025-01-12"}),
  top({caseId:"lookahead-source",featureSources:[source("2025-01-11")]}),
  top({caseId:"post-readout-exit",exitDate:"2025-02-10",exitPrice:price("2025-02-10",14)}),
  bottom({caseId:"late-pdufa-evidence",pdufaSourcePublishedAt:"2025-03-10"}),
  bottom({caseId:"too-close-pdufa",exitDate:"2025-04-18",exitPrice:price("2025-04-18",24)}),
  bottom({caseId:"readout-not-public",phase3ReadoutSourcePublishedAt:"2025-03-10"})
 ];
 const v=b.evaluateHistoricalFeed(b.parseHistoricalFeed(feed(cases)));
 assert.equal(v.accepted.length,0);
 assert.equal(v.excluded.length,6);
 assert.ok(v.excluded.every(x=>x.reason));
});
test("two NCT entries for one company drug indication count as one independent program",()=>{
 const t1=top();
 const t2=top({caseId:"same-product-other-nct",nctIds:["NCT00000003"],entryDate:"2025-01-13",
  featureAsOf:"2025-01-11",predictionPublishedAt:"2025-01-11",featureSources:[source("2025-01-09")],
  entryPrice:price("2025-01-13",11)});
 const v=b.evaluateHistoricalFeed(b.parseHistoricalFeed(feed([t1,t2])));
 assert.equal(v.accepted.length,2);
 assert.equal(v.byStage[0].independentPrograms,1);
 assert.equal(v.byStage[0].predictionCoverage,100);
 assert.equal(v.byStage[0].meanRealizedReturnPercent,39);
});
test("walk forward folds use prior exited programs and never mix program IDs",()=>{
 const r=b.evaluateHistoricalFeed(b.parseHistoricalFeed(feed([
  top(),top({caseId:"test-top-later",ticker:"NEXT",nctIds:["NCT00000004"],
   entryDate:"2025-03-10",exitDate:"2025-04-10",
   featureAsOf:"2025-03-09",predictionPublishedAt:"2025-03-09",
   marketCapSourcePublishedAt:"2025-03-06",featureSources:[source("2025-03-08")],
   phase3ReadoutDate:"2025-04-15",phase3ReadoutSourcePublishedAt:"2025-04-15",
   entryPrice:price("2025-03-10",10),exitPrice:price("2025-04-10",12)})
 ])));
 const folds=b.walkForwardFolds(r.accepted,"pre");
 assert.equal(folds.length,1);
 assert.equal(folds[0].trainPrograms,1);
 assert.equal(folds[0].testPrograms,1);
 assert.equal(folds[0].status,"INSUFFICIENT_DATA");
 const training=r.accepted.filter(x=>folds[0].trainIds.includes(x.caseId)).map(x=>x.programKey);
 const testing=r.accepted.filter(x=>folds[0].testIds.includes(x.caseId)).map(x=>x.programKey);
 assert.ok(training.every(x=>!testing.includes(x)));
});
test("TS backtest source parses without syntax errors",()=>{
 const sourceText=fs.readFileSync(path.join(__dirname,"../lib/raas-historical-backtest.ts"),"utf8");
 const res=ts.transpileModule(sourceText,{fileName:"raas-historical-backtest.ts",reportDiagnostics:true,compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}});
 assert.deepEqual((res.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error).map(x=>x.messageText),[]);
});
