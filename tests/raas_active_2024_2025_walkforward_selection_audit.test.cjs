"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const {stats,rankRows,build,csv}=require("../scripts/raas_active_2024_2025_walkforward_selection_audit.cjs");
const cases=Array.from({length:9},(_,i)=>({caseId:"CASE-"+i,
 ticker:"X"+i,cohortYear:i<5?2024:2025}));
const points=[[35,12],[76,63],[76,52],[75,63],[79,14]];
const values={
 "35|12":[8,9,10,11,12,-3,0,1,2],
 "76|63":[5,5,5,5,5,10,10,10,10],
 "76|52":[4,4,4,4,4,8,8,8,8],
 "75|63":[3,3,3,3,3,7,7,7,7],
 "79|14":[-5,-5,-5,-5,-5,-2,-2,-2,-2]
};
function row(c,e,x,gross=null,version="FINAL_AS_PUBLISHED"){
 return {caseId:c.caseId,ticker:c.ticker,cohortYear:c.cohortYear,
  targetVersion:version,targetYear:c.cohortYear,entryLeadDays:e,exitLeadDays:x,
  verifiedTrade:false,approvedRAASScore:null,
  reason:gross===null?"MISSING_ENTRY_OR_EXIT_SESSION":"PROVISIONAL_UNVERIFIED_ELIGIBILITY",
  provisionalGrossReturnPct:gross,provisionalNetReturnPct:gross===null?null:gross-1,
  provisionalCapUsdMillions:gross===null?null:500,
  entrySession:gross===null?null:"2024-01-01",exitSession:gross===null?null:"2024-01-10",
  shareSourceAtEntry:gross===null?null:"https://www.sec.gov/Archives/foo"};
}
function smallRows(){
 return points.flatMap(([e,x])=>cases.map((c,i)=>row(c,e,x,values[e+"|"+x][i])));
}
function fullFixture(){
 const rows=[];
 for(let e=90;e>=4;e--)for(let x=3;x<e;x++){
  for(const [i,c] of cases.entries()){
   const v=values[e+"|"+x],gross=v?v[i]:null;
   rows.push(row(c,e,x,gross));
  }
  for(const c of cases.slice(7))rows.push(row(c,e,x,null,"ORIGINAL_AS_PUBLISHED"));
 }
 return {scope:"RAAS_ACTIVE_2024_2025_FULL_T90_T3_RESEARCH_GRID_ONLY",
  status:"PROVISIONAL_SELECTED_CASE_PRICE_GRID_NOT_VALIDATED",
  uniqueEntryExitPairsPerGoalVersion:3828,
  totalGoalCaseWindowEvaluations:42108,
  goalVersionCaseSets:11,allSourceCases:9,
  validatedMarketCapCases:0,validatedTradingCases:0,approvedRAASMetrics:0,
  approvedBestEntryExitWindow:null,comparisonWindowSelected:null,
  independentlyPriceVerified:false,completeTwoYearFDACensus:false,
  cohortSplitRule:"FINAL_PUBLIC_PDUFA_GOAL_YEAR_REGARDLESS_OF_ORIGINAL_GOAL_VERSION",
  researchWindowCount:45,caseWindows:rows};
}
test("2024-only training ranking cannot select based on four 2025 outcomes",()=>{
 const result=rankRows(smallRows());
 assert.equal(result.trainFullCoveragePairs,5);
 assert.equal(result.allNineFullCoveragePairs,5);
 assert.equal(result.candidateTrainOnly.entryLeadDays,35);
 assert.equal(result.candidateTrainOnly.exitLeadDays,12);
 assert.equal(result.candidateTrainOnly.train2024.meanGrossPct,10);
 assert.equal(result.candidateTrainOnly.holdout2025.meanGrossPct,0);
 assert.equal(result.candidatePooledLookahead.entryLeadDays,76);
 assert.equal(result.candidatePooledLookahead.exitLeadDays,63);
 assert.equal(result.candidatePooledLookahead.all2024To2025.meanGrossPct,7.22);
 assert.equal(result.trainingRank76to63,2);
 assert.equal(result.candidatePooledLookahead.approved,false);
 assert.equal(result.preObservedWindows.length,4);
});
test("A two-year report is still unapproved with exactly 3828 candidate pairs",()=>{
 const input=fullFixture();
 assert.equal(input.caseWindows.length,42108);
 const report=build(input);
 assert.equal(report.status,"RESEARCH_ONLY_NO_APPROVED_TRADING_WINDOW");
 assert.equal(report.fullGridPairsPresent,3828);
 assert.equal(report.observed2024Cases,5);
 assert.equal(report.observed2025Cases,4);
 assert.equal(report.validatedTrades,0);
 assert.equal(report.approvedBestEntryExit,null);
 assert.equal(report.provisionalCaseWindows,45);
 const output=csv(report);
 assert.ok(output.startsWith("label,selectionMethod,entryLeadDays"));
 assert.match(output,/SELECTED_FROM_2024_TRAIN_ONLY/);
 assert.match(output,/NOT_INDEPENDENT/);
});
test("Source and study-date falsification fails closed",()=>{
 const input=fullFixture();
 for(const corrupt of [
  {validatedTradingCases:1},{approvedBestEntryExitWindow:{entry:76,exit:63}},
  {independentlyPriceVerified:true},{fullTwoYearFDACensus:true},
  {researchWindowCount:999},
  {cohortSplitRule:"ORIGINAL_GOAL_YEAR"}
 ])assert.throws(()=>build({...input,...corrupt}),/RAAS_WALKFORWARD_/,
   "Must reject "+JSON.stringify(corrupt));
 const bad=structuredClone(input);
 bad.caseWindows[0].approvedRAASScore=81;
 assert.throws(()=>build(bad),/RAAS_WALKFORWARD_CLAIMED_APPROVAL_INVALID/);
});
test("Invalid source caps, calculated net costs and duplicate issuer-window pairs fail closed",()=>{
 const a=smallRows();
 const dup=[...a,a[0]];
 assert.throws(()=>rankRows(dup),/DUPLICATE_CASE_AND_WINDOW/);
 const bad=structuredClone(a);
 bad[0].provisionalNetReturnPct=999;
 assert.throws(()=>rankRows(bad),/CASE_RETURN_OR_CAP_INVALID/);
 const bad2=structuredClone(a);
 bad2[0].provisionalCapUsdMillions=5;
 assert.throws(()=>rankRows(bad2),/CASE_RETURN_OR_CAP_INVALID/);
});
test("A positive win rate cannot be inferred for missing trade bars",()=>{
 const out=stats([]);
 assert.equal(out.cases,0);
 assert.equal(out.meanGrossPct,null);
 assert.equal(out.winRatePct,null);
 assert.equal(out.wins,0);
 assert.throws(()=>stats([{provisionalGrossReturnPct:null}]),/UNVERIFIED_ROW_AS_RETURN/);
});
