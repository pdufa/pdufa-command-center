"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const m=require("../scripts/raas_active_2024_2025_window79_audit.cjs");
const root=path.resolve(__dirname,"..");
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const events=read("new-platform/frontend/data/raas-active-2024-2025-primary-source-leads.json");
const earlier=read("new-platform/frontend/data/raas-active-2024-2025-preentry-sec-share-leads.json");
const later=read("new-platform/frontend/data/raas-active-2024-2025-sec-cover-share-leads.json");
const targets={
 ARQT:{entry:"2024-04-19",exit:"2024-06-21",gross:-6.70,cap:881,old:true},
 AXSM:{entry:"2024-11-13",exit:"2025-01-17",gross:-6.03,cap:4741.07,old:false},
 MDGL:{entry:"2023-12-26",exit:"2024-02-29",gross:-0.05,cap:4665.58,old:true},
 GERN:{entry:"2024-04-01",exit:"2024-05-31",gross:11.99,cap:1731.01,old:true},
 SLNO:{entry:"2025-01-07",exit:"2025-03-13",gross:6.08,cap:1992.89,old:true}
};
function fixture(){
 const sourceLeads=[],caseResearch=[],priceDataRawAndAdjusted=[];
 for(const event of events.records){
  const t=targets[event.ticker],old=earlier.records.find(x=>x.caseId===event.caseId);
  const now=later.records.find(x=>x.caseId===event.caseId);
  const shares=t.old?old.sharesOutstanding:now.sharesOutstanding;
  const source=t.old?old.sourceUrl:now.sourceUrl;
  const raw=t.cap*1e6/shares;
  sourceLeads.push({caseId:event.caseId,ticker:event.ticker,pdufaTargetDate:event.pdufaTargetDate,
   actualFDAActionDate:event.actualFDAActionDate,
   earlierShares:old.sharesOutstanding,laterShares:now.sharesOutstanding,
   earlierSECSource:old.sourceUrl,laterSECSource:now.sourceUrl,eligibleForApprovedTrading:false});
  caseResearch.push({caseId:event.caseId,ticker:event.ticker,year:+event.pdufaTargetDate.slice(0,4),
   namedWindow79to14:{entryLeadDays:79,exitLeadDays:14,actualEntryDate:t.entry,
    actualExitDate:t.exit,historicalSharesSourceUsed:source,
    shareFactFirstSafeDate:t.old?old.firstConservativeEntryDate:now.firstConservativeEntryDate,
    supplementalShareFactUsed:t.old,
    provisionalEntryCapMillions:t.cap,
    provisionalGrossReturnPct:t.gross,provisionalNetReturnPct:t.gross-1,
    validated:false,studyEligible:false,status:"UNVALIDATED_ADDITIONAL_PREENTRY_WINDOW_RESEARCH",
    reason:"NEEDS_SHARE_CONTINUITY_SPLIT_AND_INDEPENDENT_PRICE_AUDIT"}});
  priceDataRawAndAdjusted.push({caseId:event.caseId,ticker:event.ticker,
   pdufaTargetDate:event.pdufaTargetDate,actualFDAActionDate:event.actualFDAActionDate,
   eventTradeCasesValidated:0,approvedRaasRatings:0,
   shareFactSourceUrl:now.sourceUrl,
   source:"ALPACA_SIP_RAW_CLOSE_X_SEC_COVER_SHARES",
   priceReturnSource:"ALPACA_SIP_ADJUSTMENT_ALL_SEPARATE",
   observations:[
    {session:t.entry,rawClose:raw,adjustedClose:100},
    {session:t.exit,rawClose:raw,adjustedClose:100*(1+t.gross/100)}
   ]});
 }
 return {scope:"RAAS_ACTIVE_2024_2025_ORIGINAL_SOURCE_LEADS_AND_ALPACA_CAP_RESEARCH",
  status:"2024_2025_SOURCE_LEADS_UNVALIDATED_PRICE_RESEARCH",
  allResearchOnly:true,validatedTradingCases:0,approvedRaasMetrics:0,
  fullYearCensusesAudited:0,selectedOptimalWindow:null,
  studyStartDate:"2024-01-01",studyEndDate:"2025-12-31",
  sourceLeadCount:events.records.length,sourceLeads,caseResearch,priceDataRawAndAdjusted};
}
test("Five independent research leads yield source-gated T79/14 estimates, not trading approvals",()=>{
 const x=m.build(fixture(),events);
 assert.equal(x.sourceCaseCount,5);
 assert.equal(x.allProvisional.cases,5);
 assert.equal(x.allProvisional.provisionalMeanGrossPct,1.06);
 assert.equal(x.allProvisional.provisionalMedianGrossPct,-0.05);
 assert.equal(x.allProvisional.hypotheticalMeanNetPct,0.06);
 assert.equal(x.byYear[2024].cases,3);
 assert.equal(x.byYear[2025].cases,2);
 assert.equal(x.byYear[2025].provisionalMeanGrossPct,0.03);
 assert.equal(x.independentlyValidatedTradingCases,0);
 assert.equal(x.approvedOptimalWindow,null);
 assert.equal(x.approvedRaasMetrics,0);
 assert.ok(x.rows.every(r=>!r.independentlyVerifiedPrice&&!r.validatedTradingCase));
});
test("Soleno updated PDUFA announcement must precede the entry: never use future knowledge",()=>{
 const x=fixture(),lead=x.caseResearch.find(r=>r.ticker==="SLNO").namedWindow79to14;
 lead.actualEntryDate="2024-11-25";
 assert.throws(()=>m.build(x,events),/POINT_IN_TIME_OR_CAP_INVALID/);
 const y=structuredClone(events),slno=y.records.find(r=>r.ticker==="SLNO");
 slno.fdaGoalExtensionAnnouncedDate="2025-02-11";
 assert.throws(()=>m.build(fixture(),y),/GOAL_EXTENSION_CHRONOLOGY_INVALID/);
});
test("Missing vendor price, wrong SEC price-shares multiplication, early FDA action and false grading fail closed",()=>{
 const p=fixture();p.priceDataRawAndAdjusted[0].observations[0].adjustedClose=22;
 assert.throws(()=>m.build(p,events),/PRICE_ARITHMETIC_OR_PROVENANCE_INVALID/);
 const q=fixture();q.caseResearch[0].namedWindow79to14.provisionalEntryCapMillions=9999;
 assert.throws(()=>m.build(q,events),/PRICE_ARITHMETIC_OR_PROVENANCE_INVALID/);
 const r=fixture();r.caseResearch.find(x=>x.ticker==="GERN").namedWindow79to14.actualExitDate="2024-06-06";
 assert.throws(()=>m.build(r,events),/POINT_IN_TIME_OR_CAP_INVALID/);
 const s=fixture();s.approvedRaasMetrics=1;
 assert.throws(()=>m.build(s,events),/SOURCE_RESEARCH_INVALID/);
});
test("A missing T79/14 price window is represented as blocked, never fabricated gain",()=>{
 const x=fixture(),row=x.caseResearch[0].namedWindow79to14;
 row.status=undefined;row.reason="PRICE_VENDOR_MISSING";
 row.provisionalGrossReturnPct=null;row.provisionalNetReturnPct=null;
 const out=m.build(x,events);
 assert.equal(out.blockedCases,1);
 assert.equal(out.rows.find(x=>x.ticker==="ARQT").grossReturnPct,null);
 assert.equal(out.allProvisional.cases,4);
});
test("CSV output quotes source text and escapes formulas before spreadsheet opening",()=>{
 const result=m.build(fixture(),events);result.rows[0].ticker='=HYPERLINK("https://evil.test","x")';
 const csv=m.csv(result);
 assert.ok(csv.includes("'=HYPERLINK"));
 assert.ok(!csv.includes('"=HYPERLINK'));
 assert.equal(csv.trim().split("\n").length,6);
});
