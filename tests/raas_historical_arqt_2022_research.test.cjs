"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const m=require("../scripts/raas_historical_arqt_2022_research.cjs");
const root=path.resolve(__dirname,"..");
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const primary=read("new-platform/frontend/data/raas-historical-2022-primary-source-leads.json");
const shares=read("new-platform/frontend/data/raas-2022-sec-cover-share-leads.json");
const earlier=read("new-platform/frontend/data/raas-preentry-2022-sec-cover-share-leads.json");
function bars(start,end,adjustment){
 const out=[];
 for(let t=Date.parse(start+"T00:00:00Z");t<=Date.parse(end+"T00:00:00Z");t+=86400000){
  const d=new Date(t),dow=d.getUTCDay();
  if(dow===0||dow===6)continue;
  const close=adjustment==="raw"?13.5:17+out.length*.05;
  out.push({t:d.toISOString().slice(0,10)+"T00:00:00Z",o:close-.05,
   h:close+.15,l:close-.2,c:close,v:135000});
 }
 return out;
}
function testRequest(){
 const seen=[];
 const request=async(url,options)=>{
  const u=new URL(url),a=u.searchParams.get("adjustment");
  assert.match(u.pathname,/\/v2\/stocks\/ARQT\/bars$/);
  assert.equal(u.searchParams.get("feed"),"sip");
  assert.equal(u.searchParams.get("asof"),"2022-07-29");
  assert.equal(u.searchParams.get("timeframe"),"1Day");
  assert.ok(["raw","all"].includes(a));
  assert.equal(options.headers["APCA-API-KEY-ID"],"fake");
  assert.equal(options.headers["APCA-API-SECRET-KEY"],"fake2");
  seen.push(a);
  return {ok:true,status:200,headers:{get:()=>"application/json"},
   text:async()=>JSON.stringify({symbol:"ARQT",
    bars:bars(u.searchParams.get("start"),u.searchParams.get("end"),a),
    next_page_token:null})};
 };
 return {seen,request};
}
test("original FDA 2022 NDA 215985, DERMIS-1/2, and public PDUFA goal link exactly",()=>{
 const v=m.verifySources(primary,shares,earlier);
 assert.equal(v.caseId,"ARQT|ZORYVE_CREAM|NDA215985|2022");
 assert.equal(v.year,2022);
 assert.equal(v.ticker,"ARQT");
 assert.match(v.originalFDAApprovalUrl,/215985Orig1s000ltr.pdf/);
 assert.match(v.originalPdufaAnnouncementUrl,/arqt-20211222.htm/);
 assert.match(v.originalPhase3ReadoutUrl,/arqt-20210201.htm/);
 assert.equal(v.earlierShares,50380254);
 assert.equal(v.laterShares,51417963);
 assert.equal(v.changeInPublishedCoverShares,1037709);
});
test("2022 US market raw-close and adjusted SIP prices remain separate and unapproved",async()=>{
 const {seen,request}=testRequest();
 const r=await m.execute({primary,shares,earlier,key:"fake",secret:"fake2",request});
 assert.deepEqual(seen,["raw","all"]);
 assert.equal(r.status,"2022_RESEARCH_ONLY_NOT_CALIBRATION_READY");
 assert.equal(r.summary.sourcePrograms2022,1);
 assert.equal(r.summary.windowsChecked,3828);
 assert.ok(r.summary.priceResearchSessions>=65);
 assert.ok(r.summary.provisional300mTo10bSessions>0);
 assert.ok(r.summary.provisionalWindows>0);
 const named=r.perCaseWindowDiagnostics[0].namedWindowDiagnostics.find(w=>
  w.entryLeadDays===79&&w.exitLeadDays===14);
 assert.equal(named.status,"UNVALIDATED_RESEARCH_WINDOW_ONLY");
 assert.equal(named.studyEligible,false);
 assert.equal(named.validated,false);
 assert.ok(named.provisionalEntryCapMillions>=300);
 assert.equal(r.earlierShareWindowDiagnostics[0].publishedCoverShareCountChange,1037709);
 assert.ok(r.summary.newlyMeasurableEarlierShareWindows>0);
 assert.equal(r.summary.validatedEventTrades,0);
 assert.equal(r.summary.approvedRaasScores,0);
 assert.equal(r.summary.tenYearCensusComplete,false);
 assert.equal(r.rawCapResearch[0].approvedRaasRatings,0);
});
test("missing credentials do not use mocked research to construct trading records",async()=>{
 const r=await m.execute({primary,shares,earlier,key:"",secret:"",
  request:async()=>{throw Error("should never call provider");}});
 assert.equal(r.status,"BLOCKED_MISSING_ALPACA_CREDENTIALS");
 assert.equal(r.summary.priceResearchSessions,0);
 assert.equal(r.summary.validatedEventTrades,0);
 assert.equal(r.summary.approvedRaasScores,0);
});
test("wrong review date, wrong source case, and after-close early share leakage are blocked",()=>{
 assert.throws(()=>m.verifySources({...primary,records:[
  {...primary.records[0],actualFDAActionDate:"2022-07-28"}]},shares,earlier),
  /RAAS_2022_PRIMARY_IDENTITY_INVALID/);
 assert.throws(()=>m.verifySources({...primary,records:[
  {...primary.records[0],targetAnnouncementDate:"2022-08-01"}]},shares,earlier),
  /RAAS_PRIMARY_EVENT_SOURCE_INVALID/);
 const q=structuredClone(shares);
 q.records[0].firstConservativeEntryDate="2022-05-05";
 assert.throws(()=>m.verifySources(primary,q,earlier),/RAAS_CAP_SOURCE/);
 const e=structuredClone(earlier);e.records[0].caseId="ARQT|FAKE|NDA000000|2022";
 assert.throws(()=>m.verifySources(primary,shares,e),/DUPLICATE_OR_UNMATCHED_CASE/);
 const altered=structuredClone(shares);altered.records[0].sharesOutstanding=50380254;
 assert.throws(()=>m.verifySources(primary,altered,earlier),/RAAS_2022_SHARE_SOURCE_INVALID/);
});
