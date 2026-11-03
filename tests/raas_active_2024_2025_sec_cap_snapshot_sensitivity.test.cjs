"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const {build,csv}=require("../scripts/raas_active_2024_2025_sec_cap_snapshot_sensitivity.cjs");
const ROOT="https://www.sec.gov/Archives/edgar/data/1000000/";
const CASES=[
 {caseId:"A|2024",ticker:"AAA",year:2024,entry:"2024-02-05",
  old:100000000,new:120000000,raw:5,usingEarlier:true},
 {caseId:"B|2024",ticker:"BBB",year:2024,entry:"2024-02-05",
  old:1900000000,new:2100000000,raw:5,usingEarlier:true},
 {caseId:"C|2025",ticker:"CCC",year:2025,entry:"2025-05-05",
  old:60000000,new:70000000,raw:10,usingEarlier:false},
];
const date=(y,m,d)=>[y,m,d].join("-");
function fixture(){
 const earlier={scope:"RAAS_MANUALLY_LOCATED_PRE_ENTRY_SEC_SHARES_RESEARCH",records:[]};
 const later={scope:"RAAS_MANUALLY_LOCATED_SEC_HISTORIC_COMMON_SHARE_RESEARCH",records:[]};
 const research={scope:"RAAS_ACTIVE_2024_2025_ORIGINAL_SOURCE_LEADS_AND_ALPACA_CAP_RESEARCH",
  status:"2024_2025_SOURCE_LEADS_UNVALIDATED_PRICE_RESEARCH",
  allResearchOnly:true,validatedTradingCases:0,approvedRaasMetrics:0,
  fullYearCensusesAudited:0,selectedOptimalWindow:null,
  sourceLeadCount:CASES.length,sourceLeads:[],caseResearch:[],priceDataRawAndAdjusted:[]};
 const audit={scope:"RAAS_ACTIVE_2024_2025_T79_TO_T14_RESEARCH_AUDIT",
  status:"UNVALIDATED_PROVISIONAL_RETURN_DIAGNOSTIC_ONLY",
  sourceCaseCount:CASES.length,rows:[],
  window:{entryLeadCalendarDays:79,exitLeadCalendarDays:14},
  independentlyValidatedTradingCases:0,approvedRaasMetrics:0,
  completedFDAFullCensusYears:0,approvedOptimalWindow:null};
 for(const c of CASES){
  const y=String(c.year),oldUrl=ROOT+c.ticker+"/old.htm",
   newUrl=ROOT+c.ticker+"/new.htm",oldDate=y+"-01-10",
   oldFiled=y+"-01-11",oldSafe=y+"-01-12",
   laterDate=y+"-03-10",laterFiled=y+"-03-11",
   laterSafe=y+"-03-12",source=c.usingEarlier?oldUrl:newUrl;
  const core={caseId:c.caseId,ticker:c.ticker,venue:"NASDAQ",
   cik:"0001000000",shareClass:"NASDAQ US common stock",
   securityCurrency:"USD",rawCloseCurrency:"USD",
   status:"COVER_SHARE_RESEARCH_ONLY"};
  earlier.records.push({...core,sourceUrl:oldUrl,sharesOutstanding:c.old,
   sharesMeasurementDate:oldDate,filedDate:oldFiled,firstConservativeEntryDate:oldSafe});
  later.records.push({...core,sourceUrl:newUrl,sharesOutstanding:c.new,
   sharesMeasurementDate:laterDate,filedDate:laterFiled,firstConservativeEntryDate:laterSafe});
  research.sourceLeads.push({caseId:c.caseId,ticker:c.ticker,
   earlierShares:c.old,laterShares:c.new,
   earlierSECSource:oldUrl,laterSECSource:newUrl,
   reportedCoverShareChange:c.new-c.old});
  research.caseResearch.push({caseId:c.caseId,ticker:c.ticker,
   namedWindow79to14:{validated:false,studyEligible:false,
    actualEntryDate:c.entry,actualExitDate:y+"-06-05",
    supplementalShareFactUsed:c.usingEarlier,
    historicalSharesSourceUsed:source,
    shareFactFirstSafeDate:c.usingEarlier?oldSafe:laterSafe,
    provisionalEntryCapMillions:c.raw*(c.usingEarlier?c.old:c.new)/1000000}});
  research.priceDataRawAndAdjusted.push({caseId:c.caseId,ticker:c.ticker,
   source:"ALPACA_SIP_RAW_CLOSE_X_SEC_COVER_SHARES",
   priceReturnSource:"ALPACA_SIP_ADJUSTMENT_ALL_SEPARATE",
   eventTradeCasesValidated:0,approvedRaasRatings:0,
   observations:[{session:c.entry,rawClose:c.raw}]});
  audit.rows.push({caseId:c.caseId,ticker:c.ticker,year:c.year,
   actualFdaOutcomeRetrospective:c.ticker==="BBB"?"CRL":"APPROVED",
   entryDate:c.entry,exitDate:y+"-06-05",actualFdaActionDate:y+"-10-01",
   goalFirstPublicDate:y+"-01-01",
   validatedTradingCase:false,independentlyVerifiedPrice:false,
   approvedRaasMetric:false,completeFDAEventCensus:false,
   status:"UNVALIDATED_ALPACA_PRICE_RESEARCH",
   entryCapResearchMillions:c.raw*(c.usingEarlier?c.old:c.new)/1000000,
   earlierSECShareSnapshotUsed:c.usingEarlier,secSharesSource:source,
   grossReturnPct:5});
 }
 return {audit,research,earlier,later};
}
test("Earlier and later SEC cover snapshots are compared but later unpublished count is never selected at entry",()=>{
 const out=build(fixture());
 assert.equal(out.sourceCaseCount,3);
 assert.equal(out.comparedCases,3);
 assert.equal(out.casesWhereLaterCoverWasNotPublicAtEntry,2);
 assert.equal(out.casesWhoseProvisionalCapBandDiffersBetweenSnapshots,1);
 assert.equal(out.validatedEntryDateCapCases,0);
 assert.equal(out.independentlyValidatedTrades,0);
 assert.equal(out.approvedRaasMetrics,0);
 assert.equal(out.approvedOptimalWindow,null);
 const a=out.rows.find(r=>r.ticker==="AAA");
 assert.equal(a.capUsingEarlierCoverMillions,500);
 assert.equal(a.capUsingLaterCoverMillions,600);
 assert.equal(a.laterSourceAvailableAtEntry,false);
 assert.equal(a.sourceUsedAtEntry,"EARLIER_COVER");
 const b=out.rows.find(r=>r.ticker==="BBB");
 assert.equal(b.capUsingEarlierCoverMillions,9500);
 assert.equal(b.capUsingLaterCoverMillions,10500);
 assert.equal(b.wouldSnapshotChoiceChangeProvisional300mTo10bBand,true);
 const c=out.rows.find(r=>r.ticker==="CCC");
 assert.equal(c.laterSourceAvailableAtEntry,true);
 assert.equal(c.sourceUsedAtEntry,"LATER_COVER");
 assert.equal(c.originalPointInTimeCapResearchMillions,700);
 assert.equal(c.capUsingEarlierCoverMillions,600);
 assert.equal(c.asOfCoverMeasurementAgeCalendarDays,56);
 assert.ok(out.warnings.some(x=>x.includes("NOT bounds")));
});
test("Reject future-unpublished later cover used as if known on entry date",()=>{
 const x=fixture();const a=x.audit.rows[0],c=x.research.caseResearch[0];
 a.earlierSECShareSnapshotUsed=false;
 a.secSharesSource=x.later.records[0].sourceUrl;
 a.entryCapResearchMillions=600;
 c.namedWindow79to14.supplementalShareFactUsed=false;
 c.namedWindow79to14.historicalSharesSourceUsed=x.later.records[0].sourceUrl;
 c.namedWindow79to14.shareFactFirstSafeDate="2024-03-12";
 c.namedWindow79to14.provisionalEntryCapMillions=600;
 assert.throws(()=>build(x),/POINT_IN_TIME_SHARE_SELECTION_INVALID/);
});
test("Tampered share count, source URL and RAW entry close fail closed",()=>{
 const t=fixture();t.later.records[0].sharesOutstanding=121000000;
 assert.throws(()=>build(t),/IDENTITY_OR_SHARES_INVALID/);
 const u=fixture();u.audit.rows[0].entryCapResearchMillions=501;
 assert.throws(()=>build(u),/RAW_CAP_PROVENANCE_MISMATCH/);
 const v=fixture();v.research.priceDataRawAndAdjusted[0].observations.push(
  {session:"2024-02-05",rawClose:5});
 assert.throws(()=>build(v),/RAW_BAR_MISSING_OR_AMBIGUOUS/);
});
test("No fictitious cap or return on a blocked window",()=>{
 const x=fixture(),r=x.audit.rows[0],w=x.research.caseResearch[0].namedWindow79to14;
 r.status="BLOCKED_RESEARCH_WINDOW";
 r.entryCapResearchMillions=null;r.grossReturnPct=null;
 w.provisionalEntryCapMillions=null;
 const out=build(x);
 assert.equal(out.comparedCases,2);
 assert.equal(out.blockedCases,1);
 assert.equal(out.rows[0].rawEntryClose,null);
 assert.equal(out.rows[0].marketCapEligibleForHistoricalTrading,false);
});
test("CSV numeric negative shifts and security against spreadsheet formulas",()=>{
 const report=build(fixture());const content=csv(report);
 assert.equal(content.trim().split("\n").length,4);
 const header=content.trim().split("\n")[0].split(",");
 const b=content.trim().split("\n").find(l=>l.startsWith('"BBB",')).split(",");
 assert.equal(b[header.indexOf("earlierCoverShares")],"1900000000");
 assert.equal(b[header.indexOf("capUsingLaterCoverMillions")],"10500");
 report.rows[0].ticker='=HYPERLINK("https://malicious.example","x")';
 assert.ok(csv(report).includes("'=HYPERLINK"));
 report.rows[0].rawEntryClose="=2+2";
 assert.throws(()=>csv(report),/NON_NUMERIC_EXPORT/);
});
