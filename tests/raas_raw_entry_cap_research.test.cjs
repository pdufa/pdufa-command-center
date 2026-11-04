"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const primary=require("../new-platform/frontend/data/raas-active-2024-2025-primary-source-leads.json");
const earlier=require("../new-platform/frontend/data/raas-active-2024-2025-preentry-sec-share-leads.json");
const later=require("../new-platform/frontend/data/raas-active-2024-2025-sec-cover-share-leads.json");
const earliest=require("../new-platform/frontend/data/raas-2024-2025-additional-earliest-sec-cover.json");
const study=require("../scripts/raas_active_two_year_study.cjs");
const prior=require("../scripts/raas_alpaca_historical_price_study.cjs");
const {auditRawEntryMarketCapResearch:cap}=require("../scripts/raas_raw_entry_cap_research.cjs");
const clone=x=>structuredClone(x);
const slno=primary.records.find(x=>x.ticker==="SLNO");
const key=slno.ticker+"|"+slno.pdufaTargetDate;
function bars(start="2024-11-01",end="2025-03-26",close=10){
 const out=[];
 for(let t=Date.parse(start+"T00:00:00Z");t<=Date.parse(end+"T00:00:00Z");t+=86400000){
  const day=new Date(t),weekday=day.getUTCDay();
  if(weekday===0||weekday===6)continue;
  out.push({date:day.toISOString().slice(0,10),open:close,
   high:close,low:close,close,volume:50000});
 }
 return out;
}
const adjusted=()=>new Map([[key,bars(undefined,undefined,12)]]);
const raw=()=>new Map([[key,bars(undefined,undefined,10)]]);
const run=(options={})=>cap({leads:primary.records,earlier,later,
 adjustedBarsByEvent:adjusted(),rawBarsByEvent:raw(),...options});

