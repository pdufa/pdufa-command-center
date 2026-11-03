"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const m=require("../scripts/raas_historical_ptct_2017_research.cjs");
const root=path.resolve(__dirname,".."),read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const primary=read("new-platform/frontend/data/raas-historical-2017-primary-source-leads.json");
const shares=read("new-platform/frontend/data/raas-2017-sec-cover-share-leads.json");
const earlier=read("new-platform/frontend/data/raas-preentry-2017-sec-cover-share-leads.json");
function bars(start,end,adjustment){
 const out=[];
 for(let t=Date.parse(start+"T00:00:00Z");t<=Date.parse(end+"T00:00:00Z");t+=86400000){
  const d=new Date(t),dow=d.getUTCDay();
  if(dow===0||dow===6)continue;
  const price=adjustment==="raw"?24:31+out.length*.08;
  out.push({t:d.toISOString().slice(0,10)+"T00:00:00Z",
   o:price-.04,h:price+.22,l:price-.2,c:price,v:144000});
 }
 return out;
}
function vendor({raw=24,error=null}={}){
 const seen=[],request=async(url,opt)=>{
  const u=new URL(url),a=u.searchParams.get("adjustment");
  assert.match(u.pathname,/\/v2\/stocks\/PTCT\/bars$/);
  assert.equal(u.searchParams.get("asof"),"2017-10-24");
  assert.equal(u.searchParams.get("feed"),"sip");
  assert.equal(u.searchParams.get("timeframe"),"1Day");
  assert.ok(["raw","all"].includes(a));
  assert.equal(opt.headers["APCA-API-KEY-ID"],"key");
  assert.equal(opt.headers["APCA-API-SECRET-KEY"],"secret");
  seen.push(a);
  if(error!==null)return {ok:false,status:error};
  const result=bars(u.searchParams.get("start"),u.searchParams.get("end"),a);
  if(a==="raw")for(const p of result)p.o=p.h=p.l=p.c=raw;
  return {ok:true,status:200,headers:{get:()=>"application/json"},
   text:async()=>JSON.stringify({symbol:"PTCT",bars:result,next_page_token:null})};
 };
 return {seen,request};
}
test("2017 FDA CRL public outcome separated from Phase 3 failure and exact original FDA letter date",()=>{
 const x=m.verifySources(primary,shares,earlier);
 assert.equal(x.year,2017);
 assert.equal(x.caseId,"PTCT|TRANSLARNA|NDA200896|2017");
 assert.equal(x.originalPublicPdufaGoal,"2017-10-24");
 assert.equal(x.firstPublicCrlDisclosureDate,"2017-10-25");
 assert.equal(x.researchActionDateProxy,"2017-10-25");
 assert.equal(x.originalFdaLetterDateVerified,false);
 assert.equal(x.fdaOutcome,"CRL");
 assert.equal(x.phase3PrimaryIttP,0.213);
 assert.equal(x.earlierPublishedShares,41244004);
 assert.equal(x.laterPublishedShares,41389046);
 assert.equal(x.publishedShareCountChange,145042);
 assert.match(x.original2015Phase3ResultsUrl,/ir.ptcbio.com\/node\/10111/);
});
test("PTCT live raw/adjusted requests and 3828 windows keep CRL research unapproved",async()=>{
 const v=vendor();
 const r=await m.execute({primary,shares,earlier,key:"key",secret:"secret",request:v.request});
 assert.deepEqual(v.seen,["raw","all"]);
 assert.equal(r.status,"2017_CRL_RESEARCH_ONLY");
 assert.equal(r.summary.sourcePrograms2017,1);
 assert.equal(r.summary.programWindowPairsEvaluated,3828);
 assert.ok(r.summary.priceResearchSessions>=65);
 assert.ok(r.summary.provisionalCapInRangeSessions>0);
 assert.ok(r.summary.earlierShareWindowAdds>0);
 const early=r.shareSnapshotWindowResearch[0].namedWindowDiagnostics.find(x=>
  x.entryLeadDays===79&&x.exitLeadDays===14);
 assert.equal(early.status,"UNVALIDATED_ADDITIONAL_PREENTRY_WINDOW_RESEARCH");
 assert.equal(early.supplementalShareFactUsed,true);
 assert.equal(early.validated,false);
 assert.equal(early.studyEligible,false);
 assert.ok(early.provisionalEntryCapMillions>=300);
 const later=r.shareSnapshotWindowResearch[0].namedWindowDiagnostics.find(x=>
  x.entryLeadDays===21&&x.exitLeadDays===3);
 assert.equal(later.supplementalShareFactUsed,false);
 assert.equal(later.historicalSharesSourceUsed,shares.records[0].sourceUrl);
 assert.equal(r.summary.validatedTradingCases,0);
 assert.equal(r.summary.approvedRaasScores,0);
 assert.equal(r.summary.fullTenYearCensusAudited,false);
});
test("below $300m does not create a return or a qualifying trade",async()=>{
 const x=await m.execute({primary,shares,earlier,key:"key",secret:"secret",
  request:vendor({raw:2.5}).request});
 assert.equal(x.summary.provisionalCapInRangeSessions,0);
 assert.equal(x.summary.provisionalCompletePriceWindows,0);
 const w=x.shareSnapshotWindowResearch[0].namedWindowDiagnostics.find(x=>
  x.entryLeadDays===79&&x.exitLeadDays===14);
 assert.equal(w.reason,"PROVISIONAL_ENTRY_CAP_OUTSIDE_300M_10B");
 assert.equal(w.provisionalNetReturnPct,null);
 assert.equal(x.summary.validatedTradingCases,0);
});
test("missing historical bars and authentication failures cannot masquerade as 2017 failures",async()=>{
 const denied=await m.execute({primary,shares,earlier,key:"",secret:"",
  request:async()=>{throw Error("must not request Alpaca");}});
 assert.equal(denied.status,"BLOCKED_MISSING_ALPACA_CREDENTIALS");
 assert.equal(denied.summary.priceResearchSessions,0);
 const miss=await m.execute({primary,shares,earlier,key:"key",secret:"secret",
  request:vendor({error:404}).request});
 assert.equal(miss.status,"BLOCKED_HISTORICAL_SYMBOL_PRICE_GAP");
 assert.equal(miss.providerGapCode,"RAAS_CAP_ALPACA_HTTP_404");
 assert.equal(miss.summary.validatedTradingCases,0);
 await assert.rejects(m.execute({primary,shares,earlier,key:"key",secret:"secret",
  request:vendor({error:401}).request}),/RAAS_CAP_ALPACA_HTTP_401/);
});
test("CRL date cannot be falsely promoted as verified FDA letter, trial cannot be declared positive",()=>{
 const change=mod=>({...primary,records:[{...primary.records[0],...mod}]});
 assert.throws(()=>m.verifySources(change({originalFdaCrlLetterDateIndependentlyVerified:true}),shares,earlier),
  /RAAS_2017_FDA_CRL_OR_TIMING_INVALID/);
 assert.throws(()=>m.verifySources(change({actualFDAOutcome:"APPROVED"}),shares,earlier),
  /RAAS_2017_FDA_CRL_OR_TIMING_INVALID/);
 assert.throws(()=>m.verifySources(change({phase3OverallIttPrimaryEndpointSignificant:true}),shares,earlier),
  /RAAS_2017_FDA_CRL_OR_TIMING_INVALID/);
 assert.throws(()=>m.verifySources(change({actualFDAActionDate:"2017-10-24"}),shares,earlier),
  /RAAS_2017_FDA_CRL_OR_TIMING_INVALID/);
});
test("SEC cover shares must be separately dated and newer fact unavailable to earlier entry",()=>{
 const bad=structuredClone(shares);
 bad.records[0].firstConservativeEntryDate="2017-08-09";
 assert.throws(()=>m.verifySources(primary,bad,earlier),/RAAS_CAP_SOURCE/);
 const spoof=structuredClone(earlier);
 spoof.records[0].ticker="BAD";
 assert.throws(()=>m.verifySources(primary,shares,spoof),/RAAS_CAP_SOURCE/);
 const changed=structuredClone(shares);
 changed.records[0].sharesOutstanding=41244004;
 assert.throws(()=>m.verifySources(primary,changed,earlier),/RAAS_2017_DATED_SHARES_SOURCE_INVALID/);
});
