"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const m=require("../scripts/raas_active_2024_2025_primary_cap_research.cjs");
const root=path.resolve(__dirname,"..");
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const events=read("new-platform/frontend/data/raas-active-2024-2025-primary-source-leads.json");
const shares=read("new-platform/frontend/data/raas-active-2024-2025-sec-cover-share-leads.json");
const earlier=read("new-platform/frontend/data/raas-active-2024-2025-preentry-sec-share-leads.json");
const intake=read("new-platform/frontend/data/raas-active-2024-2025-pdufa-intake.json");
const cases=events.records;
function fakePrices(){
 const seen=[];
 const request=async(uri,headers)=>{
  const u=new URL(uri),ticker=u.pathname.split("/")[3],adjustment=u.searchParams.get("adjustment");
  assert.ok(["ARQT","AXSM","MDGL","GERN","SLNO","LXRX"].includes(ticker));
  assert.ok(["raw","all"].includes(adjustment));
  assert.equal(u.searchParams.get("feed"),"sip");
  assert.equal(u.searchParams.get("timeframe"),"1Day");
  assert.equal(u.searchParams.get("asof"),ticker==="ARQT"?"2024-07-07":ticker==="MDGL"?"2024-03-14":ticker==="GERN"?"2024-06-16":ticker==="SLNO"?"2025-03-27":ticker==="LXRX"?"2024-12-20":"2025-01-31");
  assert.equal(headers.headers["APCA-API-KEY-ID"],"key");
  assert.equal(headers.headers["APCA-API-SECRET-KEY"],"secret");
  seen.push(ticker+"|"+adjustment);
  const bars=[];
  const start=u.searchParams.get("start"),end=u.searchParams.get("end");
  for(let t=Date.parse(start+"T00:00:00Z");t<=Date.parse(end+"T00:00:00Z");t+=86400000){
   const d=new Date(t),dow=d.getUTCDay();if(dow===0||dow===6)continue;
   const base=ticker==="ARQT"?7:ticker==="MDGL"?230:ticker==="GERN"?3:ticker==="SLNO"?55:ticker==="LXRX"?1.30:92;
   const c=adjustment==="raw"?base:base+bars.length*.05;
   bars.push({t:d.toISOString().slice(0,10)+"T00:00:00Z",
    o:c-.05,h:c+.2,l:c-.2,c,v:250000});
  }
  return {ok:true,status:200,headers:{get:()=>"application/json"},
   text:async()=>JSON.stringify({symbol:ticker,bars,next_page_token:null})};
 };
 return {seen,request};
}
test("source queue has four separately sourced 2024 targets including CRL and two 2025 targets; none is a validated trade",()=>{
 const facts=m.verify(events,shares,earlier,intake);
 assert.deepEqual(facts.map(x=>x.year),[2024,2024,2024,2024,2025,2025]);
 assert.deepEqual(facts.map(x=>x.ticker),["MDGL","GERN","ARQT","LXRX","AXSM","SLNO"]);
 assert.equal(facts[0].pdufaTargetDate,"2024-03-14");
 assert.equal(facts[0].actualFDAActionDate,"2024-03-14");
 assert.equal(facts[0].reportedCoverShareChange,154779);
 assert.equal(facts[1].pdufaTargetDate,"2024-06-16");
 assert.equal(facts[1].actualFDAActionDate,"2024-06-06");
 assert.equal(facts[1].reportedCoverShareChange,47073231);
 assert.equal(facts[2].pdufaTargetDate,"2024-07-07");
 assert.equal(facts[2].actualFDAActionDate,"2024-07-09");
 assert.equal(facts[3].pdufaTargetDate,"2024-12-20");
 assert.equal(facts[3].actualFDAActionDate,"2024-12-20");
 assert.equal(facts[3].reportedCoverShareChange,0);
 assert.equal(facts[4].pdufaTargetDate,"2025-01-31");
 assert.equal(facts[4].actualFDAActionDate,"2025-01-30");
 assert.equal(facts[2].reportedCoverShareChange,18950801);
 assert.equal(facts[4].reportedCoverShareChange,462171);
 assert.equal(facts[5].pdufaTargetDate,"2025-03-27");
 assert.equal(facts[5].actualFDAActionDate,"2025-03-26");
 assert.equal(facts[5].reportedCoverShareChange,2739859);
 assert.ok(facts.every(x=>x.eligibleForApprovedTrading===false));
});
test("original FDA 2024 after-goal action and 2025 early approval remain distinct, including prior NDA review cycle",()=>{
 assert.equal(cases[0].fdaDecisionAfterPdufaGoalDays,2);
 assert.equal(cases[0].formalGoalExtensionIndependentlyVerified,false);
 assert.equal(cases[0].targetAnnouncementDate,"2023-11-29");
 assert.equal(cases[0].phase3ReadoutDate,"2022-12-12");
 assert.equal(cases[1].fdaActionEarlierThanPdufaGoalDays,1);
 assert.equal(cases[1].previousCRLAddressedInResubmission,true);
 assert.equal(cases[1].initial2022CRLNot2025Outcome,true);
 assert.equal(cases[1].phase3ReadoutDate,"2020-04-06");
 assert.equal(cases[1].targetAnnouncementDate,"2024-09-04");
});
test("historical Alpaca RAW plus separately adjusted prices remain research-only for both years",async()=>{
 const fake=fakePrices();
 const r=await m.execute({events,shares,earlier,intake,key:"key",secret:"secret",
  request:fake.request});
 assert.deepEqual(fake.seen,["ARQT|raw","ARQT|all","AXSM|raw","AXSM|all","MDGL|raw","MDGL|all","GERN|raw","GERN|all","SLNO|raw","SLNO|all","LXRX|raw","LXRX|all"]);
 assert.equal(r.status,"2024_2025_SOURCE_LEADS_UNVALIDATED_PRICE_RESEARCH");
 assert.equal(r.sourceLeadCount,6);
 assert.deepEqual(r.sourceLeadYears,[2024,2025]);
 assert.equal(r.reviewedIntakeCases,0);
 assert.equal(r.plannedWindowPairsExamined,6*3828);
 assert.ok(r.rawHistoricalSessions>=390);
 assert.ok(r.provisionalCapIn300mTo10bResearchSessions>0);
 assert.ok(r.provisionalPrimaryWindowRows>0);
 assert.ok(r.provisionalEarlierShareWindows>0);
 assert.equal(r.fullYearCensusesAudited,0);
 assert.equal(r.validatedTradingCases,0);
 assert.equal(r.approvedRaasMetrics,0);
 assert.equal(r.selectedOptimalWindow,null);
 assert.ok(r.caseResearch.every(x=>x.namedWindow79to14.studyEligible===false));
 assert.ok(r.caseResearch.every(x=>x.namedWindow79to14.validated===false));
 assert.equal(r.caseResearch[0].namedWindow79to14.supplementalShareFactUsed,true);
 assert.equal(r.caseResearch[1].namedWindow79to14.supplementalShareFactUsed,false);
});
test("unreviewed leads cannot silently enter accepted two-year intake or add a third year",()=>{
 const fake=structuredClone(intake);
 fake.records.push({caseId:cases[0].caseId});
 assert.throws(()=>m.verify(events,shares,earlier,fake),/MUST_NOT_COUNT_AS_ACCEPTED_INTAKE/);
 const wrong=structuredClone(events);
 wrong.records[0].pdufaTargetDate="2023-07-07";
 assert.throws(()=>m.verify(wrong,shares,earlier,intake),
  /PRIMARY_EVENT_SOURCE_INVALID|ACTIVE_ORIGINAL_TARGET_ACTION_IDENTITY_INVALID/);
 const changed=structuredClone(events);
 changed.records[1].actualFDAActionDate="2025-01-31";
 assert.throws(()=>m.verify(changed,shares,earlier,intake),
  /ACTIVE_ORIGINAL_TARGET_ACTION_IDENTITY_INVALID/);
});
test("unpublished SEC cover shares and fabricated share counts fail closed",()=>{
 const later=structuredClone(shares);
 later.records[1].firstConservativeEntryDate="2024-11-12";
 assert.throws(()=>m.verify(events,later,earlier,intake),
  /ACTIVE_SEC_COVER_SHARE_CHRONOLOGY_INVALID|SECURITIES_DISCLOSURE_MISMATCH|CAP_SOURCE/);
 const old=structuredClone(earlier);
 old.records[0].sharesOutstanding=115764164;
 assert.throws(()=>m.verify(events,shares,old,intake),
  /2024_SECURITIES_DISCLOSURE_MISMATCH/);
 const fake=structuredClone(shares);
 fake.records[0].ticker="AXSM";
 assert.throws(()=>m.verify(events,fake,earlier,intake),
  /CAP_SOURCE|PREENTRY/);
});
test("without Alpaca credentials the active original source study never fabricates any sessions or scores",async()=>{
 const r=await m.execute({events,shares,earlier,intake,key:"",secret:"",
  request:async()=>{throw Error("No vendor request allowed");}});
 assert.equal(r.status,"BLOCKED_MISSING_ALPACA_CREDENTIALS");
 assert.equal(r.rawHistoricalSessions,0);
 assert.equal(r.plannedWindowPairsExamined,0);
 assert.equal(r.validatedTradingCases,0);
 assert.equal(r.approvedRaasMetrics,0);
});

