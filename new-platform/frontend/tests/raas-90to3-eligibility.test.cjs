"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(module,file)=>module._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}
).outputText,file);
const {parseTopRetrospective}=require("../lib/raas-top-retrospective-intake.ts");
const {parseRetrospectiveFeed}=require("../lib/raas-retrospective-intake.ts");
const {parseShareBridge}=require("../lib/raas-share-bridge.ts");
const {parsePriceCrosschecks}=require("../lib/raas-price-crosschecks.ts");
const {analyzeRaasHistoricalReturns}=require("../lib/raas-historical-return-distribution.ts");
const {auditRaasNinetyToThree}=require("../lib/raas-90to3-eligibility.ts");
const top=parseTopRetrospective(require("../data/raas-retrospective-top-cases.json"));
const bottom=parseRetrospectiveFeed(require("../data/raas-retrospective-source-cases.json"));
const share=parseShareBridge(require("../data/raas-share-bridge-research.json"),top,bottom);
const price=parsePriceCrosschecks(require("../data/raas-price-crosschecks.json"),top,bottom);
const returns=analyzeRaasHistoricalReturns(top,bottom,price);
const report=auditRaasNinetyToThree(returns,top,bottom,share,price);
test("Only five of eight retrospectively picked historical windows meet 90-to-3 calendar timing",()=>{
 assert.equal(report.rows.length,8);
 assert.equal(report.calendarWindowCount,5);
 assert.equal(report.topCalendarCount,3);
 assert.equal(report.bottomCalendarCount,2);
 assert.equal(report.issuerCapInRangeCount,8);
 assert.equal(report.matchingCapBridgeCount,6);
 assert.equal(report.eligibleForSourceFollowUpCount,3);
 assert.equal(report.eligibleForValidatedRaas,0);
 assert.equal(report.scope,"RETROSPECTIVE_90_TO_3_DAYS_300M_TO_10B_RESEARCH_ONLY");
});
test("Historical calendar ineligible programs retain dates and cannot skew the filtered cohort",()=>{
 const byId=Object.fromEntries(report.rows.map(r=>[r.caseId,r]));
 const urg=byId["urgn-ugn102-nmibc-2025-illustrative"];
 assert.equal(urg.entryDaysBeforeEvent,91);
 assert.equal(urg.eligibleCalendarWindow,false);
 const mdgl=byId["mdgl-resmetirom-nash-2023-2024-illustrative"];
 assert.equal(mdgl.entryDaysBeforeEvent,132);
 assert.equal(mdgl.eligibleCalendarWindow,false);
 assert.equal(mdgl.secBridgeAgreesWithin2Pct,false);
 const bbio=byId["bbio-acoramidis-attrcm-2024-illustrative"];
 assert.equal(bbio.entryDaysBeforeEvent,203);
 assert.equal(bbio.eligibleCalendarWindow,false);
 assert.equal(bbio.secBridgeAgreesWithin2Pct,false);
});
test("Source-qualified FOLLOW-UP is separate from verified trades and future-known TOP dates",()=>{
 const rows=report.rows.filter(r=>r.eligibleForSourceFollowUp);
 assert.deepEqual(rows.map(r=>r.ticker).sort(),["BBIO","GERN","VRNA"]);
 assert.ok(report.rows.every(r=>r.eligibleForValidatedRaas===false));
 assert.ok(report.rows.filter(r=>r.stage==="pre").every(r=>
  r.historicalReference==="ACTUAL_READOUT_RETROSPECTIVE"&&
  r.blockers.some(x=>x.includes("known only retrospectively"))));
 assert.ok(report.rows.filter(r=>r.stage==="post").every(r=>
  r.historicalReference==="PDUFA_TARGET_KNOWN_AT_ENTRY"));
});
test("Loss of a second-provider quote cannot turn a case into validated source follow-up",()=>{
 const next=structuredClone(price);
 next.observations=next.observations.filter(x=>
  !(x.caseId==="bbio-attribute-cm-pre2023-illustrative"&&x.side==="ENTRY"));
 const r=auditRaasNinetyToThree(returns,top,bottom,share,next);
 assert.equal(r.eligibleForSourceFollowUpCount,2);
 assert.ok(r.rows.find(x=>x.ticker==="BBIO"&&x.stage==="pre").blockers.some(x=>
  x.includes("Independent exact-date")));
});
test("Filter rejects unpaired roster and never synthesizes a return estimate",()=>{
 const mismatched=structuredClone(returns);
 mismatched.windows.pop();
 assert.throws(()=>auditRaasNinetyToThree(mismatched,top,bottom,share,price),
  /RAAS_WINDOW_FILTER_ROSTER_INVALID/);
 const modified=structuredClone(returns);
 modified.windows[0].ticker="MISMATCH";
 assert.throws(()=>auditRaasNinetyToThree(modified,top,bottom,share,price),
  /RAAS_WINDOW_FILTER_IDENTITY_INVALID/);
});
test("90-to-3 filter renders on historical audit page, not on approved RAAS score ledger",()=>{
 const root=path.resolve(__dirname,"..");
 const page=fs.readFileSync(path.join(root,"app/raas-history/page.tsx"),"utf8");
 assert.ok(page.includes("data-raas-90-to-3-eligibility"));
 assert.ok(page.includes("filteredWindows.eligibleForSourceFollowUpCount"));
 assert.ok(page.includes("ACTUAL_READOUT_RETROSPECTIVE")===false);
 assert.ok(page.includes("actual readout date known in hindsight"));
 assert.ok(page.includes("0 validated trades"));
 for(const rel of ["lib/raas-90to3-eligibility.ts","app/raas-history/page.tsx"]){
  const parsed=ts.transpileModule(fs.readFileSync(path.join(root,rel),"utf8"),{
   fileName:rel,reportDiagnostics:true,compilerOptions:{
    module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX
   }});
  assert.deepEqual((parsed.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error)
   .map(x=>ts.flattenDiagnosticMessageText(x.messageText," ")),[],rel);
 }
});
