#!/usr/bin/env node
"use strict";
/**
 * Dated SEC cover share-snapshot sensitivity for actual T-79 -> T-14
 * historical RAW Alpaca entry closes. ALL results are unvalidated.
 *
 * The later SEC cover may not have been public at the entry session.
 * It is used ONLY as a retrospective stress test, never to determine
 * original entry eligibility, pricing, selection, or RAAS ratings.
 */
const fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"..");
const AUDIT_SCOPE="RAAS_ACTIVE_2024_2025_T79_TO_T14_RESEARCH_AUDIT";
const RESEARCH_SCOPE="RAAS_ACTIVE_2024_2025_ORIGINAL_SOURCE_LEADS_AND_ALPACA_CAP_RESEARCH";
const OUT_SCOPE="RAAS_ACTIVE_2024_2025_SEC_COVER_CAP_SNAPSHOT_SENSITIVITY_ONLY";
const date=s=>typeof s==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 !Number.isNaN(Date.parse(s+"T00:00:00Z"))&&
 new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const round=n=>Math.round((n+Number.EPSILON)*100)/100;
const days=(end,start)=>Math.round((Date.parse(end+"T00:00:00Z")-
 Date.parse(start+"T00:00:00Z"))/86400000);
const inCap=v=>v>=300&&v<=10000;
const url=s=>typeof s==="string"&&/^https:\/\/[^\s/]+\.[^\s/]+/.test(s);
const getMap=(a,label)=>{
 if(!Array.isArray(a))throw Error("RAAS_SEC_SENSITIVITY_SOURCE_ARRAY_INVALID_"+label);
 const m=new Map();
 for(const x of a){
  if(!x||typeof x.caseId!=="string"||!x.caseId||m.has(x.caseId))
   throw Error("RAAS_SEC_SENSITIVITY_DUPLICATE_OR_UNMATCHED_"+label);
  m.set(x.caseId,x);
 }
 return m;
};
function build({audit,research,earlier,later}){
 if(audit?.scope!==AUDIT_SCOPE||
  audit.status!=="UNVALIDATED_PROVISIONAL_RETURN_DIAGNOSTIC_ONLY"||
  audit.independentlyValidatedTradingCases!==0||audit.approvedRaasMetrics!==0||
  audit.completedFDAFullCensusYears!==0||audit.approvedOptimalWindow!==null||
  audit.window?.entryLeadCalendarDays!==79||audit.window?.exitLeadCalendarDays!==14||
  research?.scope!==RESEARCH_SCOPE||
  research.status!=="2024_2025_SOURCE_LEADS_UNVALIDATED_PRICE_RESEARCH"||
  research.allResearchOnly!==true||research.validatedTradingCases!==0||
  research.approvedRaasMetrics!==0||research.fullYearCensusesAudited!==0||
  research.selectedOptimalWindow!==null||
  earlier?.scope!=="RAAS_MANUALLY_LOCATED_PRE_ENTRY_SEC_SHARES_RESEARCH"||
  later?.scope!=="RAAS_MANUALLY_LOCATED_SEC_HISTORIC_COMMON_SHARE_RESEARCH"||
  !Array.isArray(audit.rows)||audit.rows.length<1||
  audit.rows.length!==audit.sourceCaseCount||
  audit.sourceCaseCount!==research.sourceLeadCount)
  throw Error("RAAS_SEC_SENSITIVITY_UNTRUSTED_SOURCE");
 const previous=getMap(earlier.records,"EARLIER"),latest=getMap(later.records,"LATER");
 const byRaw=getMap(research.priceDataRawAndAdjusted,"RAW_PRICE");
 const byLead=getMap(research.sourceLeads,"ORIGINAL_LEAD");
 const byResearch=getMap(research.caseResearch,"CASE");
 if([previous,latest,byRaw,byLead,byResearch].some(m=>m.size!==audit.rows.length))
  throw Error("RAAS_SEC_SENSITIVITY_MISSING_CASE");
 const visited=new Set(),rows=[];
 for(const r of audit.rows){
  const p=previous.get(r?.caseId),q=latest.get(r?.caseId),
   raw=byRaw.get(r?.caseId),lead=byLead.get(r?.caseId),
   c=byResearch.get(r?.caseId);
  if(!p||!q||!raw||!lead||!c||visited.has(r.caseId)||
   ![2024,2025].includes(r.year)||!/^[A-Z][A-Z0-9.-]{0,11}$/.test(r.ticker)||
   [p,q,raw,lead,c].some(x=>x.ticker!==r.ticker)||c.caseId!==r.caseId||
   r.validatedTradingCase!==false||r.independentlyVerifiedPrice!==false||
   r.approvedRaasMetric!==false||r.completeFDAEventCensus!==false||
   !["APPROVED","CRL"].includes(r.actualFdaOutcomeRetrospective)||
   !["UNVALIDATED_ALPACA_PRICE_RESEARCH","BLOCKED_RESEARCH_WINDOW"].includes(r.status)||
   p.status!=="COVER_SHARE_RESEARCH_ONLY"||q.status!=="COVER_SHARE_RESEARCH_ONLY"||
   p.cik!==q.cik||p.shareClass!==q.shareClass||
   p.securityCurrency!=="USD"||q.securityCurrency!=="USD"||
   p.rawCloseCurrency!=="USD"||q.rawCloseCurrency!=="USD"||
   p.venue!=="NASDAQ"||q.venue!=="NASDAQ"||
   !date(p.sharesMeasurementDate)||!date(q.sharesMeasurementDate)||
   !date(p.filedDate)||!date(q.filedDate)||
   !date(p.firstConservativeEntryDate)||!date(q.firstConservativeEntryDate)||
   !(p.sharesMeasurementDate<=p.filedDate&&p.filedDate<p.firstConservativeEntryDate)||
   !(q.sharesMeasurementDate<=q.filedDate&&q.filedDate<q.firstConservativeEntryDate)||
   !(p.sharesMeasurementDate<q.sharesMeasurementDate&&p.filedDate<q.filedDate&&
     p.firstConservativeEntryDate<q.firstConservativeEntryDate)||
   !url(p.sourceUrl)||!url(q.sourceUrl)||p.sourceUrl===q.sourceUrl||
   !Number.isSafeInteger(p.sharesOutstanding)||p.sharesOutstanding<=0||
   !Number.isSafeInteger(q.sharesOutstanding)||q.sharesOutstanding<=0||
   lead.earlierShares!==p.sharesOutstanding||lead.laterShares!==q.sharesOutstanding||
   lead.earlierSECSource!==p.sourceUrl||lead.laterSECSource!==q.sourceUrl||
   lead.reportedCoverShareChange!==q.sharesOutstanding-p.sharesOutstanding||
   !Array.isArray(raw.observations)||raw.source!=="ALPACA_SIP_RAW_CLOSE_X_SEC_COVER_SHARES"||
   raw.priceReturnSource!=="ALPACA_SIP_ADJUSTMENT_ALL_SEPARATE"||
   raw.eventTradeCasesValidated!==0||raw.approvedRaasRatings!==0||
   c.namedWindow79to14?.validated!==false||
   c.namedWindow79to14.studyEligible!==false)
   throw Error("RAAS_SEC_SENSITIVITY_IDENTITY_OR_SHARES_INVALID");
  visited.add(r.caseId);
  const shared={
   caseId:r.caseId,ticker:r.ticker,year:r.year,
   actualFDAOutcomeRetrospective:r.actualFdaOutcomeRetrospective,
   entryDate:r.entryDate??null,exitDate:r.exitDate??null,
   earlierSECUrl:p.sourceUrl,laterSECUrl:q.sourceUrl,
   earlierCoverShares:p.sharesOutstanding,laterCoverShares:q.sharesOutstanding,
   publishedCoverShareCountChange:q.sharesOutstanding-p.sharesOutstanding,
   publishedCoverShareChangePct:round(100*(q.sharesOutstanding/p.sharesOutstanding-1)),
   earlierSharesMeasuredAt:p.sharesMeasurementDate,
   earlierSharesFirstUsableAt:p.firstConservativeEntryDate,
   laterSharesMeasuredAt:q.sharesMeasurementDate,
   laterSharesFirstUsableAt:q.firstConservativeEntryDate,
   shareContinuityIndependentlyVerified:false,
   splitAndCorporateActionAuditCompleted:false,
   independentVendorPriceAuditCompleted:false,
   marketCapEligibleForHistoricalTrading:false,
   validatedTradingCase:false,approvedRaasMetric:false,
  };
  if(r.status==="BLOCKED_RESEARCH_WINDOW"){
   if(r.grossReturnPct!==null||r.entryCapResearchMillions!==null)
    throw Error("RAAS_SEC_SENSITIVITY_BLOCKED_CANNOT_HAVE_RETURN");
   rows.push({...shared,status:"BLOCKED_ORIGINAL_WINDOW",
    rawEntryClose:null,capUsingEarlierCoverMillions:null,capUsingLaterCoverMillions:null,
    absoluteCapSnapshotSpreadMillions:null,capSnapshotPercentDifference:null,
    wouldSnapshotChoiceChangeProvisional300mTo10bBand:null,
    laterSourceAvailableAtEntry:null,sourceUsedAtEntry:null,
    asOfSharesFirstUsableAt:null,asOfCoverMeasurementAgeCalendarDays:null,
    retrospectiveOnly:true});
   continue;
  }
  const entry=r.entryDate,exit=r.exitDate,entrySource=r.secSharesSource;
  if(!date(entry)||!date(exit)||entry>=exit||exit>=r.actualFdaActionDate||
   entry<r.goalFirstPublicDate||
   !Number.isFinite(r.entryCapResearchMillions)||
   r.entryCapResearchMillions<300||r.entryCapResearchMillions>10000||
   (r.earlierSECShareSnapshotUsed!==true&&r.earlierSECShareSnapshotUsed!==false))
   throw Error("RAAS_SEC_SENSITIVITY_BAD_ORIGINAL_WINDOW");
  const selected=r.earlierSECShareSnapshotUsed?p:q;
  const x=c.namedWindow79to14;
  if(entrySource!==selected.sourceUrl||
   x.actualEntryDate!==entry||x.actualExitDate!==exit||
   x.historicalSharesSourceUsed!==entrySource||
   x.supplementalShareFactUsed!==r.earlierSECShareSnapshotUsed||
   x.shareFactFirstSafeDate!==selected.firstConservativeEntryDate||
   entry<selected.firstConservativeEntryDate||
   (q.firstConservativeEntryDate<=entry&&selected!==q)||
   (p.firstConservativeEntryDate>entry))
   throw Error("RAAS_SEC_SENSITIVITY_POINT_IN_TIME_SHARE_SELECTION_INVALID");
  const bars=raw.observations.filter(o=>o.session===entry);
  if(bars.length!==1||typeof bars[0].rawClose!=="number"||
   !Number.isFinite(bars[0].rawClose)||bars[0].rawClose<=0)
   throw Error("RAAS_SEC_SENSITIVITY_RAW_BAR_MISSING_OR_AMBIGUOUS");
  const price=bars[0].rawClose;
  const knownCap=round(price*selected.sharesOutstanding/1000000);
  if(Math.abs(knownCap-r.entryCapResearchMillions)>0.011||
   Math.abs(knownCap-x.provisionalEntryCapMillions)>0.011)
   throw Error("RAAS_SEC_SENSITIVITY_RAW_CAP_PROVENANCE_MISMATCH");
  const first=round(price*p.sharesOutstanding/1000000),
   second=round(price*q.sharesOutstanding/1000000);
  const laterAvailable=q.firstConservativeEntryDate<=entry;
  rows.push({...shared,status:"RETROSPECTIVE_SHARE_SNAPSHOT_CAP_SENSITIVITY_ONLY",
   rawEntryClose:price,asOfSharesFirstUsableAt:selected.firstConservativeEntryDate,
   asOfCoverMeasurementAgeCalendarDays:days(entry,selected.sharesMeasurementDate),
   sourceUsedAtEntry:r.earlierSECShareSnapshotUsed?"EARLIER_COVER":"LATER_COVER",
   laterSourceAvailableAtEntry:laterAvailable,
   capUsingEarlierCoverMillions:first,capUsingLaterCoverMillions:second,
   originalPointInTimeCapResearchMillions:knownCap,
   absoluteCapSnapshotSpreadMillions:round(Math.abs(second-first)),
   capSnapshotPercentDifference:round(100*Math.abs(q.sharesOutstanding/p.sharesOutstanding-1)),
   wouldSnapshotChoiceChangeProvisional300mTo10bBand:inCap(first)!==inCap(second),
   // Even if both cover counts match, issuances may have occurred between dates.
   retrospectiveOnly:true,
  });
 }
 const compared=rows.filter(r=>r.status==="RETROSPECTIVE_SHARE_SNAPSHOT_CAP_SENSITIVITY_ONLY");
 const sorted=compared.slice().sort((a,b)=>b.absoluteCapSnapshotSpreadMillions-
  a.absoluteCapSnapshotSpreadMillions||a.ticker.localeCompare(b.ticker));
 return {schemaVersion:1,scope:OUT,status:"PROVISIONAL_SEC_COVER_SNAPSHOT_SENSITIVITY_NOT_MARKET_CAP_VALIDATION",
  sourceCaseCount:rows.length,comparedCases:compared.length,
  blockedCases:rows.length-compared.length,
  casesWhereLaterCoverWasNotPublicAtEntry:compared.filter(x=>!x.laterSourceAvailableAtEntry).length,
  casesWhoseProvisionalCapBandDiffersBetweenSnapshots:compared.filter(
   x=>x.wouldSnapshotChoiceChangeProvisional300mTo10bBand).length,
  maximumHistoricalCoverCountDifferencePct:sorted.length?
   Math.max(...compared.map(x=>x.capSnapshotPercentDifference)):null,
  largestAbsoluteCapSnapshotSpreadMillions:sorted[0]?.absoluteCapSnapshotSpreadMillions??null,
  mostCapSensitiveTicker:sorted[0]?.ticker??null,
  rows,
  validatedEntryDateCapCases:0,independentlyValidatedTrades:0,
  fullFDAYearCensusesAudited:0,approvedRaasMetrics:0,
  approvedOptimalWindow:null,
  warnings:[
   "Two SEC cover snapshots are observations on separate disclosed dates, NOT bounds on the real share count throughout the intervening period.",
   "A later filing unavailable at trade entry is used ONLY for retrospective sensitivity; no lookahead is allowed in cap selection.",
   "Both SEC share snapshots omit independent daily issuance, redemption, warrants, ADR and stock split reconciliation.",
   "An apparent $300M-$10B eligibility band match is NOT a verified historical market-cap pass.",
   "Returns are still from an outcome-selected incomplete FDA sample with no independent price vendor audit or completed target-year census."
  ]};
}
function csv(report){
 if(report?.scope!==OUT)throw Error("RAAS_SEC_SENSITIVITY_CSV_SCOPE_INVALID");
 const cols=["ticker","year","entryDate","sourceUsedAtEntry","laterSourceAvailableAtEntry",
  "earlierCoverShares","laterCoverShares","publishedCoverShareChangePct",
  "rawEntryClose","capUsingEarlierCoverMillions","capUsingLaterCoverMillions",
  "absoluteCapSnapshotSpreadMillions","capSnapshotPercentDifference",
  "wouldSnapshotChoiceChangeProvisional300mTo10bBand","asOfCoverMeasurementAgeCalendarDays",
  "earlierSECUrl","laterSECUrl","status"];
 const numeric=new Set(["year","earlierCoverShares","laterCoverShares",
  "publishedCoverShareChangePct","rawEntryClose","capUsingEarlierCoverMillions",
  "capUsingLaterCoverMillions","absoluteCapSnapshotSpreadMillions",
  "capSnapshotPercentDifference","asOfCoverMeasurementAgeCalendarDays"]);
 const cell=(key,v)=>{
  if(numeric.has(key)){if(v===null||v===undefined)return "";
   if(typeof v!=="number"||!Number.isFinite(v))
    throw Error("RAAS_SEC_SENSITIVITY_NON_NUMERIC_EXPORT");
   return String(v);}
  const text=String(v??"");
  const safe=/^[\s\u0000-\u001f]*[=+\-@]/u.test(text)?"'"+text:text;
  return '"'+safe.replaceAll('"','""')+'"';
 };
 return cols.join(",")+"\n"+report.rows.map(r=>
  cols.map(k=>cell(k,r[k])).join(",")).join("\n")+"\n";
}
function main(){
 try{
  const load=(env,f)=>JSON.parse(fs.readFileSync(process.env[env]||
   path.join(root,f),"utf8"));
  const report=build({
   audit:load("RAAS_T79_14_AUDIT_JSON","raas-2024-2025-t79-14-audit.json"),
   research:load("RAAS_ACTIVE_SOURCE_RESEARCH_OUTPUT","raas-2024-2025-original-source-research.json"),
   earlier:load("RAAS_2024_2025_EARLIER_SHARE_JSON",
    "new-platform/frontend/data/raas-active-2024-2025-preentry-sec-share-leads.json"),
   later:load("RAAS_2024_2025_LATER_SHARE_JSON",
    "new-platform/frontend/data/raas-active-2024-2025-sec-cover-share-leads.json"),
  });
  const out=process.env.RAAS_SEC_SENSITIVITY_JSON||
   path.join(root,"raas-2024-2025-sec-cap-snapshot-sensitivity.json");
  const csvPath=process.env.RAAS_SEC_SENSITIVITY_CSV||
   path.join(root,"raas-2024-2025-sec-cap-snapshot-sensitivity.csv");
  for(const p of [out,csvPath])fs.mkdirSync(path.dirname(p),{recursive:true});
  fs.writeFileSync(out,JSON.stringify(report,null,2)+"\n");
  fs.writeFileSync(csvPath,csv(report));
  const summary={status:report.status,cases:report.comparedCases,
   laterCoverUnpublishedAtEntry:report.casesWhereLaterCoverWasNotPublicAtEntry,
   largestCapSnapshotSpreadMillions:report.largestAbsoluteCapSnapshotSpreadMillions,
   mostSensitiveTicker:report.mostCapSensitiveTicker,
   capBandDisagreementCases:report.casesWhoseProvisionalCapBandDiffersBetweenSnapshots,
   validatedCapCases:0,approvedRaasMetrics:0};
  console.log(JSON.stringify(summary));
  if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
   "### SEC share-cover snapshot sensitivity (RESEARCH ONLY)\n\n"+
   JSON.stringify(summary,null,2)+"\n\nNo validated historical cap or RAAS grade.\n");
 }catch(e){console.error("RAAS_SEC_SENSITIVITY_FATAL_"+
  String(e.message||e).replace(/[^A-Z0-9_]/g,"_"));process.exitCode=1;}
}
if(require.main===module)main();
module.exports={build,csv};
