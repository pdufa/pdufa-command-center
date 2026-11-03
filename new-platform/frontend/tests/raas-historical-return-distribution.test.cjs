"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(module,file)=>module._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
  module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022
 }}).outputText,file);
const topLib=require("../lib/raas-top-retrospective-intake.ts");
const bottomLib=require("../lib/raas-retrospective-intake.ts");
const priceLib=require("../lib/raas-price-crosschecks.ts");
const {analyzeRaasHistoricalReturns:analyze}=require("../lib/raas-historical-return-distribution.ts");
const top=topLib.parseTopRetrospective(require("../data/raas-retrospective-top-cases.json"));
const bottom=bottomLib.parseRetrospectiveFeed(require("../data/raas-retrospective-source-cases.json"));
const checks=priceLib.parsePriceCrosschecks(
 require("../data/raas-price-crosschecks.json"),top,bottom);
const report=analyze(top,bottom,checks);
test("Eight real historical selected windows produce transparent stage distributions",()=>{
 assert.equal(report.windows.length,8);
 assert.equal(report.totalUniqueIssuers,5);
 assert.equal(report.yearRange,"2022–2025");
 assert.equal(report.top.count,3);
 assert.equal(report.top.winCount,2);
 assert.equal(report.top.meanGrossPercent,6.49);
 assert.equal(report.top.medianGrossPercent,7.08);
 assert.equal(report.top.meanAfterOnePercentCost,5.49);
 assert.equal(report.top.minimumGrossPercent,-12.36);
 assert.equal(report.top.maximumGrossPercent,24.74);
 assert.equal(report.bottom.count,5);
 assert.equal(report.bottom.winCount,2);
 assert.equal(report.bottom.meanGrossPercent,2.65);
 assert.equal(report.bottom.medianGrossPercent,-9.67);
 assert.equal(report.bottom.medianAfterOnePercentCost,-10.67);
 assert.equal(report.bottom.minimumGrossPercent,-33.42);
 assert.equal(report.bottom.maximumGrossPercent,73.82);
 assert.deepEqual(report.bottom.leaveOneOutMeanRange,{min:-15.14,max:11.67});
 assert.equal(report.top.positiveAfterOnePercentCostCount,2);
 assert.equal(report.bottom.positiveAfterOnePercentCostCount,2);
});
test("Price provenance does not silently become an adjusted return or archived prediction",()=>{
 assert.equal(report.nominalPricePoints,16);
 assert.equal(report.nominalSecondSourcePointsMatched,14);
 assert.equal(report.top.bothClosesSecondSourceMatched,1);
 assert.equal(report.bottom.bothClosesSecondSourceMatched,5);
 assert.equal(report.originalRaasPredictions,0);
 assert.equal(report.adjustedTotalReturnVerified,0);
 assert.equal(report.eligibleCalibrations,0);
 assert.ok(report.windows.every(x=>x.adjustedTotalReturnVerified===false&&
  x.historicalPredictionRecorded===false));
});
test("Relative event-window offsets preserve published pre-readout and PDUFA chronology",()=>{
 const caseByTicker=(t,stage)=>report.windows.find(x=>x.ticker===t&&x.stage===stage);
 const gern=caseByTicker("GERN","pre");
 assert.equal(gern.daysEntryToScheduledEvent,47);
 assert.equal(gern.daysExitToScheduledEvent,5);
 assert.equal(gern.holdingCalendarDays,42);
 const mdgl=caseByTicker("MDGL","pre");
 assert.equal(mdgl.daysExitToScheduledEvent,3);
 const postGern=caseByTicker("GERN","post");
 assert.equal(postGern.daysExitToScheduledEvent,16);
 assert.equal(postGern.daysExitToActualOutcome,6);
 assert.ok(report.windows.every(x=>x.daysExitToScheduledEvent>0&&
  x.holdingCalendarDays>0));
});
test("Historical analytic cohort refuses duplicate or reversed windows",()=>{
 const f=structuredClone(top);
 f.records[1].id=f.records[0].id;
 assert.throws(()=>analyze(f,bottom,checks),/RAAS_DISTRIBUTION_WINDOW_INVALID/);
 const b=structuredClone(bottom);
 b.records[0].exit.date=b.records[0].entry.date;
 assert.throws(()=>analyze(top,b,checks),/RAAS_DISTRIBUTION_WINDOW_INVALID/);
});
test("Historical distribution is on the audit page but never labeled calibrated predictive RAAS",()=>{
 const root=path.resolve(__dirname,"..");
 const page=fs.readFileSync(path.join(root,"app/raas-history/page.tsx"),"utf8");
 for(const marker of ["analyzeRaasHistoricalReturns","data-raas-return-cohort","medianGrossPercent",
  "meanAfterOnePercentCost","leaveOneOutMeanRange","Retrospectively selected"]){
  assert.ok(page.includes(marker),marker);
 }
 assert.match(page,/Not a validated return forecast/);
 for(const name of ["lib/raas-historical-return-distribution.ts","app/raas-history/page.tsx"]){
  const res=ts.transpileModule(fs.readFileSync(path.join(root,name),"utf8"),{
   fileName:name,reportDiagnostics:true,compilerOptions:{
    target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,jsx:ts.JsxEmit.ReactJSX
   }});
  assert.deepEqual((res.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error)
   .map(d=>ts.flattenDiagnosticMessageText(d.messageText," ")),[],name);
 }
});