test("MDGL 2024 NDA original approval and pre-2024 SEC cover shares cannot be forged",()=>{
 const mdgl=cases.find(x=>x.ticker==="MDGL");
 assert.equal(mdgl.application,"NDA 217785");
 assert.equal(mdgl.pdufaTargetDate,"2024-03-14");
 assert.equal(mdgl.phase3ReadoutDate,"2022-12-19");
 assert.equal(mdgl.acceleratedApproval,true);
 assert.equal(mdgl.confirmatoryEvidenceStillRequired,true);
 assert.equal(m.verify(events,shares,earlier,intake).find(x=>x.ticker==="MDGL").reportedCoverShareChange,154779);
 const changed=structuredClone(earlier);
 changed.records.find(x=>x.ticker==="MDGL").sharesOutstanding=19897425;
 assert.throws(()=>m.verify(events,shares,changed,intake),/2024_MDGL_SECURITIES_DISCLOSURE_MISMATCH/);
 const premature=structuredClone(shares);
 premature.records.find(x=>x.ticker==="MDGL").firstConservativeEntryDate="2024-02-28";
 assert.throws(()=>m.verify(events,premature,earlier,intake),/2024_MDGL_SECURITIES_DISCLOSURE_MISMATCH|CAP_SOURCE/);
});

