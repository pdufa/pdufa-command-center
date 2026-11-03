"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const candidates=require("../new-platform/frontend/data/raas-2024-2025-expanded-candidate-source-leads.json");
const shareFeed=require("../new-platform/frontend/data/raas-2024-2025-expanded-candidate-sec-snapshots.json");
const primary=require("../new-platform/frontend/data/raas-active-2024-2025-primary-source-leads.json");
const m=require("../scripts/raas_2024_2025_expanded_sec_price_research.cjs");
const clone=x=>structuredClone(x);
const shift=(s,n)=>new Date(Date.parse(s+"T00:00:00Z")+n*86400000).toISOString().slice(0,10);
const get=t=>({event:candidates.records.find(c=>c.ticker===t),
 shares:shareFeed.records.find(c=>c.ticker===t)});
const bars=(ticker,start,end,adjustment)=>{
 const result=[];
 for(let s=start;s<=end;s=shift(s,1)){
  const dow=new Date(s+"T00:00:00Z").getUTCDay();
  if(dow!==0&&dow!==6)result.push({
   date:s,close:adjustment==="all"?20:10
  });
 }
 return result;
};
test("Four original SEC cover facts for TVTX/URGN are publication-timed, dated and unapproved",()=>{
 const sources=m.checkSources(candidates,shareFeed,primary);
 assert.equal(sources.size,2);
 const tvtx=get("TVTX").shares.snapshots,urgn=get("URGN").shares.snapshots;
 assert.deepEqual(tvtx.map(x=>x.sharesOutstanding),[76129018,76491485]);
 assert.deepEqual(tvtx.map(x=>x.firstConservativeEntryDate),["2024-05-07","2024-08-02"]);
 assert.deepEqual(urgn.map(x=>x.sharesOutstanding),[46094352,46107451]);
 assert.deepEqual(urgn.map(x=>x.firstConservativeEntryDate),["2025-03-11","2025-05-13"]);
 assert.ok(primary.records.every(x=>!sources.has(x.caseId)));
});
test("All 3828 pairs for each new candidate are blocked without actual Alpaca credentials",async()=>{
 const x=await m.execute({candidates,shareFeed,primary,key:null,secret:null});
 assert.equal(x.sourceCaseCount,2);
 assert.equal(x.status,"BLOCKED_NO_ALPACA_BARS");
 assert.equal(x.totalCaseWindowEvaluations,7656);
 assert.equal(x.provisionalReturnWindowCount,0);
 assert.equal(x.addedToNineCaseStudy,0);
 assert.equal(x.approvedBestTradingWindow,null);
 assert.equal(x.independentlyValidatedMarketCaps,0);
 assert.equal(x.independentlyValidatedTrades,0);
 assert.equal(x.candidateReport.length,7656);
});
test("Later SEC counts cannot be used before filing is public; raw never mixed with adjusted",()=>{
 const {event,shares}=get("TVTX"),d1=shift(event.pdufaTargetDate,-90),
  d2=shift(event.pdufaTargetDate,-30),out=shift(event.pdufaTargetDate,-14);
 const rows=[
  {date:d1,rawClose:10,adjustedClose:20},
  {date:d2,rawClose:12,adjustedClose:30},
  {date:out,rawClose:14,adjustedClose:35}
 ];
 const early=m.inspectCase(event,shares,rows,90,14);
 assert.equal(early.reason,"SOURCE_ELIGIBLE_RESEARCH_ONLY_NOT_VALIDATED_TRADE");
 assert.equal(early.publishedSECSourceUsed,shares.snapshots[0].sourceUrl);
 assert.equal(early.approximateMarketCapUSDMillions,761.29);
 assert.equal(early.provisionalGrossReturnPct,75);
 assert.equal(early.provisionalNetAfter1ptCostPct,74);
 const late=m.inspectCase(event,shares,rows,30,14);
 assert.equal(late.publishedSECSourceUsed,shares.snapshots[1].sourceUrl);
 assert.equal(late.approximateMarketCapUSDMillions,
  Math.round(12*shares.snapshots[1].sharesOutstanding/10000)/100);
 assert.equal(late.provisionalGrossReturnPct,16.67);
 assert.equal(late.independentlyValidatedTrade,false);
 assert.equal(late.independentlyVerifiedDailyShares,false);
});
test("Original 2025 URGN caps must use March 10 filing by March and May 12 by May",()=>{
 const {event,shares}=get("URGN");
 const s1=shift(event.pdufaTargetDate,-90),s2=shift(event.pdufaTargetDate,-28),
  exit=shift(event.pdufaTargetDate,-14);
 const data=[
  {date:s1,rawClose:11,adjustedClose:11},
  {date:s2,rawClose:11,adjustedClose:11},
  {date:exit,rawClose:11,adjustedClose:11}
 ];
 const early=m.inspectCase(event,shares,data,90,14),
  late=m.inspectCase(event,shares,data,28,14);
 assert.equal(early.publishedSECSourceUsed,shares.snapshots[0].sourceUrl);
 assert.equal(late.publishedSECSourceUsed,shares.snapshots[1].sourceUrl);
 assert.equal(early.reason,"SOURCE_ELIGIBLE_RESEARCH_ONLY_NOT_VALIDATED_TRADE");
 assert.equal(late.reason,"SOURCE_ELIGIBLE_RESEARCH_ONLY_NOT_VALIDATED_TRADE");
 assert.equal(early.provisionalGrossReturnPct,0);
 assert.ok(early.approximateMarketCapUSDMillions>=300);
});
test("A low raw market cap is excluded even if adjusted prices look attractive",()=>{
 const {event,shares}=get("URGN");
 const d1=shift(event.pdufaTargetDate,-76),d2=shift(event.pdufaTargetDate,-63);
 const res=m.inspectCase(event,shares,[
  {date:d1,rawClose:5,adjustedClose:10},
  {date:d2,rawClose:6,adjustedClose:30}
 ],76,63);
 assert.equal(res.reason,"PROVISIONAL_CAP_OUTSIDE_300M_TO_10B");
 assert.equal(res.provisionalGrossReturnPct,null);
 assert.ok(res.approximateMarketCapUSDMillions<300);
});
test("Two Alpaca adjustment requests, matched sessions, and no approved cases",async()=>{
 const requests=[];
 const fake=async(ticker,asof,start,end,adjustment,key,secret)=>{
  requests.push({ticker,asof,adjustment,start,end});
  return bars(ticker,start,end,adjustment);
 };
 const result=await m.execute({candidates,shareFeed,primary,
  key:"fake-key",secret:"fake-secret",fetcher:fake});
 assert.equal(requests.length,4);
 assert.deepEqual(requests.map(x=>[x.ticker,x.adjustment]),
  [["TVTX","raw"],["TVTX","all"],["URGN","raw"],["URGN","all"]]);
 assert.equal(result.status,"PROVISIONAL_SEC_PRICE_RESEARCH_UNVALIDATED");
 assert.equal(result.totalCaseWindowEvaluations,7656);
 assert.ok(result.provisionalReturnWindowCount>0);
 assert.equal(result.distinctIssuerCasesWithProvisionalReturns,2);
 assert.equal(result.independentlyValidatedTrades,0);
 assert.equal(result.independentlyValidatedMarketCaps,0);
 assert.equal(result.approvedBestTradingWindow,null);
 assert.match(m.csv(result),/publishedSECSourceUsed/);
 assert.match(m.csv(result),/TVTX/);
});
test("Misaligned adjusted bars, duplicate SEC shares, future source dates and approval all fail closed",()=>{
 const start="2024-05-25",end="2024-08-21";
 const raw=bars("TVTX",start,end,"raw"),adj=bars("TVTX",start,end,"all");
 assert.throws(()=>m.combine(raw,adj.slice(1),start,end),
  /RAAS_EXPANDED_CAP_ALPACA_RAW_ADJUSTED_SESSION_MISMATCH/);
 const corrupt=clone(shareFeed);
 corrupt.records[0].snapshots[0].firstConservativeEntryDate="2024-05-06";
 assert.throws(()=>m.checkSources(candidates,corrupt,primary),/RAAS_EXPANDED_CAP_SEC_SNAPSHOT_DATE_OR_PUBLISHED_FACT_INVALID/);
 const future=clone(shareFeed);
 future.records[1].snapshots[0].filedDate="2025-06-20";
 assert.throws(()=>m.checkSources(candidates,future,primary),/RAAS_EXPANDED_CAP_SEC_SNAPSHOT_DATE_OR_PUBLISHED_FACT_INVALID/);
 const score=clone(candidates);
 score.records[0].eligibleForApprovedTradingStudy=true;
 assert.throws(()=>m.checkSources(score,shareFeed,primary),/RAAS_EXPANDED_CAP_CANDIDATE_CHRONOLOGY_OR_APPROVAL_INVALID/);
});
