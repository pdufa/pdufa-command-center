"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const {assemble}=require("../scripts/raas_historical_candidate_review_queue.cjs");
const root=path.resolve(__dirname,"..");
const primary=JSON.parse(fs.readFileSync(path.join(root,
 "new-platform/frontend/data/raas-historical-2020-primary-source-leads.json"),"utf8"));
const shares=JSON.parse(fs.readFileSync(path.join(root,
 "new-platform/frontend/data/raas-2020-sec-cover-share-leads.json"),"utf8"));
function rawSample(){
 const e=primary.records.find(x=>x.ticker==="KALA");
 return {scope:"RAAS_HISTORIC_RAW_CAP_RESEARCH",
  status:"UNVALIDATED_HISTORICAL_CAP_RESEARCH_ONLY",
  historicallyEligibleTrades:0,approvedRaasRatings:0,
  cases:[{caseId:e.caseId,ticker:e.ticker,
   pdufaTargetDate:e.pdufaTargetDate,actualFDAActionDate:e.actualFDAActionDate,
   status:"RAW_MARKET_CAP_DIAGNOSTICS_NOT_PROVEN_TRADING_ELIGIBILITY",
   approvedRaasRatings:0,eventTradeCasesValidated:0,
   observations:[{session:"2020-08-07",beforeActualFDAAction:true,
    historicMarketCapResearchMillions:448.48,within300mTo10bUnreviewed:true},
    {session:"2020-10-26",beforeActualFDAAction:false,
     historicMarketCapResearchMillions:500,within300mTo10bUnreviewed:true}]}]};
}
test("all located source programs appear, but zero are promoted into ten-year score intake",()=>{
 const r=assemble({primary,shares});
 assert.equal(r.summary.sourcePrograms,6);
 assert.equal(r.summary.distinctSourceIssuers,5);
 assert.equal(r.summary.sameIssuerOverlappingPairs,1);
 assert.equal(r.summary.datedShareResearchPrograms,5);
 assert.equal(r.summary.distinctIssuersWithShareResearch,4);
 assert.equal(r.summary.liveRawCapResearchPrograms,0);
 assert.equal(r.summary.provisionalPreAction300mTo10bSessions,0);
 assert.equal(r.summary.reviewedEligibleTradingEvents,0);
 assert.equal(r.summary.approvedRaasScores,0);
 assert.equal(r.summary.fullTenYearCensusAudited,false);
 assert.ok(r.cases.every(c=>c.tenYearIntakeStatus==="DO_NOT_PROMOTE_REQUIRES_INDEPENDENT_REVIEW"));
 assert.ok(r.cases.every(c=>c.pendingVerification.includes("60_RAAS_METRIC_CALIBRATION_APPROVAL")));
 const dbvt=r.cases.find(c=>c.ticker==="DBVT");
 assert.equal(dbvt.shareSourceAvailable,false);
 assert.ok(dbvt.pendingVerification.includes("MISSING_DATED_US_COMMON_SHARE_OR_ADR_CONVERSION_SOURCE"));
});
test("live raw Alpaca market-cap diagnostics are counted only as provisional pre-action research",()=>{
 const r=assemble({primary,shares,rawCap:rawSample()});
 const kala=r.cases.find(c=>c.ticker==="KALA");
 assert.equal(kala.observedPreActionResearchSessions,1);
 assert.equal(kala.provisionalPreAction300mTo10bSessions,1);
 assert.equal(kala.approvedRaasScores,0);
 assert.equal(kala.reviewedEligibleTradingEvents,0);
 assert.equal(r.summary.liveRawCapResearchPrograms,1);
 assert.equal(r.summary.provisionalPreAction300mTo10bSessions,1);
 assert.ok(r.cases.find(c=>c.ticker==="HRTX").pendingVerification.includes("MISSING_LIVE_ALPACA_RAW_CAP_RESEARCH"));
});
test("wrong issuer, review cycle, invented scores, post-action chronology or duplicated raw cases fail closed",()=>{
 const r=rawSample();
 assert.throws(()=>assemble({primary,shares,rawCap:{...r,approvedRaasRatings:1}}),/INVALID_RAW_RESEARCH_SCOPE/);
 assert.throws(()=>assemble({primary,shares,rawCap:{...r,cases:[{...r.cases[0],ticker:"DBVT"}]}}),/UNTRUSTED_RAW_CASE/);
 assert.throws(()=>assemble({primary,shares,rawCap:{...r,cases:[{...r.cases[0],actualFDAActionDate:"2020-10-30"}]}}),/UNTRUSTED_RAW_CASE/);
 assert.throws(()=>assemble({primary,shares,rawCap:{...r,cases:[r.cases[0],r.cases[0]]}}),/UNTRUSTED_RAW_CASE/);
 assert.throws(()=>assemble({primary,shares,rawCap:{...r,cases:[{...r.cases[0],
  observations:[{session:"2020-10-27",beforeActualFDAAction:true,
   historicMarketCapResearchMillions:400,within300mTo10bUnreviewed:true}]}]}}),/RAW_PRE_ACTION_GUARD/);
});
test("all share facts must match exact source case identities",()=>{
 assert.throws(()=>assemble({primary,shares:{...shares,records:[...shares.records,
  {...shares.records[0],caseId:"FAKE|FDA|2020"}]}}),/UNMATCHED_OR_DUPLICATE_SHARES/);
 assert.throws(()=>assemble({primary,shares:{...shares,records:[...shares.records,
  shares.records[0]]}}),/UNMATCHED_OR_DUPLICATE_SHARES/);
});