test("GERN RYTELO retains ten-day early FDA action and dated SEC financing gap",()=>{
 const gern=cases.find(x=>x.ticker==="GERN");
 assert.equal(gern.application,"NDA 217779");
 assert.equal(gern.pdufaTargetDate,"2024-06-16");
 assert.equal(gern.targetAnnouncementDate,"2023-08-22");
 assert.equal(gern.phase3ReadoutDate,"2023-01-04");
 assert.equal(gern.actualFDAActionDate,"2024-06-06");
 assert.equal(gern.fdaActionEarlierThanPdufaGoalDays,10);
 const audit=m.verify(events,shares,earlier,intake).find(x=>x.ticker==="GERN");
 assert.equal(audit.reportedCoverShareChange,47073231);
 assert.equal(audit.eligibleForApprovedTrading,false);
 const bad=structuredClone(earlier);
 bad.records.find(x=>x.ticker==="GERN").firstConservativeEntryDate="2024-02-28";
 assert.throws(()=>m.verify(events,shares,bad,intake),/CAP_SOURCE|GERN_SECURITIES_DISCLOSURE/);
});

test("SLNO maintains original 2024 PDUFA and formally extended 2025 goal without lookahead",()=>{
 const slno=cases.find(x=>x.ticker==="SLNO");
 assert.equal(slno.application,"NDA 216665");
 assert.equal(slno.originallyAnnouncedPdufaTargetDate,"2024-12-27");
 assert.equal(slno.originalTargetAnnouncementDate,"2024-08-27");
 assert.equal(slno.targetAnnouncementDate,"2024-11-26");
 assert.equal(slno.fdaGoalExtensionAnnouncedDate,"2024-11-26");
 assert.equal(slno.formalGoalExtensionIndependentlyVerified,true);
 assert.equal(slno.pdufaTargetDate,"2025-03-27");
 assert.equal(slno.phase3ReadoutDate,"2023-09-26");
 assert.deepEqual(slno.nctIds,["NCT03440814","NCT03714373"]);
 assert.equal(slno.actualFDAActionDate,"2025-03-26");
 assert.equal(slno.fdaActionEarlierThanPdufaGoalDays,1);
 const audit=m.verify(events,shares,earlier,intake).find(x=>x.ticker==="SLNO");
 assert.equal(audit.reportedCoverShareChange,2739859);
 assert.equal(audit.eligibleForApprovedTrading,false);
 const forged=structuredClone(earlier);
 forged.records.find(x=>x.ticker==="SLNO").sharesOutstanding=45857291;
 assert.throws(()=>m.verify(events,shares,forged,intake),/SLNO_SECURITIES_DISCLOSURE_MISMATCH/);
 const changed=structuredClone(events);
 changed.records.find(x=>x.ticker==="SLNO").originallyAnnouncedPdufaTargetDate="2025-03-27";
 assert.throws(()=>m.verify(changed,shares,earlier,intake),/ORIGINAL_TARGET_ACTION_IDENTITY_INVALID/);
});

