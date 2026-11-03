"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const primary=require("../new-platform/frontend/data/raas-active-2024-2025-primary-source-leads.json");
const earlier=require("../new-platform/frontend/data/raas-active-2024-2025-preentry-sec-share-leads.json");
const later=require("../new-platform/frontend/data/raas-active-2024-2025-sec-cover-share-leads.json");
const {allWindows}=require("../scripts/raas_historical_provisional_window_grid.cjs");
const {goalVersions,assess,build,stringifyCSV}=require("../scripts/raas_active_2024_2025_full_90_3_grid.cjs");
const date=(s,n)=>new Date(Date.parse(s+"T00:00:00Z")+n*86400000).toISOString().slice(0,10);
const clone=x=>structuredClone(x);
const find=t=>primary.records.find(x=>x.ticker===t);
const share=t=>later.records.find(x=>x.ticker===t);
const earlierShare=t=>earlier.records.find(x=>x.ticker===t);
const base=(override={})=>build({primary,earlier,later,...override});
const makeResearch=()=>{
 const cases=primary.records.map(e=>({
  caseId:e.caseId,ticker:e.ticker,pdufaTargetDate:e.pdufaTargetDate,
  actualFDAActionDate:e.actualFDAActionDate,
  source:"ALPACA_SIP_RAW_CLOSE_X_SEC_COVER_SHARES",
  priceReturnSource:"ALPACA_SIP_ADJUSTMENT_ALL_SEPARATE",
  eventTradeCasesValidated:0,approvedRaasRatings:0,observations:[]
 }));
 return {scope:"RAAS_ACTIVE_2024_2025_ORIGINAL_SOURCE_LEADS_AND_ALPACA_CAP_RESEARCH",
  status:"2024_2025_SOURCE_LEADS_UNVALIDATED_PRICE_RESEARCH",
  validatedTradingCases:0,approvedRaasMetrics:0,fullYearCensusesAudited:0,
  selectedOptimalWindow:null,allResearchOnly:true,priceDataRawAndAdjusted:cases};
};
const bar=(e,d,price,adjusted)=>({session:d,rawClose:price,
 adjustedClose:adjusted,sourceUrl:share(e.ticker).sourceUrl,
 beforeActualFDAAction:d<e.actualFDAActionDate});
