"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,file);
const lib=require("../lib/raas-corporate-action-audit.ts");
const pre=require("../lib/raas-top-retrospective-intake.ts").parseTopRetrospective(require("../data/raas-retrospective-top-cases.json"));
const post=require("../lib/raas-retrospective-intake.ts").parseRetrospectiveFeed(require("../data/raas-retrospective-source-cases.json"));
const source=require("../data/raas-corporate-actions-research.json");
test("historic corporate action dates correctly partition eight study windows and never certify adjusted returns",()=>{
 const feed=lib.parseCorporateActions(source),overall=lib.corporateActionSummary(feed,pre,post);
 assert.equal(feed.records.length,3);
 assert.equal(overall.cases,8);
 assert.equal(overall.withPartialActionHistory,5);
 assert.equal(overall.withoutActionHistory,3);
 assert.equal(overall.verifiedAdjustedReturns,0);
 assert.equal(overall.approvedRAASPredictions,0);
 for(const example of [...pre.records,...post.records]){
  const r=lib.corporateActionsForCase(feed,pre,post,example.id);
  assert.equal(r.adjustedTotalReturnVerified,false);
  assert.equal(r.actionHistoryComplete,false);
  assert.equal(r.approvedRAAS,false);
  assert.ok(r.blockers.length>=3);
 }
});
test("GERN 2014 split/distribution and Asterias spinoff predate both its study windows",()=>{
 const feed=lib.parseCorporateActions(source);
 for(const id of ["gern-imerge-mds-pre2023-illustrative","gern-imetelstat-mds-2024-illustrative"]){
  const r=lib.corporateActionsForCase(feed,pre,post,id);
  assert.equal(r.knownBefore,2);assert.equal(r.eventsDuringWindow,0);
  assert.ok(r.listedEvents.every(x=>x.placement==="BEFORE_WINDOW"));
 }
});
test("MDGL 2016 reverse split predates both windows; Verona merger occurred after its 2024 window",()=>{
 const feed=lib.parseCorporateActions(source);
 for(const id of ["mdgl-resmetirom-maestro-nash-pre2022-illustrative","mdgl-resmetirom-nash-2023-2024-illustrative"]){
  const r=lib.corporateActionsForCase(feed,pre,post,id);
  assert.equal(r.knownBefore,1);
  assert.equal(r.eventsDuringWindow,0);
 }
 const vrna=lib.corporateActionsForCase(feed,pre,post,"vrna-ensifentrine-copd-2024-illustrative");
 assert.equal(vrna.knownAfter,1);
 assert.equal(vrna.adsOrdinaryShares,8);
 assert.equal(vrna.eventsDuringWindow,0);
 assert.equal(vrna.listedEvents[0].event.cashPerQuotedSecurityUsd,107);
});
test("No source for BBIO or URGN is NOT interpreted as proof of no in-window events",()=>{
 const feed=lib.parseCorporateActions(source);
 for(const id of ["bbio-acoramidis-attrcm-2024-illustrative","urgn-ugn102-nmibc-2025-illustrative"]){
  const row=lib.corporateActionsForCase(feed,pre,post,id);
  assert.equal(row.researchStatus,"NO_ACTION_SOURCE_IMPORTED");
  assert.equal(row.actionHistoryComplete,false);
  assert.ok(row.blockers.some(x=>/No issuer\/exchange/.test(x)));
 }
});
test("Bad ADS conversion, future actions, missing split factor and invalid cash merger reject",()=>{
 const records=source.records;
 const change=(idx,patch)=>({...source,records:records.map((r,i)=>i===idx?{...r,...patch}:r)});
 assert.throws(()=>lib.parseCorporateActions(change(2,{adsOrdinaryShares:1})),/RAAS_ACTION_RECORD_INVALID/);
 const badDate=change(2,{events:records[2].events.map(e=>({...e,date:"2027-01-01"}))});
 assert.throws(()=>lib.parseCorporateActions(badDate),/RAAS_ACTION_EVENT_INVALID/);
 const missingFactor=change(1,{events:records[1].events.map(e=>({...e,factorDenominator:undefined}))});
 assert.throws(()=>lib.parseCorporateActions(missingFactor),/RAAS_ACTION_FACTOR_MISSING/);
 const merger=change(2,{events:records[2].events.map(e=>({...e,cashPerQuotedSecurityUsd:-1}))});
 assert.throws(()=>lib.parseCorporateActions(merger),/RAAS_ACTION_MERGER_CASH_INVALID/);
});
test("Corporate action module and Next.js audit page parse",()=>{
 for(const p of ["lib/raas-corporate-action-audit.ts","app/raas-history/page.tsx"]){
  const r=ts.transpileModule(fs.readFileSync(path.join(__dirname,"..",p),"utf8"),{fileName:p,reportDiagnostics:true,compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}});
  assert.deepEqual((r.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error).map(d=>d.messageText),[],p);
 }
});