test("LXRX 2024 ZYNQUISTA adverse FDA CRL is not 2019 review or positive approval",()=>{
 const lxrx=cases.find(x=>x.ticker==="LXRX");
 assert.equal(lxrx.application,"NDA 210934");
 assert.equal(lxrx.actualFDAOutcome,"CRL");
 assert.equal(lxrx.targetAnnouncementDate,"2024-07-16");
 assert.equal(lxrx.pdufaTargetDate,"2024-12-20");
 assert.equal(lxrx.actualFDAActionDate,"2024-12-20");
 assert.equal(lxrx.phase3ReadoutDate,"2017-06-09");
 assert.equal(lxrx.previous2019CRLIsSeparateReviewCycle,true);
 assert.equal(lxrx.priorCRLDate,"2019-03-22");
 assert.equal(lxrx.fdaLetterRetrospectivelyPublishedAfterAction,true);
 assert.deepEqual(lxrx.nctIds,["NCT02531035"]);
 const history=m.verify(events,shares,earlier,intake).find(x=>x.ticker==="LXRX");
 assert.equal(history.reportedCoverShareChange,0);
 assert.equal(history.eligibleForApprovedTrading,false);
 const changed=structuredClone(events);
 changed.records.find(x=>x.ticker==="LXRX").actualFDAOutcome="APPROVED";
 assert.throws(()=>m.verify(changed,shares,earlier,intake),/ACTIVE_ORIGINAL_TARGET_ACTION_IDENTITY_INVALID/);
 const forged=structuredClone(shares);
 forged.records.find(x=>x.ticker==="LXRX").sharesOutstanding=361492296;
 assert.throws(()=>m.verify(events,forged,earlier,intake),/LXRX_SECURITIES_DISCLOSURE_MISMATCH/);
});
