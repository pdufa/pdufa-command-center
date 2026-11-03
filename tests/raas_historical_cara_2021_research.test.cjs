"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const m=require("../scripts/raas_historical_cara_2021_research.cjs");
const {validateSourceLeads}=require("../scripts/raas_historical_event_census_worklist.cjs");
const root=path.resolve(__dirname,".."),read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const primary=read("new-platform/frontend/data/raas-historical-2021-primary-source-leads.json");
const shares=read("new-platform/frontend/data/raas-2021-sec-cover-share-leads.json");
const earlier=read("new-platform/frontend/data/raas-preentry-2021-sec-cover-share-leads.json");
function dailyBars(start,end,adjustment){
 const bars=[];for(let t=Date.parse(start+"T00:00:00Z");t<=Date.parse(end+"T00:00:00Z");t+=86400000){
  const d=new Date(t),wd=d.getUTCDay();if(wd===0||wd===6)continue;
  const close=adjustment==="raw"?12:15+bars.length*.04;
  bars.push({t:d.toISOString().slice(0,10)+"T00:00:00Z",o:close-.1,h:close+.15,l:close-.2,c:close,v:85000});
 }
 return bars;
}
function testRequest(){
 const seen=[];const fn=async (url,opts)=>{
  const u=new URL(url),params=u.searchParams,adjustment=params.get("adjustment");
  assert.match(u.pathname,/\/v2\/stocks\/CARA\/bars$/);
  assert.equal(params.get("feed"),"sip");
  assert.equal(params.get("asof"),"2021-08-23");
  assert.equal(params.get("timeframe"),"1Day");
  assert.ok(["raw","all"].includes(adjustment));
  assert.equal(opts.headers["APCA-API-KEY-ID"],"fake");
  assert.equal(opts.headers["APCA-API-SECRET-KEY"],"fake2");
  seen.push(adjustment);
  return {ok:true,status:200,headers:{get:()=>"application/json"},
   text:async()=>JSON.stringify({symbol:"CARA",
    bars:dailyBars(params.get("start"),params.get("end"),adjustment),
    next_page_token:null})};
 };return {seen,request:fn};
}
test("2021 CARA FDA review has independently dated public goal, Phase 3 and FDA original approval",()=>{
 const x=m.verifySources(primary,shares,earlier);
 assert.equal(validateSourceLeads(primary).length,1);
 assert.equal(x.ticker,"CARA");
 assert.equal(x.year,2021);
 assert.equal(x.caseId,"CARA|KORSUVA|NDA214916|2021");
 assert.match(x.originalFDAApprovalSourceUrl,/214916Orig1s000Approv\.pdf/);
 assert.match(x.originalPdufaSourceUrl,/202103.*ex99/);
 assert.equal(x.earlierPublishedShares,49876763);
 assert.equal(x.laterPublishedShares,50052011);
 assert.equal(x.publishedShareCountChange,175248);
});
test("2021 live SIP raw and adjusted data remain preliminary and never select a trade window",async()=>{
 const {seen,request}=testRequest();
 const x=await m.execute({primary,shares,earlier,key:"fake",secret:"fake2",request});
 assert.deepEqual(seen,["raw","all"]);
 assert.equal(x.status,"2021_RESEARCH_ONLY_NOT_CALIBRATION_READY");
 assert.equal(x.summary.sourcePrograms2021,1);
 assert.equal(x.summary.entryExitWindowsChecked,3828);
 assert.ok(x.summary.priceResearchSessions>=65);
 assert.ok(x.summary.provisional300mTo10bSessions>0);
 assert.ok(x.summary.provisionalWindows>0);
 const named=x.perCaseWindowDiagnostics[0].namedWindowDiagnostics.find(x=>
  x.entryLeadDays===79&&x.exitLeadDays===14);
 assert.equal(named.status,"UNVALIDATED_RESEARCH_WINDOW_ONLY");
 assert.equal(named.studyEligible,false);
 assert.equal(named.validated,false);
 assert.ok(named.provisionalEntryCapMillions>=300);
 assert.equal(x.shareSnapshotResearch[0].publishedCoverShareCountChange,175248);
 assert.equal(x.summary.validatedEventTrades,0);
 assert.equal(x.summary.approvedRaasScores,0);
 assert.equal(x.summary.tenYearCensusComplete,false);
 assert.equal(x.rawCapResearch[0].approvedRaasRatings,0);
});
test("missing credentials never simulate prices or promote research",async()=>{
 const x=await m.execute({primary,shares,earlier,key:"",secret:"",
  request:async()=>{throw Error("must not query vendor");}});
 assert.equal(x.status,"BLOCKED_MISSING_ALPACA_CREDENTIALS");
 assert.equal(x.summary.priceResearchSessions,0);
 assert.equal(x.summary.validatedEventTrades,0);
 assert.equal(x.summary.approvedRaasScores,0);
});
test("cross-year case cannot be spoofed or combine old and later SEC facts as one entry-time fact",()=>{
 assert.throws(()=>m.verifySources({...primary,records:[
  {...primary.records[0],actualFDAActionDate:"2021-08-22"}]},shares,earlier),
  /SOURCE_PROGRAM_IDENTITY_INVALID/);
 assert.throws(()=>m.verifySources({...primary,records:[
  {...primary.records[0],targetAnnouncementDate:"2021-08-24"}]},shares,earlier),
  /RAAS_PRIMARY_EVENT_SOURCE_INVALID/);
 const bad=structuredClone(shares);
 bad.records[0].firstConservativeEntryDate="2021-05-10";
 assert.throws(()=>m.verifySources(primary,bad,earlier),/RAAS_CAP_SOURCE/);
 const later=structuredClone(shares);
 later.records[0].sharesOutstanding=49876763;
 assert.throws(()=>m.verifySources(primary,later,earlier),/HISTORICAL_SHARE_CHRONOLOGY_INVALID/);
 const conflict=structuredClone(earlier);
 conflict.records[0].caseId="CARA|FAKE|NDA222222|2021";
 assert.throws(()=>m.verifySources(primary,shares,conflict),/DUPLICATE_OR_UNMATCHED_CASE/);
});
