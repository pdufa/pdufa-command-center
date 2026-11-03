"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const m=require("../scripts/raas_active_2024_2025_window_robustness_audit.cjs");
function fixture(){
 const tickers=["AA","BB","CC","DD","EE","FF","GG","HH"];
 const gross=[-60,10,0,-5,4,-2,5,-12]; // SYNTHETIC TEST RETURNS ONLY.
 const rows=tickers.map((ticker,i)=>({
  caseId:ticker+"|SYNTHETIC",ticker,year:i<4?2024:2025,
  status:"UNVALIDATED_ALPACA_PRICE_RESEARCH",
  actualFdaOutcomeRetrospective:(i===0||i===7)?"CRL":"APPROVED",
  entryDate:i<4?"2024-07-01":"2025-07-01",
  exitDate:i<4?"2024-09-01":"2025-09-01",
  goalFirstPublicDate:i<4?"2024-01-01":"2025-01-01",
  actualFdaActionDate:i<4?"2024-10-01":"2025-10-01",
  validatedTradingCase:false,approvedRaasMetric:false,
  independentlyVerifiedPrice:false,completeFDAEventCensus:false,
  grossReturnPct:gross[i],hypotheticalNetReturnPct:gross[i]-1,
  entryCapResearchMillions:4000,
 }));
 return {scope:"RAAS_ACTIVE_2024_2025_T79_TO_T14_RESEARCH_AUDIT",
  status:"UNVALIDATED_PROVISIONAL_RETURN_DIAGNOSTIC_ONLY",
  window:{entryLeadCalendarDays:79,exitLeadCalendarDays:14},
  rows,sourceCaseCount:8,blockedCases:0,
  completedFDAFullCensusYears:0,independentlyValidatedTradingCases:0,
  approvedRaasMetrics:0,approvedOptimalWindow:null,
  requiredIndependentTrainIssuers:30,requiredIndependentHoldoutIssuers:30};
}
test("Eight independent synthetic cases quantify extreme single-issuer sensitivity, not a trading strategy",()=>{
 const r=m.build(fixture());
 assert.equal(r.scope,"RAAS_ACTIVE_2024_2025_T79_TO_T14_ROBUSTNESS_ONLY");
 assert.equal(r.status,"UNVALIDATED_SELECTED_SAMPLE_FRAGILITY_DIAGNOSTIC");
 assert.equal(r.all.meanGrossPct,-7.5);
 assert.equal(r.trimmedOneEachGrossMeanPct,-1.67);
 assert.equal(r.mostInfluentialIssuerTicker,"AA");
 assert.equal(r.maxAbsoluteOneIssuerEffectPctPoints,7.5);
 const withoutAA=r.leaveOneIssuerOut.find(x=>x.tickerOmitted==="AA");
 assert.equal(withoutAA.remainingMeanGrossPct,0);
 assert.equal(withoutAA.changeFromAllMeanPctPoints,7.5);
 assert.equal(r.byYear[2024].meanGrossPct,-13.75);
 assert.equal(r.byYear[2025].meanGrossPct,-1.25);
 assert.equal(r.byRetrospectiveOutcome.CRL.cases,2);
 assert.equal(r.byRetrospectiveOutcome.APPROVED.cases,6);
 assert.equal(r.calibrationPermitted,false);
 assert.equal(r.prospectiveFDAOutcomeKnownAtEntry,false);
 assert.equal(r.approvedOptimalWindow,null);
 assert.equal(r.independentlyValidatedTrades,0);
 assert.equal(r.approvedRaasMetrics,0);
});
test("Never accept a validated trade, invented FDA census, optimized window or missing sample",()=>{
 for(const edit of [
  x=>{x.independentlyValidatedTradingCases=1},
  x=>{x.completedFDAFullCensusYears=1},
  x=>{x.approvedRaasMetrics=1},
  x=>{x.approvedOptimalWindow={entry:79}},
  x=>{x.sourceCaseCount=100},
  x=>{x.requiredIndependentHoldoutIssuers=1}
 ]){
  const x=fixture();edit(x);
  assert.throws(()=>m.build(x),/UNTRUSTED_SOURCE/);
 }
});
test("Future announced target, event-window hindsight, and retrospective outcome leakage do not pass",()=>{
 for(const edit of [
  r=>{r[0].goalFirstPublicDate="2024-08-01"},
  r=>{r[0].exitDate="2024-10-02"},
  r=>{r[0].actualFdaOutcomeRetrospective="PREDICTED_APPROVAL"},
  r=>{r[0].independentlyVerifiedPrice=true},
  r=>{r[0].approvedRaasMetric=true}
 ]){
  const x=fixture();edit(x.rows);
  assert.throws(()=>m.build(x),/CASE_OR_CHRONOLOGY_INVALID/);
 }
});
test("Reject one issuer reusing multiple PDUFA rows or leaking between train and holdout",()=>{
 const x=fixture();x.rows[7].ticker="AA";
 assert.throws(()=>m.build(x),/ISSUER_NOT_INDEPENDENT/);
});
test("Missing SEC cap, unbounded loss, distorted net or string returns are rejected",()=>{
 for(const edit of [
  r=>{r.grossReturnPct="4"},
  r=>{r.grossReturnPct=-101},
  r=>{r.entryCapResearchMillions=200},
  r=>{r.hypotheticalNetReturnPct=300}
 ]){
  const x=fixture();edit(x.rows[2]);
  assert.throws(()=>m.build(x),/PROVISIONAL_PRICE_INVALID/);
 }
});
test("Blocked research case stays blocked and cannot contribute to a historical return",()=>{
 const x=fixture();const r=x.rows[0];
 r.status="BLOCKED_RESEARCH_WINDOW";
 r.grossReturnPct=null;r.hypotheticalNetReturnPct=null;r.entryCapResearchMillions=null;
 x.blockedCases=1;
 const out=m.build(x);
 assert.equal(out.blockedCases,1);
 assert.equal(out.usableCases,7);
 assert.equal(out.leaveOneIssuerOut.length,7);
 const bad=fixture();
 bad.rows[0].status="BLOCKED_RESEARCH_WINDOW";bad.blockedCases=1;
 assert.throws(()=>m.build(bad),/BLOCKED_RETURNS_NOT_NULL/);
});
test("CSV retains numeric negative returns, escapes untrusted formulas, refuses nonnumeric cells",()=>{
 const result=m.build(fixture());
 const output=m.csv(result);
 const headings=output.trim().split("\n")[0].split(",");
 const first=output.trim().split("\n").find(x=>x.startsWith('"AA",'));
 assert.equal(first.split(",")[headings.indexOf("omittedGrossPct")],"-60");
 assert.equal(first.split(",")[headings.indexOf("remainingMeanGrossPct")],"0");
 result.leaveOneIssuerOut[0].tickerOmitted='=HYPERLINK("https://evil.example","open")';
 assert.ok(m.csv(result).includes("'=HYPERLINK"));
 result.leaveOneIssuerOut[0].remainingMeanGrossPct="=1+1";
 assert.throws(()=>m.csv(result),/NUMERIC_EXPORT_INVALID/);
});
