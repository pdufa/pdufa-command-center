"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const m=require("../scripts/raas_historical_preentry_share_window_research.cjs");
const {minusDays}=require("../scripts/raas_alpaca_historical_price_study.cjs");
const root=path.resolve(__dirname,".."),read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const primary=read("new-platform/frontend/data/raas-historical-2020-primary-source-leads.json");
const shares=read("new-platform/frontend/data/raas-2020-sec-cover-share-leads.json");
const preentry=read("new-platform/frontend/data/raas-preentry-2020-sec-cover-share-leads.json");
const rnd=n=>Math.round((n+Number.EPSILON)*100)/100;
function fixture(ticker){
 const event=primary.records.find(e=>e.ticker===ticker);
 const share=shares.records.find(s=>s.caseId===event.caseId);
 const evidenceDay=[share.firstConservativeEntryDate,
  event.targetAnnouncementDate,event.phase3ReadoutDate].sort().at(-1);
 const observations=[];
 for(let n=100;n>=1;n--){
  const session=minusDays(event.pdufaTargetDate,n);
  if([0,6].includes(new Date(session+"T00:00:00Z").getUTCDay()))continue;
  const rawClose=15,adjustedClose=20+observations.length*.05;
  const after=session>=evidenceDay;
  const cap=rawClose*share.sharesOutstanding/1000000;
  observations.push({session,rawClose,adjustedClose,
   sharesOutstandingKnownFromFiling:after?share.sharesOutstanding:null,
   historicMarketCapResearchMillions:after?rnd(cap):null,
   within300mTo10bUnreviewed:after?cap>=300&&cap<=10000:null,
   beforeActualFDAAction:session<event.actualFDAActionDate,
   sourceStatus:after?"RESEARCH_ONLY_NEEDS_SHARE_CLASS_AND_CORPORATE_ACTION_AUDIT":
    "PRE_DISCLOSURE_OR_MISSING_FACT",
   sourceUrl:share.sourceUrl});
 }
 const research={caseId:event.caseId,ticker:event.ticker,
  pdufaTargetDate:event.pdufaTargetDate,actualFDAActionDate:event.actualFDAActionDate,
  shareFactFiledDate:share.filedDate,
  conservativeEligibleInformationDate:share.firstConservativeEntryDate,
  originalSharesMeasurementDate:share.sharesMeasurementDate,
  shareFactSourceUrl:share.sourceUrl,
  status:"RAW_MARKET_CAP_DIAGNOSTICS_NOT_PROVEN_TRADING_ELIGIBILITY",
  eventTradeCasesValidated:0,approvedRaasRatings:0,
  observations};
 return {event,share,research};
}
function payload(...xs){
 return {scope:"RAAS_HISTORIC_RAW_CAP_RESEARCH",
  status:"UNVALIDATED_HISTORICAL_CAP_RESEARCH_ONLY",
  historicallyEligibleTrades:0,approvedRaasRatings:0,cases:xs.map(x=>x.research)};
}
test("HRTX and ICPT original 2019 annual covers are earlier than the already located Q1 filings",()=>{
 const found=m.validatePreentry({primary,shares,preentry});
 assert.equal(found.size,2);
 const h=found.get("HRTX|HTX011|NDA211988|2020");
 const i=found.get("ICPT|OCA_NASH|NDA212833|2020");
 assert.equal(h.sharesOutstanding,90374284);
 assert.equal(h.filedDate,"2020-03-02");
 assert.equal(h.firstConservativeEntryDate,"2020-03-03");
 assert.equal(i.sharesOutstanding,32853066);
 assert.equal(i.filedDate,"2020-02-25");
 assert.equal(i.firstConservativeEntryDate,"2020-02-26");
 assert.equal(shares.records.find(x=>x.ticker==="HRTX").sharesOutstanding-h.sharesOutstanding,267870);
 assert.equal(shares.records.find(x=>x.ticker==="ICPT").sharesOutstanding-i.sharesOutstanding,84365);
});
test("earlier dated SEC covers reopen T-79 to T-14 price research without validating actual trades",()=>{
 const h=fixture("HRTX"),i=fixture("ICPT");
 const report=m.build({primary,shares,preentry,rawCap:payload(h,i)});
 assert.equal(report.summary.sourcePrograms,6);
 assert.equal(report.summary.earlyCoverShareSourcePrograms,2);
 assert.equal(report.summary.gridWindowsChecked,6*3828);
 assert.ok(report.summary.newlyMeasurablePreentryWindows>0);
 for(const ticker of ["HRTX","ICPT"]){
  const c=report.cases.find(x=>x.ticker===ticker);
  const w=c.namedWindowDiagnostics.find(x=>x.entryLeadDays===79&&x.exitLeadDays===14);
  assert.equal(w.status,"UNVALIDATED_ADDITIONAL_PREENTRY_WINDOW_RESEARCH");
  assert.equal(w.supplementalShareFactUsed,true);
  assert.ok(w.provisionalEntryCapMillions>=300);
  assert.equal(w.studyEligible,false);
  assert.equal(w.validated,false);
  assert.ok(c.newlyMeasurablePreentryWindows>0);
 }
 assert.equal(report.summary.independentlyValidatedEventTrades,0);
 assert.equal(report.summary.approvedRaasScores,0);
 assert.equal(report.summary.optimalWindowDeclared,false);
});
test("original current filings supersede prior covers from their own publication dates",()=>{
 const h=fixture("HRTX");
 const earlier=preentry.records.find(x=>x.ticker==="HRTX");
 const bars=m.validateBars(h.research,h.event,h.share);
 const near=m.evaluate(h.event,bars,earlier,h.share,30,14);
 assert.equal(near.supplementalShareFactUsed,false);
 assert.equal(near.historicalSharesSourceUsed,h.share.sourceUrl);
 const old=m.evaluate(h.event,bars,earlier,h.share,79,14);
 assert.equal(old.supplementalShareFactUsed,true);
 assert.equal(old.historicalSharesSourceUsed,earlier.sourceUrl);
});
test("future disclosure, early FDA action and missing historical share source are not treated as returns",()=>{
 const i=fixture("ICPT"),bars=m.validateBars(i.research,i.event,i.share);
 const earlier=preentry.records.find(x=>x.ticker==="ICPT");
 const future=m.evaluate(i.event,bars,{...earlier,firstConservativeEntryDate:"2020-08-01"},i.share,79,14);
 assert.equal(future.reason,"NO_DATED_SHARE_SOURCE_KNOWN_AT_ENTRY");
 assert.equal(future.provisionalNetReturnPct,null);
 const k=fixture("KALA");
 const kBars=m.validateBars(k.research,k.event,k.share);
 const early=m.evaluate(k.event,kBars,null,k.share,14,3);
 assert.equal(early.reason,"EARLY_FDA_ACTION_CENSORS_EXIT");
 assert.equal(early.provisionalNetReturnPct,null);
});
test("reject wrong filing identity, future old shares and fabricated raw bars",()=>{
 const dup=structuredClone(preentry);
 dup.records.push(dup.records[0]);
 assert.throws(()=>m.validatePreentry({primary,shares,preentry:dup}),/DUPLICATE_OR_UNMATCHED_CASE/);
 const wrong=structuredClone(preentry);
 wrong.records[0].ticker="ICPT";
 assert.throws(()=>m.validatePreentry({primary,shares,preentry:wrong}),/SOURCE_IDENTITY_OR_ASOF_INVALID/);
 const future=structuredClone(preentry);
 future.records[1].firstConservativeEntryDate="2020-06-20";
 assert.throws(()=>m.validatePreentry({primary,shares,preentry:future}),/WRONG_CHRONOLOGY_OR_SHARE_CLASS/);
 const h=fixture("HRTX");
 h.research.observations[1].rawClose=0;
 assert.throws(()=>m.validateBars(h.research,h.event,h.share),/RAW_BAR_INVALID/);
});
test("a missing live Alpaca feed never generates synthetic market-cap windows",()=>{
 const report=m.build({primary,shares,preentry});
 assert.equal(report.status,"BLOCKED_NO_LIVE_ALPACA_RESEARCH");
 assert.equal(report.summary.newlyMeasurablePreentryWindows,0);
 assert.equal(report.cases.find(x=>x.ticker==="ICPT")
  .namedWindowDiagnostics.find(x=>x.entryLeadDays===79&&x.exitLeadDays===14)
  .reason,"MISSING_LIVE_ALPACA_RAW_PRICES");
});