test("historical raw close and SEC point-in-time shares produce only a provisional cap",()=>{
 const x=run();
 assert.equal(x.caseCount,9);
 assert.equal(x.sameSessionRawAdjustedPricePairs,1);
 assert.equal(x.provisionalCapEstimates,1);
 assert.equal(x.independentlyValidatedEntryMarketCaps,0);
 assert.equal(x.independentlyReconciledAdjustedPricePairs,0);
 assert.equal(x.validatedTradingCases,0);
 assert.equal(x.approvedRaasScores,0);
 const s=x.rows.find(r=>r.ticker==="SLNO");
 assert.equal(s.entryLeadTradingSessions,79);
 assert.ok(s.proposedEntrySession>="2024-11-07"&&s.proposedEntrySession<"2025-02-28");
 assert.equal(s.adjustedCloseAlpacaAll,12);
 assert.equal(s.rawCloseAlpaca,10);
 assert.equal(s.rawToAdjustedCloseRatio,1.2);
 assert.equal(s.secSharesOutstanding,43117432);
 assert.equal(s.secFirstConservativeUse,"2024-11-07");
 assert.equal(s.provisionalRawPriceTimesDatedSecCoverCapUsdMillions,431.17);
 assert.equal(s.marketCap300MTo10BIndependentlyVerified,false);
 assert.equal(s.independentAdjustedPriceVendorVerified,false);
 assert.equal(s.secShareContinuityVerified,false);
 assert.equal(s.corporateActionReconciliationVerified,false);
 assert.equal(s.eligibleForValidatedRaasTradingCase,false);
 assert.equal(s.approvedRaasScore,null);
 assert.match(s.status,/PROVISIONAL_CAP_ONLY/);
 assert.equal(x.rows.filter(r=>r.rawCloseAlpaca===null).length,8);
});
test("SEC share-date staleness and later share-count differences are diagnostics only",()=>{
 const x=run();
 const slnoCase=x.rows.find(r=>r.ticker==="SLNO");
 assert.ok(slnoCase.secShareObservationAgeDaysAtEntry>=0);
 assert.ok(["WITHIN_30_DAYS","OVER_30_DAYS","OVER_90_DAYS"].includes(
  slnoCase.secShareObservationAgeBucket));
 assert.equal(slnoCase.sameVendorRawAndAllCloseEqualAtEntry,false);
 assert.equal(slnoCase.laterSECShareObservationsExcludedAtEntry.length,1);
 const future=slnoCase.laterSECShareObservationsExcludedAtEntry[0];
 assert.equal(future.firstUsableDate,"2025-03-01");
 assert.equal(future.sharesOutstanding,45857291);
 assert.equal(future.changeFromEntryCoverPct,6.35);
 assert.equal(future.knowledgeTiming,"NOT_PUBLIC_AT_ENTRY_AUDIT_ONLY");
 assert.equal(slnoCase.laterSECShareChangeFromEntrySnapshotPresent,true);
 assert.equal(slnoCase.largestAbsoluteLaterCoverShareDeltaPct,6.35);
 assert.equal(slnoCase.eligibleForValidatedRaasTradingCase,false);
 assert.equal(x.laterSECShareCountChangeObserved,1);
 assert.equal(x.sameVendorRawAdjustedEntryPriceMatches,0);
 assert.equal(x.independentlyValidatedEntryMarketCaps,0);
 assert.equal(x.approvedRaasScores,0);
});
test("SEC source age and postentry differences never substitute for a verified cap",()=>{
 const age=run({rawBarsByEvent:new Map([[key,bars()]]),adjustedBarsByEvent:new Map([[key,bars()]])});
 const r=age.rows.find(x=>x.ticker==="SLNO");
 assert.equal(r.sameVendorRawAndAllCloseEqualAtEntry,true);
 assert.equal(age.sameVendorRawAdjustedEntryPriceMatches,1);
 assert.ok(r.secShareObservationAgeDaysAtEntry>0);
 assert.equal(r.marketCap300MTo10BIndependentlyVerified,false);
 assert.equal(r.corporateActionReconciliationVerified,false);
 assert.equal(r.independentAdjustedPriceVendorVerified,false);
 assert.equal(age.independentlyReconciledAdjustedPricePairs,0);
 assert.equal(age.validatedTradingCases,0);
});
test("missing same-session raw bar can never borrow an adjusted close",()=>{
 const r=run({rawBarsByEvent:new Map([[key,bars(undefined,"2024-11-15",10)]])});
 const s=r.rows.find(x=>x.ticker==="SLNO");
 assert.equal(s.rawCloseAlpaca,null);
 assert.equal(s.provisionalRawPriceTimesDatedSecCoverCapUsdMillions,null);
 assert.equal(s.status,"MISSING_RAW_PRICE_FOR_SAME_T79_SESSION");
 assert.equal(r.provisionalCapEstimates,0);
});
test("SEC cover published after entry is unavailable even when later price matches",()=>{
 const a=clone(earlier),b=clone(later);
 const s=a.records.find(x=>x.ticker==="SLNO");
 s.firstConservativeEntryDate="2025-01-15"; // before later source but AFTER proposed T-79
 const r=run({earlier:a,later:b});
 const row=r.rows.find(x=>x.ticker==="SLNO");
 assert.equal(row.secSharesOutstanding,null);
 assert.equal(row.provisionalRawPriceTimesDatedSecCoverCapUsdMillions,null);
 assert.equal(row.status,"NO_SEC_COVER_PUBLIC_BY_ENTRY");
});
test("no future sources, corrupt share counts, duplicate cases or invalid cap bars enter research",()=>{
 const cases=[
  ()=>{const d=clone(primary);d.records[1].caseId=d.records[0].caseId;return {leads:d.records};},
  ()=>{const d=clone(earlier);d.records[0].sharesOutstanding=-100;return {earlier:d};},
  ()=>{const d=clone(later);d.records[0].sourceUrl="https://bad.invalid/sec";return {later:d};},
  ()=>({rawBarsByEvent:new Map([[key,[{date:"2026-11-01",close:10}]]])}),
  ()=>({rawBarsByEvent:new Map([[key,[{date:"2025-01-02",close:0}]]])}),
 ];
 for(const change of cases)assert.throws(()=>run(change()),/RAAS_RAW_CAP_/);
 const d=clone(primary);d.records.find(x=>x.ticker==="SLNO").targetAnnouncementDate="2025-03-01";
 const r=run({leads:d.records});
 const row=r.rows.find(x=>x.ticker==="SLNO");
 assert.equal(row.status,"PDUFA_TARGET_NOT_PUBLIC_BEFORE_ENTRY");
 assert.equal(row.provisionalRawPriceTimesDatedSecCoverCapUsdMillions,null);
});
test("two Alpaca adjustments use the same SIP vendor and explicit adjustment query",async()=>{
 const sample=bars("2025-01-02","2025-01-10",10);
 const calls=[];
 for(const adjustment of ["all","raw"]){
  const downloaded=await prior.downloadBars({
    ticker:"SLNO",scheduledEventDate:"2025-03-27",
    firstBarDate:"2025-01-01",lastBarDate:"2025-01-10"
  },"fake-key","fake-secret",async(u)=>{
   const url=new URL(u);calls.push(url.searchParams.get("adjustment"));
   assert.equal(url.searchParams.get("feed"),"sip");
   assert.equal(url.searchParams.get("asof"),"2025-03-27");
   const c=adjustment==="raw"?10:12;
   return {ok:true,headers:{get:()=>"application/json"},text:async()=>JSON.stringify({
    symbol:"SLNO",next_page_token:null,bars:sample.map(x=>({
      t:x.date+"T00:00:00Z",o:c,h:c,l:c,c,v:10000
    }))
   })};
  },adjustment);
  assert.equal(downloaded.length,sample.length);
 }
 assert.deepEqual(calls,["all","raw"]);
 await assert.rejects(()=>prior.downloadBars({ticker:"SLNO"},"a","b",
  async()=>{throw Error("should not call vendor");},"unsupported"),
  /RAAS_ALPACA_ADJUSTMENT_UNSUPPORTED/);
});
test("active 2024–2025 Alpaca research includes raw cap output, never approved grades",async()=>{
 const rawRows=bars(),allRows=bars(undefined,undefined,12),seen=[];
 const result=await study.execute({
  csv:"event_key,ticker,pdufa_date\n",
  researchLeads:[slno],sourceCapLeads:primary.records,
  earlierSecCover:earlier,laterSecCover:later,
  venueExceptions:[],key:"fake",secret:"fake",
  request:async(u)=>{
   const url=new URL(u),adjustment=url.searchParams.get("adjustment");
   seen.push(adjustment);
   assert.equal(url.pathname,"/v2/stocks/SLNO/bars");
   assert.equal(url.searchParams.get("feed"),"sip");
   const x=adjustment==="raw"?rawRows:allRows;
   return {ok:true,headers:{get:()=>"application/json"},text:async()=>JSON.stringify({
    symbol:"SLNO",next_page_token:null,bars:x.map(v=>({
     t:v.date+"T00:00:00Z",o:v.open,h:v.high,l:v.low,c:v.close,v:v.volume
    }))
   })};
  }
 });
 assert.deepEqual(seen,["all","raw"]);
 assert.equal(result.rawPriceResearchEventsCollected,1);
 assert.equal(result.rawAdjustedSameSessionPairs,1);
 assert.equal(result.provisionalHistoricalEntryCaps,1);
 assert.equal(typeof result.rawEntryCapResearch.secCoverOlderThan30DaysAtEntry,"number");
 assert.equal(typeof result.rawEntryCapResearch.laterSECShareCountChangeObserved,"number");
 assert.equal(typeof result.rawEntryCapResearch.sameVendorRawAdjustedEntryPriceMatches,"number");
 assert.equal(result.independentlyVerifiedHistoricalEntryCaps,0);
 assert.equal(result.sourceReviewedIntakeCases,0);
 assert.equal(result.fullYearCensusAudited,0);
 assert.equal(result.independentTradingCasesValidated,0);
 assert.equal(result.approvedRaasMetricCalibrations,0);
 assert.equal(result.approvedTradingWindow,null);
 assert.equal(result.rawEntryCapResearch.rows.length,9);
 assert.equal(result.status,"INCOMPLETE_2024_2025_CENSUS_RESEARCH_ONLY");
});

