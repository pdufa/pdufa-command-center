"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const m=require("../scripts/raas_historical_provisional_window_grid.cjs");
const {minusDays}=require("../scripts/raas_alpaca_historical_price_study.cjs");
const root=path.resolve(__dirname,"..");
const primary=JSON.parse(fs.readFileSync(path.join(root,
 "new-platform/frontend/data/raas-historical-2020-primary-source-leads.json"),"utf8"));
const shares=JSON.parse(fs.readFileSync(path.join(root,
 "new-platform/frontend/data/raas-2020-sec-cover-share-leads.json"),"utf8"));
const rounded=n=>Math.round((n+Number.EPSILON)*100)/100;
function fixture(ticker="KALA"){
 const event=primary.records.find(x=>x.ticker===ticker);
 const share=shares.records.find(x=>x.caseId===event.caseId);
 const firstEvidence=[share.firstConservativeEntryDate,event.targetAnnouncementDate,event.phase3ReadoutDate].sort().at(-1);
 const observations=[];
 for(let n=100;n>=1;n--){
  const session=minusDays(event.pdufaTargetDate,n);
  if([0,6].includes(new Date(session+"T00:00:00Z").getUTCDay()))continue;
  const rawClose=20,adjustedClose=25+observations.length*0.15;
  const published=session>=firstEvidence;
  const cap=rawClose*share.sharesOutstanding/1000000;
  observations.push({session,rawClose,adjustedClose,
   sharesOutstandingKnownFromFiling:published?share.sharesOutstanding:null,
   historicMarketCapResearchMillions:published?rounded(cap):null,
   within300mTo10bUnreviewed:published?cap>=300&&cap<=10000:null,
   beforeActualFDAAction:session<event.actualFDAActionDate,
   sourceStatus:published?"RESEARCH_ONLY_NEEDS_SHARE_CLASS_AND_CORPORATE_ACTION_AUDIT":
    "PRE_DISCLOSURE_OR_MISSING_FACT",
   sourceUrl:share.sourceUrl});
 }
 const research={caseId:event.caseId,ticker,
  pdufaTargetDate:event.pdufaTargetDate,actualFDAActionDate:event.actualFDAActionDate,
  shareFactFiledDate:share.filedDate,
  conservativeEligibleInformationDate:share.firstConservativeEntryDate,
  originalSharesMeasurementDate:share.sharesMeasurementDate,
  shareFactSourceUrl:share.sourceUrl,source:"ALPACA_SIP_RAW_CLOSE_X_SEC_COVER_SHARES",
  priceReturnSource:"ALPACA_SIP_ADJUSTMENT_ALL_SEPARATE",
  status:"RAW_MARKET_CAP_DIAGNOSTICS_NOT_PROVEN_TRADING_ELIGIBILITY",
  approvedRaasRatings:0,eventTradeCasesValidated:0,observations};
 return {event,share,research};
}
function rawPayload(...x){
 return {scope:"RAAS_HISTORIC_RAW_CAP_RESEARCH",
  status:"UNVALIDATED_HISTORICAL_CAP_RESEARCH_ONLY",
  approvedRaasRatings:0,historicallyEligibleTrades:0,cases:x.map(v=>v.research)};
}
test("checks 3,828 exact calendar-offset entry/exit pairs; no optimal window is published",()=>{
 assert.equal(m.allWindows().length,3828);
 assert.equal(m.allWindows()[0].entryLeadDays,90);
 assert.equal(m.allWindows()[0].exitLeadDays,3);
 const result=m.build({primary,shares});
 assert.equal(result.cases.length,6);
 assert.equal(result.summary.programWindowEvaluations,6*3828);
 assert.equal(result.summary.provisionalWindowsWithCompletePriceAndTiming,0);
 assert.equal(result.summary.independentlyVerifiedEligibleTradingCases,0);
 assert.equal(result.summary.approvedRaasScores,0);
 assert.equal(result.summary.optimalWindowDeclared,false);
 assert.equal(result.issuerExposureGroups.length,1);
 assert.equal(result.issuerExposureGroups[0].ticker,"ESPR");
 assert.ok(result.cases.every(x=>x.reasonCounts.MISSING_LIVE_ALPACA_RAW_CAP_RESEARCH===3828));
});
test("T-79 to T-14 is shown as unvalidated when dated cap is available; no grade",()=>{
 const kala=fixture(),heron=fixture("HRTX");
 const r=m.build({primary,shares,rawCap:rawPayload(kala,heron)});
 const k=r.cases.find(x=>x.caseId===kala.event.caseId);
 const h=r.cases.find(x=>x.caseId===heron.event.caseId);
 const a=k.namedWindowDiagnostics.find(x=>x.entryLeadDays===79&&x.exitLeadDays===14);
 const b=h.namedWindowDiagnostics.find(x=>x.entryLeadDays===79&&x.exitLeadDays===14);
 assert.equal(a.status,"UNVALIDATED_RESEARCH_WINDOW_ONLY");
 assert.equal(a.studyEligible,false);
 assert.equal(a.validated,false);
 assert.ok(Number.isFinite(a.provisionalNetReturnPct));
 assert.ok(a.provisionalEntryCapMillions>300);
 assert.equal(b.reason,"SEC_SHARE_SOURCE_NOT_PUBLIC_AT_ENTRY");
 assert.equal(b.provisionalNetReturnPct,null);
 assert.equal(r.summary.independentlyVerifiedEligibleTradingCases,0);
 assert.equal(r.summary.optimalWindowDeclared,false);
});
test("early FDA action blocks T-14 to T-3 even if prices and shares exist",()=>{
 const k=fixture();
 const rows=m.guardedObservations(k.share,k.event,k.research);
 const a=m.evaluate(k.event,rows,14,3);
 assert.equal(k.event.actualFDAActionDate,"2020-10-26");
 assert.equal(a.reason,"EARLY_FDA_ACTION_CENSORS_EXIT");
 assert.equal(a.provisionalGrossReturnPct,null);
});
test("rejects provider rows that misstate caps, future filing, adjusted prices, action timing, session order",()=>{
 const f=fixture();
 const corruption=(mutate,re)=>{const x=structuredClone(f.research);mutate(x);assert.throws(
  ()=>m.guardedObservations(f.share,f.event,x),re);};
 corruption(x=>{x.observations.find(o=>o.historicMarketCapResearchMillions!==null)
  .historicMarketCapResearchMillions=4000},/CAP_OR_ASOF_CONTRADICTION/);
 corruption(x=>{x.observations[0].rawClose=-1},/UNTRUSTED_PRICE_ROW/);
 corruption(x=>{x.observations[0].adjustedClose=0},/UNTRUSTED_PRICE_ROW/);
 corruption(x=>{x.observations[0].beforeActualFDAAction=false},/UNTRUSTED_PRICE_ROW/);
 corruption(x=>{x.observations[2].session=x.observations[1].session},/UNTRUSTED_PRICE_ROW/);
 corruption(x=>{x.shareFactFiledDate="2020-01-01"},/SOURCE_META_INVALID/);
 corruption(x=>{x.observations.find(o=>o.sharesOutstandingKnownFromFiling===null)
  .sharesOutstandingKnownFromFiling=f.share.sharesOutstanding},/CAP_OR_ASOF_CONTRADICTION/);
});
test("blocked cap band cannot generate a provisional return",()=>{
 const f=fixture("ESPR"),event=f.event;
 const share=f.share;
 // Test specific record independently while keeping share arithmetic consistent.
 f.research.observations.forEach(o=>{
  const disclosed=o.sharesOutstandingKnownFromFiling!==null;
  o.rawClose=2;
  o.historicMarketCapResearchMillions=disclosed?
   rounded(2*share.sharesOutstanding/1000000):null;
  o.within300mTo10bUnreviewed=disclosed?false:null;
 });
 const rows=m.guardedObservations(share,event,f.research);
 const x=m.evaluate(event,rows,79,14);
 assert.equal(x.reason,"PROVISIONAL_ENTRY_CAP_OUTSIDE_300M_TO_10B");
 assert.equal(x.provisionalNetReturnPct,null);
});