test("Full 90-to-3 range includes all 3828 strictly ordered pairs; 79/14 is ordinary",()=>{
 const windows=allWindows();
 assert.equal(windows.length,3828);
 assert.deepEqual(windows[0],{entryLeadDays:90,exitLeadDays:3});
 assert.deepEqual(windows.at(-1),{entryLeadDays:4,exitLeadDays:3});
 assert.ok(windows.some(x=>x.entryLeadDays===79&&x.exitLeadDays===14));
 for(const w of windows){
  assert.ok(w.entryLeadDays>=4&&w.entryLeadDays<=90);
  assert.ok(w.exitLeadDays>=3&&w.exitLeadDays<w.entryLeadDays);
 }
 const result=base();
 assert.equal(result.status,"BLOCKED_NO_ALPACA_BARS");
 assert.equal(result.uniqueEntryExitPairsPerGoalVersion,3828);
 assert.equal(result.goalVersionCaseSets,11);
 assert.equal(result.totalGoalCaseWindowEvaluations,42108);
 assert.equal(result.approvedBestEntryExitWindow,null);
 assert.equal(result.validatedTradingCases,0);
});
test("Source-corrected 2024 case uses separate adjusted return and RAW cap across arbitrary 88-to-13 pair",()=>{
 const e=find("ARQT"),research=makeResearch();
 const entry=date(e.pdufaTargetDate,-88),exit=date(e.pdufaTargetDate,-13);
 const r=research.priceDataRawAndAdjusted.find(x=>x.caseId===e.caseId);
 r.observations=[bar(e,entry,10,5),bar(e,exit,12,6)];
 const g=goalVersions(e)[0];
 assert.equal(g.version,"FINAL_AS_PUBLISHED");
 const x=assess(e,g,{entryLeadDays:88,exitLeadDays:13},r.observations,[earlierShare("ARQT"),share("ARQT")]);
 assert.equal(x.reason,"PROVISIONAL_UNVERIFIED_ELIGIBILITY");
 assert.equal(x.provisionalGrossReturnPct,20);
 assert.equal(x.provisionalNetReturnPct,19);
 assert.equal(x.provisionalCapUsdMillions,
  Math.round(10*earlierShare("ARQT").sharesOutstanding/10000)/100);
 assert.equal(x.shareSourceAtEntry,earlierShare("ARQT").sourceUrl);
 assert.equal(x.verifiedTrade,false);
 assert.equal(x.approvedRAASScore,null);
 const report=base({research});
 assert.equal(report.totalGoalCaseWindowEvaluations,42108);
 assert.ok(report.researchWindowCount>0);
 const w=report.windowSummaries.find(x=>x.targetVersion==="FINAL_AS_PUBLISHED"&&
  x.entryLeadDays===88&&x.exitLeadDays===13);
 assert.equal(w.training2024.n,1);
 assert.equal(w.training2024.meanGrossPct,20);
 assert.equal(w.holdout2025.n,0);
 assert.equal(w.approvedWinner,false);
 assert.equal(report.approvedBestEntryExitWindow,null);
 assert.ok(stringifyCSV(report).includes("PROVISIONAL_UNVERIFIED_ELIGIBILITY"));
});
test("PDUFA goal revision and unpublished Phase 3 prevent after-the-fact window selection",()=>{
 const e=find("SLNO");
 const v=goalVersions(e);
 assert.equal(v.length,2);
 assert.equal(v[0].version,"ORIGINAL_AS_PUBLISHED");
 assert.equal(v[1].version,"FINAL_AS_PUBLISHED");
 const before=assess(e,v[1],{entryLeadDays:90,exitLeadDays:3},[],
  [earlierShare("SLNO"),share("SLNO")]);
 assert.equal(before.reason,"MISSING_ALPACA_RAW_AND_ADJUSTED_BARS");
 const copied={...v[0],sourceUrl:"https://source.example.com/known-original"};
 const revisedWindow=assess(e,copied,{entryLeadDays:70,exitLeadDays:3},[],
  [earlierShare("SLNO"),share("SLNO")]);
 assert.ok(["ORIGINAL_GOAL_REVISED_BEFORE_PLANNED_EXIT",
  "GOAL_DATE_NOT_PUBLIC_BY_PLANNED_ENTRY"].includes(revisedWindow.reason));
 const e2=find("CYTK"),v2=goalVersions(e2);
 assert.equal(v2.length,2);
 const p=assess(e2,v2[0],{entryLeadDays:60,exitLeadDays:3},[],
  [earlierShare("CYTK"),share("CYTK")]);
 assert.ok(["ORIGINAL_GOAL_REVISED_BEFORE_PLANNED_EXIT",
  "INDEPENDENT_ORIGINAL_GOAL_SOURCE_URL_NOT_RECORDED"].includes(p.reason));
});
test("Early FDA action censored before exit even if retrospectively observed bars exist",()=>{
 const e=find("BBIO"),g=goalVersions(e)[0],entry=date(e.pdufaTargetDate,-45);
 const plannedExit=date(e.pdufaTargetDate,-3);
 const observed=[bar(e,entry,30,30),bar(e,plannedExit,35,35)];
 const o=assess(e,g,{entryLeadDays:45,exitLeadDays:3},observed,
  [earlierShare("BBIO"),share("BBIO")]);
 assert.equal(o.reason,"FDA_ACTION_BEFORE_PLANNED_EXIT_CENSORS_WINDOW");
 assert.equal(o.provisionalGrossReturnPct,null);
});
test("A later-dated SEC filing must not enter an earlier stock-cap calculation",()=>{
 const e=find("ARQT"),g=goalVersions(e)[0],entry=date(e.pdufaTargetDate,-88),
  exit=date(e.pdufaTargetDate,-13);
 const x=assess(e,g,{entryLeadDays:88,exitLeadDays:13},[
  bar(e,entry,10,10),bar(e,exit,12,12)
 ],[earlierShare("ARQT"),share("ARQT")]);
 assert.equal(x.shareSourceAtEntry,earlierShare("ARQT").sourceUrl);
 assert.notEqual(x.shareSourceAtEntry,share("ARQT").sourceUrl);
});
test("An invented, missing, duplicate or after-FDA price bar never produces a validated trade",()=>{
 const e=find("ARQT"),r=makeResearch();
 r.priceDataRawAndAdjusted.find(x=>x.caseId===e.caseId).observations=[
  bar(e,"2024-04-10",10,5),bar(e,"2024-04-10",11,6)];
 assert.throws(()=>base({research:r}),/RAAS_T90_T3_BAR_PROVENANCE_INVALID/);
 const broken=makeResearch();
 broken.priceDataRawAndAdjusted[0].eventTradeCasesValidated=1;
 assert.throws(()=>base({research:broken}),/RAAS_T90_T3_PRICE_CASE_IDENTITY_INVALID/);
});