test("earlier 2023 SEC cover source is available for GERN's 2024-02 T-79 before 2024-02 10-K was published",()=>{
 const gern=primary.records.find(x=>x.ticker==="GERN");
 const event=gern.ticker+"|"+gern.pdufaTargetDate;
 const extraAdjusted=adjusted(),extraRaw=raw();
 extraAdjusted.set(event,bars("2024-02-01","2024-06-14",1.96));
 extraRaw.set(event,bars("2024-02-01","2024-06-14",1.96));
 const x=run({
  additionalEarliest:earliest,
  adjustedBarsByEvent:extraAdjusted,rawBarsByEvent:extraRaw
 });
 assert.equal(x.sameSessionRawAdjustedPricePairs,2);
 assert.equal(x.provisionalCapEstimates,2);
 const r=x.rows.find(y=>y.ticker==="GERN");
 assert.equal(r.proposedEntrySession,"2024-02-27");
 assert.equal(r.rawCloseAlpaca,1.96);
 assert.equal(r.secSharesOutstanding,543063950);
 assert.equal(r.secSharesMeasurementDate,"2023-10-31");
 assert.equal(r.secFirstConservativeUse,"2023-11-03");
 assert.equal(r.provisionalRawPriceTimesDatedSecCoverCapUsdMillions,1064.41);
 assert.equal(r.marketCap300MTo10BIndependentlyVerified,false);
 assert.equal(r.independentAdjustedPriceVendorVerified,false);
 assert.equal(r.approvedRaasScore,null);
 const without=run({adjustedBarsByEvent:extraAdjusted,rawBarsByEvent:extraRaw});
 assert.equal(without.rows.find(y=>y.ticker==="GERN").status,
  "NO_SEC_COVER_PUBLIC_BY_ENTRY");
});
test("extra SEC snapshot cannot backdate a later filing or overwrite the original SEC chain",()=>{
 const event="GERN|"+primary.records.find(x=>x.ticker==="GERN").pdufaTargetDate;
 const a=adjusted(),b=raw();
 a.set(event,bars("2024-02-01","2024-06-14",1.96));
 b.set(event,bars("2024-02-01","2024-06-14",1.96));
 const laterEarliest=clone(earliest);
 laterEarliest.records[0].firstConservativeEntryDate="2024-02-28";
 const r=run({additionalEarliest:laterEarliest,adjustedBarsByEvent:a,rawBarsByEvent:b});
 assert.equal(r.rows.find(x=>x.ticker==="GERN").status,"NO_SEC_COVER_PUBLIC_BY_ENTRY");
 const corrupt=clone(earliest);corrupt.records[0].sharesOutstanding=0;
 assert.throws(()=>run({additionalEarliest:corrupt}),/RAAS_RAW_CAP_SEC_RECORD_INVALID/);
 const wrong=clone(earliest);wrong.records[0].cik="0000000000";
 assert.throws(()=>run({additionalEarliest:wrong}),/RAAS_RAW_CAP_CASE_IDENTITY_OR_SEQUENCE_INVALID/);
 const future=clone(earliest);future.records[0].filedDate="2024-03-01";
 assert.throws(()=>run({additionalEarliest:future}),/RAAS_RAW_CAP_SEC_RECORD_INVALID/);
});
