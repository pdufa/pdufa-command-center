"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),
 fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"..");
const expansion=require("../new-platform/frontend/data/raas-2024-2025-expanded-candidate-source-leads.json");
const source=require("../new-platform/frontend/data/raas-active-2024-2025-primary-source-leads.json");
const date=s=>typeof s==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const minus=(d,n)=>new Date(Date.parse(d+"T00:00:00Z")-n*86400000).toISOString().slice(0,10);
function verify(x){
 assert.equal(x.schemaVersion,1);
 assert.equal(x.scope,"RAAS_2024_2025_ADDITIONAL_PHASE3_FDA_SOURCE_LEADS_RESEARCH_ONLY");
 assert.equal(x.allResearchOnly,true);
 assert.equal(x.approvedAdditionsTo2024To2025Backtest,0);
 assert.equal(x.independentlyVerifiedTradingCases,0);
 assert.equal(x.fullFDAEventCensusCompleted,false);
 assert.equal(x.sourceAsOf,"2026-11-03");
 assert.equal(x.records.length,2);
 const ids=new Set(source.records.map(e=>e.caseId)),tickers=new Set(source.records.map(e=>e.ticker));
 for(const r of x.records){
  assert.ok(!ids.has(r.caseId));
  assert.ok(!tickers.has(r.ticker));
  assert.equal(r.eligibleForApprovedTradingStudy,false);
  assert.equal(r.historicalSECEntrySharesValidated,false);
  assert.equal(r.historicalEntryMarketCap300m10bValidated,false);
  assert.equal(r.adjustedPriceBarsIndependentlyReconciled,false);
  assert.equal(r.postPhase3AtEntrySourceLead,true);
  assert.equal(r.asOfStatus,"SOURCE_DATES_RECORDED_MARKET_CAP_AND_PRICE_INDEPENDENT_CHECK_PENDING");
  assert.ok(r.missingChecks.length>=3);
  assert.ok(r.nctIds.every(n=>/^NCT\d{8}$/.test(n)));
  assert.ok([r.targetAnnouncementDate,r.phase3EvidenceDate,r.pdufaTargetDate,
   r.actualFDAActionDate].every(date));
  assert.ok(r.phase3EvidenceDate<=minus(r.pdufaTargetDate,90));
  assert.ok(r.targetAnnouncementDate<=minus(r.pdufaTargetDate,90));
  assert.ok(r.actualFDAActionDate<=r.pdufaTargetDate);
  assert.ok(r.actualFDAActionDate>minus(r.pdufaTargetDate,3));
  assert.equal(r.actualFDAOutcome,"APPROVED");
  for(const k of ["phase3EvidenceSourceUrl","targetAnnouncementSourceUrl","outcomeSourceUrl"]){
   assert.match(r[k],/^https:\/\/(ir\.travere\.com|investors\.urogen\.com|www\.fda\.gov|www\.sec\.gov)\//);
  }
 }
 assert.deepEqual(x.records.map(r=>r.ticker).sort(),["TVTX","URGN"]);
 const tvtx=x.records.find(x=>x.ticker==="TVTX"),urgn=x.records.find(x=>x.ticker==="URGN");
 assert.equal(tvtx.nctIds[0],"NCT03762850");
 assert.equal(tvtx.reviewCycleType,"SUPPLEMENTAL_ACCELERATED_TO_TRADITIONAL_APPROVAL");
 assert.equal(tvtx.pdufaTargetDate,"2024-09-05");
 assert.equal(tvtx.targetAnnouncementDate,"2024-05-06");
 assert.equal(urgn.nctIds[0],"NCT05243550");
 assert.equal(urgn.reviewCycleType,"ORIGINAL_NDA_PHASE3_ENVISION");
 assert.equal(urgn.pdufaTargetDate,"2025-06-13");
 assert.equal(urgn.targetAnnouncementDate,"2024-10-15");
 return true;
}
test("Two sourced FDA case leads are chronologically eligible for further cap screening, NOT eligible study rows",()=>verify(expansion));
test("Historical RAAS remains exactly nine selected research events with no extra scores",()=>{
 assert.equal(source.records.length,9);
 assert.equal(expansion.approvedAdditionsTo2024To2025Backtest,0);
 const fullGrid=fs.readFileSync(path.join(root,"scripts/raas_active_2024_2025_full_90_3_grid.cjs"),"utf8");
 assert.match(fullGrid,/EVENTS|sourceCases|sourcePrograms/);
});
test("Mobile research page exposes backlog with citations and explicit missing validation",()=>{
 const page=fs.readFileSync(path.join(root,"new-platform/frontend/app/raas-worklist/page.tsx"),"utf8");
 assert.match(page,/ExpandedHistoricalCandidates/);
 assert.match(page,/raas-historical-expansion-candidates/);
 assert.match(page,/Missing:/);
 assert.ok(page.includes("<ExpandedHistoricalCandidates/>"));
});
