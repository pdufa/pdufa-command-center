"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const {build,csv,addDays}=require("../scripts/raas_2025_crl_candidate_inclusion_exclusion.cjs");
const candidates=require("../new-platform/frontend/data/raas-2025-adverse-candidate-inclusion-exclusion-leads.json");
const primary=require("../new-platform/frontend/data/raas-active-2024-2025-primary-source-leads.json");
const fixture=()=>structuredClone(candidates);
const fake=(price=4.94)=>{const calls=[];
 const fetcher=async(ticker,asof,start,end,adjustment,key,secret)=>{
  calls.push({ticker,asof,start,end,adjustment});
  return [{date:"2025-01-13",close:price},
   {date:"2025-01-14",close:price+0.03}];};
 return {calls,fetcher};
};
test("2025 adverse cases: CAPR rejected before pricing, ALDX priced at Jan 2025 entry and fails provisional $300m band",async()=>{
 const {calls,fetcher}=fake();
 const r=await build({candidates:fixture(),primarySource:primary,key:"test",secret:"test",fetcher});
 assert.equal(r.candidateSourceCount,2);
 assert.equal(calls.length,1);
 assert.deepEqual(calls[0],{ticker:"ALDX",asof:"2025-04-02",start:"2025-01-13",end:"2025-01-18",adjustment:"raw"});
 const aldx=r.rows.find(x=>x.ticker==="ALDX"),capr=r.rows.find(x=>x.ticker==="CAPR");
 assert.equal(aldx.status,"EXCLUDED_PROVISIONAL_ENTRY_CAP_OUTSIDE_300M_10B");
 assert.equal(aldx.plannedExitCalendarDate,"2025-03-19");
 assert.equal(aldx.capResearchMillions,294.18);
 assert.equal(aldx.secCoverSharesUsed,59549598);
 assert.equal(aldx.computedEntrySession,"2025-01-13");
 assert.equal(capr.status,"EXCLUDED_FROM_PHASE3_COMPLETE_AT_ENTRY_COHORT");
 assert.equal(capr.exclusionOrReviewReason,"PHASE3_READOUT_NOT_PUBLIC_AT_PLANNED_ENTRY");
 assert.equal(capr.plannedEntryCalendarDate,"2025-06-13");
 assert.equal(capr.plannedExitCalendarDate,"2025-08-17");
 assert.equal(capr.actualFDAActionDateRetrospective,"2025-07-09");
 assert.equal(capr.rawEntryClose,null);
 assert.equal(capr.capResearchMillions,null);
 assert.ok(r.rows.every(x=>!x.validatedHistoricalCap&&!x.historicalEntryTradeApproved&&
  !x.eligibleForRaasCalibration&&!x.retrospectiveFDAOutcomeWasKnownAtEntry));
 assert.equal(r.approvedRaasMetrics,0);
 assert.equal(r.approvedOptimalTradingWindow,null);
});
test("Even if hypothetical ALDX raw entry cap is >$300m, zero eligibility/trade/RAAS validation",async()=>{
 const {fetcher}=fake(5.1);
 const r=await build({candidates:fixture(),primarySource:primary,key:"fake",secret:"fake",fetcher});
 const a=r.rows.find(x=>x.ticker==="ALDX");
 assert.equal(a.status,"BLOCKED_FOR_FULL_VALIDATION_EVEN_WITH_CAP_IN_BAND");
 assert.equal(a.capResearchMillions,303.9);
 assert.equal(a.historicalEntryTradeApproved,false);
 assert.equal(a.validatedHistoricalReturn,false);
 assert.equal(r.independentlyValidatedEntryCaps,0);
});
test("Missing Alpaca credentials block ALDX but CAPR remains chronologically excluded",async()=>{
 const {calls,fetcher}=fake();
 const r=await build({candidates:fixture(),primarySource:primary,fetcher});
 assert.equal(calls.length,0);
 assert.equal(r.rows.find(x=>x.ticker==="ALDX").status,"BLOCKED_ALPACA_CREDENTIALS");
 assert.equal(r.rows.find(x=>x.ticker==="CAPR").status,"EXCLUDED_FROM_PHASE3_COMPLETE_AT_ENTRY_COHORT");
});
test("Fail closed on tampered FDA CRL dates, PDUFA announcement or SEC as-of share facts",async()=>{
 const edits=[
  a=>{a.records.find(x=>x.ticker==="ALDX").actualFDAActionDate="2025-04-03"},
  a=>{a.records.find(x=>x.ticker==="ALDX").shareSource.sharesOutstanding=70000000},
  a=>{a.records.find(x=>x.ticker==="ALDX").targetAnnouncementDate="2025-02-01"},
  a=>{a.records.find(x=>x.ticker==="CAPR").phase3ReadoutDate="2025-06-01"},
  a=>{a.records.find(x=>x.ticker==="ALDX").actualFDAActionSourceUrl="https://invalid.example/20250402.pdf"},
  a=>{a.records.find(x=>x.ticker==="CAPR").originalPublicFDAOutcomeKnownAtEntry=true},
 ];
 for(const edit of edits){const data=fixture();edit(data);
  await assert.rejects(build({candidates:data,primarySource:primary}),
   /RAAS_CRL_REVIEW_CANDIDATE_PROVENANCE_INVALID|RAAS_CRL_REVIEW_ALDX_DATED_SEC_OR_CYCLE_INVALID|RAAS_CRL_REVIEW_CAPR_ACTION_OR_PHASE3_INVALID/);
 }
});
test("Never accept duplicate ticker or silently repeat case already present in original nine-study data",async()=>{
 const f=fixture();
 f.records[1]=structuredClone(f.records[0]);
 await assert.rejects(build({candidates:f,primarySource:primary}),/DUPLICATE_TICKER|SOURCE_INVALID/);
 const duplicate={...primary,records:[...primary.records,{caseId:f.records[0].caseId,ticker:"ALDX"}]};
 await assert.rejects(build({candidates:fixture(),primarySource:duplicate}),
  /ALREADY_IN_PRIMARY_SAMPLE/);
});
test("Invalid or missing raw trade bars cannot produce synthetic historical capitalization",async()=>{
 const invalid=()=>[{date:"2025-01-13",close:-2}];
 await assert.rejects(build({candidates:fixture(),primarySource:primary,key:"x",secret:"x",fetcher:invalid}),
  /RAW_ALPACA_INVALID/);
 const r=await build({candidates:fixture(),primarySource:primary,key:"x",secret:"x",fetcher:async()=>[]});
 assert.equal(r.rows.find(x=>x.ticker==="ALDX").status,"BLOCKED_NO_ENTRY_SESSION");
 assert.equal(r.rows.find(x=>x.ticker==="ALDX").capResearchMillions,null);
});
test("CSV has actual numeric caps, no formulas, and never upgrades candidate grade",async()=>{
 const {fetcher}=fake(),r=await build({candidates:fixture(),primarySource:primary,key:"x",secret:"x",fetcher});
 const t=csv(r);
 assert.equal(t.trim().split("\n").length,3);
 assert.match(t,/294\.18/);
 r.rows[0].ticker='=HYPERLINK("https://evil.example","click")';
 assert.ok(csv(r).includes("'=HYPERLINK"));
 r.rows[0].capResearchMillions="=5*6";
 assert.throws(()=>csv(r),/NUMERIC_EXPORT_INVALID/);
 assert.equal(addDays("2025-04-02",-79),"2025-01-13");
});
