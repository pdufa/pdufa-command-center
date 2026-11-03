"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const m=require("../scripts/raas_historical_acrx_2018_research.cjs");
const root=path.resolve(__dirname,".."),load=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const primary=load("new-platform/frontend/data/raas-historical-2018-primary-source-leads.json");
const shares=load("new-platform/frontend/data/raas-2018-sec-cover-share-leads.json");
const earlier=load("new-platform/frontend/data/raas-preentry-2018-sec-cover-share-leads.json");
function bars(start,end,adjustment){
 const arr=[];
 for(let t=Date.parse(start+"T00:00:00Z");t<=Date.parse(end+"T00:00:00Z");t+=86400000){
  const d=new Date(t),day=d.getUTCDay();if(day===0||day===6)continue;
  const close=adjustment==="raw"?6.7:15+arr.length*.045;
  arr.push({t:d.toISOString().slice(0,10)+"T00:00:00Z",
   o:close-.03,h:close+.2,l:close-.2,c:close,v:195000});
 }
 return arr;
}
function provider(close=6.7){
 const seen=[],request=async(url,options)=>{
  const u=new URL(url),a=u.searchParams.get("adjustment");
  assert.match(u.pathname,/\/v2\/stocks\/ACRX\/bars$/);
  assert.equal(u.searchParams.get("asof"),"2018-11-03");
  assert.equal(u.searchParams.get("feed"),"sip");
  assert.equal(u.searchParams.get("timeframe"),"1Day");
  assert.ok(["raw","all"].includes(a));
  assert.equal(options.headers["APCA-API-KEY-ID"],"fake");
  assert.equal(options.headers["APCA-API-SECRET-KEY"],"fake2");
  seen.push(a);
  const b=bars(u.searchParams.get("start"),u.searchParams.get("end"),a);
  if(a==="raw")for(const x of b)x.o=x.h=x.l=x.c=close;
  return {ok:true,status:200,headers:{get:()=>"application/json"},
   text:async()=>JSON.stringify({symbol:"ACRX",bars:b,next_page_token:null})};
 };
 return {seen,request};
}
test("2018 public Nov 3 PDUFA, retrospective FDA Nov 2 goal and action never collapse into one date",()=>{
 const s=m.verifySources(primary,shares,earlier);
 assert.equal(s.caseId,"ACRX|DSUVIA|NDA209128|2018");
 assert.equal(s.year,2018);
 assert.equal(s.ticker,"ACRX");
 assert.equal(s.firstLocatedPublicPdufaTarget,"2018-11-03");
 assert.equal(s.retrospectiveInternalFdaGoalDate,"2018-11-02");
 assert.equal(s.actualFdaActionDate,"2018-11-02");
 assert.equal(s.priorCrLActionDate,"2017-10-11");
 assert.match(s.targetSourceUrl,/acelrx-announces-fda-acceptance/);
 assert.match(s.actionSourceUrl,/209128Orig1s000Ltr\.pdf/);
 assert.match(s.phase3SourceUrl,/038720\/ex99-1/);
 assert.equal(s.oldPublishedShares,51320598);
 assert.equal(s.newPublishedShares,60599914);
 assert.equal(s.publishedCoverShareIncrease,9279316);
});
test("2018 ACRX research: exactly 3828 T-90..T-3 windows, distinct raw and adjusted data, no grade",async()=>{
 const {seen,request}=provider();
 const x=await m.execute({primary,shares,earlier,key:"fake",secret:"fake2",request});
 assert.deepEqual(seen,["raw","all"]);
 assert.equal(x.status,"2018_ACRX_RAW_CAP_RESEARCH_NOT_ELIGIBILITY");
 assert.equal(x.summary.sourcePrograms2018,1);
 assert.equal(x.summary.windowPairsChecked,3828);
 assert.ok(x.summary.priceResearchSessions>=65);
 assert.ok(x.summary.preliminaryCapInRangeSessions>0);
 assert.ok(x.summary.provisionalPriceAndCapWindows>0);
 assert.equal(x.summary.addedEarlierShareWindows,0); // May Q1 superseded Aug 3 before T-90
 assert.equal(x.summary.approvedRaasScores,0);
 assert.equal(x.summary.validatedTradingCases,0);
 assert.equal(x.summary.fullTenYearCensusAudited,false);
 const named=x.shareSnapshotsAndWindows[0].namedWindowDiagnostics.find(w=>
  w.entryLeadDays===79&&w.exitLeadDays===14);
 assert.equal(named.status,"UNVALIDATED_ADDITIONAL_PREENTRY_WINDOW_RESEARCH");
 assert.equal(named.supplementalShareFactUsed,false);
 assert.equal(named.studyEligible,false);
 assert.equal(named.validated,false);
 assert.ok(named.provisionalEntryCapMillions>=300);
 assert.equal(x.shareSnapshotsAndWindows[0].publishedCoverShareCountChange,9279316);
});
test("cap below $300m returns explicit exclusion without inventing successful trades",async()=>{
 const {request}=provider(2.5);
 const x=await m.execute({primary,shares,earlier,key:"fake",secret:"fake2",request});
 assert.equal(x.summary.preliminaryCapInRangeSessions,0);
 assert.equal(x.summary.provisionalPriceAndCapWindows,0);
 const named=x.shareSnapshotsAndWindows[0].namedWindowDiagnostics.find(w=>
  w.entryLeadDays===79&&w.exitLeadDays===14);
 assert.equal(named.reason,"PROVISIONAL_ENTRY_CAP_OUTSIDE_300M_10B");
 assert.equal(named.provisionalNetReturnPct,null);
 assert.equal(x.summary.validatedTradingCases,0);
});
test("provider absent ticker and auth errors are not silently represented as losing stocks",async()=>{
 const missing=await m.execute({primary,shares,earlier,key:"fake",secret:"fake2",
  request:async()=>({ok:false,status:404})});
 assert.equal(missing.status,"BLOCKED_ASOF_SYMBOL_OR_PRICE_HISTORY_UNAVAILABLE");
 assert.equal(missing.providerGapCode,"RAAS_CAP_ALPACA_HTTP_404");
 assert.equal(missing.summary.priceResearchSessions,0);
 assert.equal(missing.summary.validatedTradingCases,0);
 const blocked=await m.execute({primary,shares,earlier,key:"",secret:""});
 assert.equal(blocked.status,"BLOCKED_MISSING_ALPACA_CREDENTIALS");
 await assert.rejects(m.execute({primary,shares,earlier,key:"fake",secret:"fake2",
  request:async()=>({ok:false,status:401})}),/RAAS_CAP_ALPACA_HTTP_401/);
});
test("forged company public PDUFA day, internal goal, prior CRL and SEC chronology fail closed",()=>{
 const spoof=changes=>({...primary,records:[{...primary.records[0],...changes}]});
 assert.throws(()=>m.verifySources(spoof({pdufaTargetDate:"2018-11-02"}),shares,earlier),
  /RAAS_2018_ACRX_FDA_SOURCE_INVALID/);
 assert.throws(()=>m.verifySources(spoof({fdaInternalGoalFromRetrospectiveReviewDate:"2018-11-03"}),shares,earlier),
  /RAAS_2018_ACRX_FDA_SOURCE_INVALID/);
 assert.throws(()=>m.verifySources(spoof({priorCRLReviewCycleDifferent:false}),shares,earlier),
  /RAAS_2018_ACRX_FDA_SOURCE_INVALID/);
 const forged=structuredClone(shares);
 forged.records[0].firstConservativeEntryDate="2018-08-02";
 assert.throws(()=>m.verifySources(primary,forged,earlier),/RAAS_CAP_SOURCE/);
 const bad=structuredClone(earlier);bad.records[0].ticker="BAD";
 assert.throws(()=>m.verifySources(primary,shares,bad),/RAAS_CAP_SOURCE/);
});
