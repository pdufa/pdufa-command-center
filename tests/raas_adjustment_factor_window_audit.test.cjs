"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const {auditWindowFactors:audit}=require("../scripts/raas_adjustment_factor_window_audit.cjs");
const eventDate="2025-06-16",key="TEST|"+eventDate;
const lead={caseId:"TEST|NDA123|2025",ticker:"TEST",pdufaTargetDate:eventDate};
function weekdayBars(start="2025-01-01",end="2025-06-15",rawClose=10,adjustment=x=>1){
 const result=[];
 for(let epoch=Date.parse(start+"T00:00:00Z");epoch<=Date.parse(end+"T00:00:00Z");epoch+=86400000){
  const d=new Date(epoch),day=d.getUTCDay();if(day===0||day===6)continue;
  result.push({date:d.toISOString().slice(0,10),close:rawClose*adjustment(result.length)});
 }
 return result;
}
const raw=()=>weekdayBars();
const all=()=>weekdayBars(undefined,undefined,10,()=>0.9);
const run=(over={})=>audit({
 leads:[lead],rawBarsByEvent:new Map([[key,raw()]]),
 adjustedBarsByEvent:new Map([[key,all()]]),...over
});
test("a complete same-vendor window reports paired session factors, not verified adjustment accuracy",()=>{
 const r=run(),x=r.rows[0];
 assert.equal(r.scope,"RAAS_2024_2025_FULL_WINDOW_ADJUSTMENT_FACTOR_RESEARCH");
 assert.equal(r.caseCount,1);
 assert.equal(r.casesWithCompleteSameVendorPriceWindow,1);
 assert.equal(x.adjustedWindowSessions,66);
 assert.equal(x.sameDateRawAdjustedPairs,66);
 assert.equal(x.entryAdjustedToRawFactor,0.9);
 assert.equal(x.exitAdjustedToRawFactor,0.9);
 assert.equal(x.entryToExitFactorChangePct,0);
 assert.equal(x.largestConsecutiveSessionFactorStepPct,0);
 assert.equal(x.completeSameVendorWindow,true);
 assert.equal(x.researchStatus,"NO_LARGE_FACTOR_STEP_OBSERVED_NOT_ACTION_VERIFIED");
 assert.equal(r.totalFactorStepCandidates,0);
 assert.equal(r.independentlyVerifiedCorporateActionHistories,0);
 assert.equal(r.independentlyVerifiedAdjustedReturnWindows,0);
 assert.equal(r.validatedTradingCases,0);
 assert.equal(r.approvedRaasMetricGrades,0);
 assert.equal(x.dividendSplitSpinOffAndADRReconciliationVerified,false);
});
test("factor change inside the window creates an investigation lead, not a certified split or return",()=>{
 const c=all(),r=raw();const before=c.length-79;
 for(let i=before+18;i<c.length;i++)c[i].close=10;
 const x=run({adjustedBarsByEvent:new Map([[key,c]]),
  rawBarsByEvent:new Map([[key,r]])});
 const row=x.rows[0];
 assert.equal(row.completeSameVendorWindow,true);
 assert.equal(row.adjustmentFactorStepCandidates.length,1);
 assert.equal(row.adjustmentFactorStepCandidates[0].status,"POTENTIAL_ADJUSTMENT_FACTOR_STEP_UNATTRIBUTED");
 assert.ok(row.adjustmentFactorStepCandidates[0].changeInAdjustedToRawFactorPct>10);
 assert.equal(row.researchStatus,"FACTOR_CHANGE_CANDIDATES_REQUIRES_SOURCE_AUDIT");
 assert.equal(row.entryToExitFactorChangePct,11.1111);
 assert.equal(x.casesWithFactorStepCandidates,1);
 assert.equal(x.totalFactorStepCandidates,1);
 assert.equal(x.independentlyVerifiedCorporateActionHistories,0);
 assert.equal(x.approvedRaasMetricGrades,0);
});
test("missing same-day raw prices report an explicit gap without interpolating corporate actions",()=>{
 const r=raw(),a=all(),position=a.length-79+11;
 const dropped=r.splice(position,1)[0].date;
 const x=run({rawBarsByEvent:new Map([[key,r]])});
 const row=x.rows[0];
 assert.equal(row.completeSameVendorWindow,false);
 assert.equal(row.sameDateRawAdjustedPairs,65);
 assert.deepEqual(row.missingRawSessions,[dropped]);
 assert.equal(row.entryToExitFactorChangePct,null);
 assert.equal(row.largestConsecutiveSessionFactorStepPct,null);
 assert.equal(row.researchStatus,"RAW_ADJUSTED_SESSION_GAPS");
 assert.equal(x.missingRawSessionsInSelectedWindows,1);
 assert.equal(x.independentlyVerifiedAdjustedReturnWindows,0);
});
test("a missing price series or insufficient T-79 sessions is unknown, not zero adjustment risk",()=>{
 const missing=run({rawBarsByEvent:new Map()});
 assert.equal(missing.rows[0].researchStatus,"MISSING_RAW_PRICE_SERIES");
 assert.equal(missing.rows[0].adjustmentFactorStepCandidates.length,0);
 assert.equal(missing.rows[0].completeSameVendorWindow,false);
 const short=run({adjustedBarsByEvent:new Map([[key,all().slice(-30)]])});
 assert.equal(short.rows[0].researchStatus,"INSUFFICIENT_ADJUSTED_TRADING_SESSIONS");
 assert.equal(short.rows[0].proposedEntrySession,null);
 assert.equal(short.rows[0].entryToExitFactorChangePct,null);
});
test("reject bad numbers, wrong dates, duplicates, cross-period events, and invalid controls",()=>{
 const corrupt=[
  ()=>run({leads:[lead,{...lead,caseId:"SECOND"}]}),
  ()=>run({leads:[{...lead,pdufaTargetDate:"2023-06-16"}]}),
  ()=>run({adjustedBarsByEvent:new Map([[key,[{date:"2026-01-01",close:10}]]])}),
  ()=>run({rawBarsByEvent:new Map([[key,[{date:"2025-01-02",close:0}]]])}),
  ()=>{const x=raw();x.push({...x[0]});return run({rawBarsByEvent:new Map([[key,x]])});},
  ()=>run({entryLeadTradingSessions:79,exitLeadTradingSessions:79}),
  ()=>run({stepAlertPercent:0})
 ];
 for(const invoke of corrupt)assert.throws(invoke,/RAAS_RATIO_/);
});
test("two events remain separate; one missing feed does not become a success in the other",()=>{
 const second={caseId:"OTHER|NDA456|2025",ticker:"OTHER",pdufaTargetDate:eventDate};
 const r=run({leads:[lead,second]});
 assert.equal(r.caseCount,2);
 assert.equal(r.casesWithCompleteSameVendorPriceWindow,1);
 assert.equal(r.rows[1].researchStatus,"INSUFFICIENT_ADJUSTED_TRADING_SESSIONS");
 assert.equal(r.rows[1].sameDateRawAdjustedPairs,0);
 assert.equal(r.independentlyVerifiedAdjustedReturnWindows,0);
});
test("nightly live-study integration keeps adjusted windows and missing validation distinct",async()=>{
 const study=require("../scripts/raas_active_two_year_study.cjs");
 const source=require("../new-platform/frontend/data/raas-active-2024-2025-primary-source-leads.json");
 const src=source.records[0];
 const earlier=require("../new-platform/frontend/data/raas-active-2024-2025-preentry-sec-share-leads.json");
 const later=require("../new-platform/frontend/data/raas-active-2024-2025-sec-cover-share-leads.json");
 const earliest=require("../new-platform/frontend/data/raas-2024-2025-additional-earliest-sec-cover.json");
 const x=await study.execute({csv:"event_key,ticker,pdufa_date\n",
  venueExceptions:[],researchLeads:[],sourceCapLeads:source.records,
  earlierSecCover:earlier,laterSecCover:later,additionalEarliestSecCover:earliest,
  key:"",secret:"",request:async()=>{throw Error("should never fetch");}});
 assert.equal(x.adjustmentFactorWindowAudit.caseCount,9);
 assert.equal(x.adjustmentFactorWindowAudit.casesWithCompleteSameVendorPriceWindow,0);
 assert.equal(x.sameVendorCompleteAdjustmentWindows,0);
 assert.equal(x.independentlyVerifiedCorporateActionHistories,0);
 assert.equal(x.adjustmentFactorWindowAudit.rows.find(z=>z.ticker===src.ticker)
  .researchStatus,"INSUFFICIENT_ADJUSTED_TRADING_SESSIONS");
 assert.equal(x.independentTradingCasesValidated,0);
 assert.equal(x.approvedRaasMetricCalibrations,0);
});
