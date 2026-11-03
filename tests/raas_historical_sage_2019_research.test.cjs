"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const m=require("../scripts/raas_historical_sage_2019_research.cjs");
const root=path.resolve(__dirname,".."),read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const primary=read("new-platform/frontend/data/raas-historical-2019-primary-source-leads.json");
const shares=read("new-platform/frontend/data/raas-2019-sec-cover-share-leads.json");
const earlier=read("new-platform/frontend/data/raas-preentry-2019-sec-cover-share-leads.json");
function bars(start,end,adjustment){
 const out=[];
 for(let t=Date.parse(start+"T00:00:00Z");t<=Date.parse(end+"T00:00:00Z");t+=86400000){
  const d=new Date(t),dow=d.getUTCDay();
  if(dow===0||dow===6)continue;
  const close=adjustment==="raw"?80:96+out.length*.08;
  out.push({t:d.toISOString().slice(0,10)+"T00:00:00Z",
   o:close-.02,h:close+.15,l:close-.18,c:close,v:220000});
 }
 return out;
}
function fakeRequest(){
 const seen=[];const request=async(url,opts)=>{
  const u=new URL(url),a=u.searchParams.get("adjustment");
  assert.match(u.pathname,/\/v2\/stocks\/SAGE\/bars$/);
  assert.equal(u.searchParams.get("asof"),"2019-03-19");
  assert.equal(u.searchParams.get("feed"),"sip");
  assert.equal(u.searchParams.get("timeframe"),"1Day");
  assert.ok(["raw","all"].includes(a));
  assert.equal(opts.headers["APCA-API-KEY-ID"],"fake");
  assert.equal(opts.headers["APCA-API-SECRET-KEY"],"fake2");
  seen.push(a);
  return {ok:true,status:200,headers:{get:()=>"application/json"},
   text:async()=>JSON.stringify({symbol:"SAGE",
    bars:bars(u.searchParams.get("start"),u.searchParams.get("end"),a),
    next_page_token:null})};
 };return {seen,request};
}
test("2019 SAGE Phase 3, REMS goal extension, FDA action and DEA marketing condition are distinct",()=>{
 const v=m.verifySources(primary,shares,earlier);
 assert.equal(v.caseId,"SAGE|ZULRESSO|NDA211371|2019");
 assert.equal(v.year,2019);
 assert.equal(v.ticker,"SAGE");
 assert.equal(v.initialPdufaTargetDate,"2018-12-19");
 assert.equal(v.revisedPdufaTargetDate,"2019-03-19");
 assert.equal(v.fdaActionDate,"2019-03-19");
 assert.equal(v.fdaApprovalLetterMarketingCondition,
  "DEA_SCHEDULING_REQUIRED_BEFORE_EFFECTIVE_MARKETING");
 assert.equal(v.priorPublishedShares,46887174);
 assert.equal(v.laterPublishedShares,47092657);
 assert.equal(v.changeInPublishedCoverShares,205483);
 assert.match(v.originalPhase3EvidenceSourceUrl,/d486951dex991/);
 assert.match(v.originalPdufaAnnouncementSourceUrl,/d674636dex991/);
});
test("SAGE 2019 SIP raw and separately adjusted simulated provider request never approves returns",async()=>{
 const {seen,request}=fakeRequest();
 const r=await m.execute({primary,shares,earlier,key:"fake",secret:"fake2",request});
 assert.deepEqual(seen,["raw","all"]);
 assert.equal(r.status,"2019_SAGE_PRICE_RESEARCH_NOT_CALIBRATION_READY");
 assert.equal(r.summary.sourcePrograms2019,1);
 assert.equal(r.summary.entryExitWindowsChecked,3828);
 assert.ok(r.summary.priceResearchSessions>=65);
 assert.ok(r.summary.provisional300mTo10bSessions>0);
 assert.ok(r.summary.supplementaryEarlierShareWindows>0);
 const named=r.earlyShareWindowDiagnostics[0].namedWindowDiagnostics.find(x=>
  x.entryLeadDays===79&&x.exitLeadDays===14);
 assert.equal(named.status,"UNVALIDATED_ADDITIONAL_PREENTRY_WINDOW_RESEARCH");
 assert.equal(named.supplementalShareFactUsed,true);
 assert.equal(named.studyEligible,false);
 assert.equal(named.validated,false);
 assert.ok(named.provisionalEntryCapMillions>=300);
 const later=r.earlyShareWindowDiagnostics[0].namedWindowDiagnostics.find(x=>
  x.entryLeadDays===30&&x.exitLeadDays===14);
 assert.equal(later.supplementalShareFactUsed,false);
 assert.equal(r.summary.validatedEventTrades,0);
 assert.equal(r.summary.approvedRaasScores,0);
 assert.equal(r.summary.tenYearCensusComplete,false);
});
test("missing provider keys are an explicit blocker, never zero-return observations",async()=>{
 const r=await m.execute({primary,shares,earlier,key:"",secret:"",
  request:async()=>{throw Error("provider should not be called");}});
 assert.equal(r.status,"BLOCKED_MISSING_ALPACA_CREDENTIALS");
 assert.equal(r.summary.priceResearchSessions,0);
 assert.equal(r.summary.validatedEventTrades,0);
 assert.equal(r.summary.approvedRaasScores,0);
});
test("historically absent delisted/as-of SAGE symbol is an auditable gap, not a fabricated loss",async()=>{
 const r=await m.execute({primary,shares,earlier,key:"fake",secret:"fake2",
  request:async()=>({ok:false,status:404})});
 assert.equal(r.status,"BLOCKED_HISTORICAL_PRICE_OR_SYMBOL_UNAVAILABLE");
 assert.equal(r.providerGapCode,"RAAS_CAP_ALPACA_HTTP_404");
 assert.equal(r.summary.priceResearchSessions,0);
 assert.equal(r.summary.validatedEventTrades,0);
 assert.equal(r.summary.approvedRaasScores,0);
 await assert.rejects(m.execute({primary,shares,earlier,key:"fake",secret:"fake2",
  request:async()=>({ok:false,status:401})}),/RAAS_CAP_ALPACA_HTTP_401/);
});
test("wrong FDA target, missing DEA exception and forged SEC share date fail closed",()=>{
 assert.throws(()=>m.verifySources({...primary,records:[
  {...primary.records[0],pdufaTargetDate:"2018-12-19"}]},shares,earlier),
  /RAAS_2019_SAGE_FDA_SOURCE_INVALID/);
 assert.throws(()=>m.verifySources({...primary,records:[
  {...primary.records[0],marketingDeferredPendingDEAScheduling:false}]},shares,earlier),
  /RAAS_2019_SAGE_FDA_SOURCE_INVALID/);
 const forged=structuredClone(shares);
 forged.records[0].firstConservativeEntryDate="2019-02-19";
 assert.throws(()=>m.verifySources(primary,forged,earlier),/RAAS_CAP_SOURCE/);
 const spoof=structuredClone(earlier);
 spoof.records[0].caseId="SAGE|WRONG|NDA111111|2019";
 assert.throws(()=>m.verifySources(primary,shares,spoof),/RAAS_PREENTRY_DUPLICATE_OR_UNMATCHED_CASE/);
});
