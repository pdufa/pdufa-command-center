#!/usr/bin/env node
"use strict";

// Permanent retirement: no historical artifact writer may execute as a command.
if (require.main === module) { process.stderr.write("RAAS_PERMANENTLY_RETIRED: this archived command cannot run or modify historical records.\n"); process.exit(78); }

/**
 * Read-only, source-gated summary of T-79 -> T-14 research arithmetic from
 * the active 2024-2025 ALPACA RAW + adjusted price artifact.
 *
 * This is NOT a validated backtest. Historical CAP share continuity, corporate
 * actions, independent vendor parity, and full FDA outcome census are pending.
 * Never issue an optimized entry window or a numeric RAAS grade.
 */
const fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"..");
const sourcesPath="new-platform/frontend/data/raas-active-2024-2025-primary-source-leads.json";
const validDate=x=>typeof x==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&
 !Number.isNaN(Date.parse(x+"T00:00:00Z"))&&
 new Date(x+"T00:00:00Z").toISOString().slice(0,10)===x;
const validUrl=x=>typeof x==="string"&&/^https:\/\/[^/\s]+\.[^/\s]+/i.test(x);
const round=n=>Math.round((n+Number.EPSILON)*100)/100;
const days=(s,n)=>new Date(Date.parse(s+"T00:00:00Z")+n*86400000).toISOString().slice(0,10);
const median=a=>{const x=[...a].sort((u,v)=>u-v);return x.length%2?x[(x.length-1)/2]:(x[x.length/2-1]+x[x.length/2])/2;};
function numeric(x){return Number.isFinite(x)&&typeof x==="number";}
function build(research,sourceEvents){
 if(!research||research.scope!=="RAAS_ACTIVE_2024_2025_ORIGINAL_SOURCE_LEADS_AND_ALPACA_CAP_RESEARCH"||
  research.status!=="2024_2025_SOURCE_LEADS_UNVALIDATED_PRICE_RESEARCH"||
  research.allResearchOnly!==true||research.validatedTradingCases!==0||
  research.approvedRaasMetrics!==0||research.fullYearCensusesAudited!==0||
  research.selectedOptimalWindow!==null||
  research.studyStartDate!=="2024-01-01"||research.studyEndDate!=="2025-12-31"||
  !sourceEvents||!Array.isArray(sourceEvents.records)||
  !Array.isArray(research.caseResearch)||!Array.isArray(research.sourceLeads)||
  !Array.isArray(research.priceDataRawAndAdjusted)||
  research.sourceLeadCount!==sourceEvents.records.length||
  research.caseResearch.length!==sourceEvents.records.length||
  research.priceDataRawAndAdjusted.length!==sourceEvents.records.length||
  research.sourceLeads.length!==sourceEvents.records.length)
  throw Error("RAAS_T79_14_SOURCE_RESEARCH_INVALID");
 const seen=new Set();
 const byLead=new Map(research.sourceLeads.map(x=>[x.caseId,x]));
 const byRaw=new Map(research.priceDataRawAndAdjusted.map(x=>[x.caseId,x]));
 if(byLead.size!==research.sourceLeads.length||
  byRaw.size!==research.priceDataRawAndAdjusted.length)
  throw Error("RAAS_T79_14_DUPLICATE_OR_MISSING_CASE");
 const rows=[];
 for(const event of sourceEvents.records){
  const c=research.caseResearch.find(x=>x.caseId===event.caseId);
  const lead=byLead.get(event.caseId),prices=byRaw.get(event.caseId);
  if(!c||!lead||!prices||seen.has(event.caseId)||
   c.ticker!==event.ticker||lead.ticker!==event.ticker||
   prices.ticker!==event.ticker||lead.pdufaTargetDate!==event.pdufaTargetDate||
   prices.pdufaTargetDate!==event.pdufaTargetDate||
   lead.actualFDAActionDate!==event.actualFDAActionDate||
   prices.actualFDAActionDate!==event.actualFDAActionDate||
   lead.eligibleForApprovedTrading!==false||
   prices.eventTradeCasesValidated!==0||prices.approvedRaasRatings!==0||
   prices.source!=="ALPACA_SIP_RAW_CLOSE_X_SEC_COVER_SHARES"||
   prices.priceReturnSource!=="ALPACA_SIP_ADJUSTMENT_ALL_SEPARATE"||
   !Array.isArray(prices.observations)||!validDate(event.targetAnnouncementDate)||
   !validDate(event.phase3ReadoutDate)||!validDate(event.actualFDAActionDate)||
   !["APPROVED","CRL"].includes(event.actualFDAOutcome))
   throw Error("RAAS_T79_14_CASE_IDENTITY_OR_SOURCE_INVALID");
  seen.add(event.caseId);
  const x=c.namedWindow79to14;
  if(!x||x.entryLeadDays!==79||x.exitLeadDays!==14||
   x.studyEligible!==false||x.validated!==false)
   throw Error("RAAS_T79_14_WINDOW_INVALID");
  const base={caseId:event.caseId,ticker:event.ticker,year:+event.pdufaTargetDate.slice(0,4),
   originalPdufaGoalDate:event.originallyAnnouncedPdufaTargetDate||event.pdufaTargetDate,
   revisedPdufaGoalDate:event.pdufaTargetDate,goalFirstPublicDate:event.targetAnnouncementDate,
   formalExtension:!!event.formalGoalExtensionIndependentlyVerified,
   actualFdaActionDate:event.actualFDAActionDate,
   actualFdaOutcomeRetrospective:event.actualFDAOutcome,
   entryLeadDays:79,exitLeadDays:14,entryDate:x.actualEntryDate||null,
   exitDate:x.actualExitDate||null,netCostModel:"ILLUSTRATIVE_FLAT_ONE_PERCENTAGE_POINT",
   validatedTradingCase:false,approvedRaasMetric:false,independentlyVerifiedPrice:false,
   completeFDAEventCensus:false};
  if(x.status!=="UNVALIDATED_ADDITIONAL_PREENTRY_WINDOW_RESEARCH"){
   if(x.provisionalGrossReturnPct!==null||x.provisionalNetReturnPct!==null)
    throw Error("RAAS_T79_14_BLOCKED_RETURN_MUST_BE_NULL");
   rows.push({...base,status:"BLOCKED_RESEARCH_WINDOW",blocker:x.reason||"UNKNOWN",
    grossReturnPct:null,hypotheticalNetReturnPct:null,entryCapResearchMillions:null});
   continue;
  }
  if(!validDate(x.actualEntryDate)||!validDate(x.actualExitDate)||
   x.actualEntryDate>=x.actualExitDate||
   x.actualEntryDate<days(event.pdufaTargetDate,-79)||
   x.actualEntryDate>days(event.pdufaTargetDate,-75)||
   x.actualExitDate>days(event.pdufaTargetDate,-14)||
   x.actualExitDate<days(event.pdufaTargetDate,-18)||
   x.actualEntryDate<event.targetAnnouncementDate||
   x.actualEntryDate<event.phase3ReadoutDate||
   x.actualExitDate>=event.actualFDAActionDate||
   !numeric(x.provisionalGrossReturnPct)||
   !numeric(x.provisionalNetReturnPct)||
   !numeric(x.provisionalEntryCapMillions)||
   x.provisionalEntryCapMillions<300||x.provisionalEntryCapMillions>10000||
   !validUrl(x.historicalSharesSourceUsed)||
   !validDate(x.shareFactFirstSafeDate)||
   x.actualEntryDate<x.shareFactFirstSafeDate||
   ![lead.earlierSECSource,lead.laterSECSource].includes(x.historicalSharesSourceUsed)||
   x.supplementalShareFactUsed!==(x.historicalSharesSourceUsed===lead.earlierSECSource))
   throw Error("RAAS_T79_14_POINT_IN_TIME_OR_CAP_INVALID");
  if(event.originallyAnnouncedPdufaTargetDate&&(
    !validDate(event.originallyAnnouncedPdufaTargetDate)||
    !validDate(event.originalTargetAnnouncementDate)||
    event.originalTargetAnnouncementDate>=event.targetAnnouncementDate||
    event.originallyAnnouncedPdufaTargetDate>=event.pdufaTargetDate||
    !validDate(event.fdaGoalExtensionAnnouncedDate)||
    event.fdaGoalExtensionAnnouncedDate!==event.targetAnnouncementDate||
    event.formalGoalExtensionIndependentlyVerified!==true))
   throw Error("RAAS_T79_14_GOAL_EXTENSION_CHRONOLOGY_INVALID");
  const entry=prices.observations.find(o=>o.session===x.actualEntryDate);
  const exit=prices.observations.find(o=>o.session===x.actualExitDate);
  if(!entry||!exit||!numeric(entry.rawClose)||entry.rawClose<=0||
   !numeric(entry.adjustedClose)||entry.adjustedClose<=0||
   !numeric(exit.adjustedClose)||exit.adjustedClose<=0||
   !validUrl(prices.shareFactSourceUrl))
   throw Error("RAAS_T79_14_MISSING_RAW_OR_ADJUSTED_BARS");
  const expectedGross=round((exit.adjustedClose/entry.adjustedClose-1)*100);
  const selectedShares=x.supplementalShareFactUsed?lead.earlierShares:lead.laterShares;
  const expectedCap=round(entry.rawClose*selectedShares/1000000);
  if(Math.abs(expectedGross-x.provisionalGrossReturnPct)>0.02||
   Math.abs(round(x.provisionalGrossReturnPct-1)-x.provisionalNetReturnPct)>0.011||
   Math.abs(expectedCap-x.provisionalEntryCapMillions)>0.011||
   x.reason!=="NEEDS_SHARE_CONTINUITY_SPLIT_AND_INDEPENDENT_PRICE_AUDIT")
   throw Error("RAAS_T79_14_PRICE_ARITHMETIC_OR_PROVENANCE_INVALID");
  rows.push({...base,status:"UNVALIDATED_ALPACA_PRICE_RESEARCH",
   blocker:"SEC_SHARE_CONTINUITY_CORPORATE_ACTIONS_AND_INDEPENDENT_PRICE_CHECK_MISSING",
   grossReturnPct:x.provisionalGrossReturnPct,
   hypotheticalNetReturnPct:x.provisionalNetReturnPct,
   entryCapResearchMillions:x.provisionalEntryCapMillions,
   secSharesSource:x.historicalSharesSourceUsed,
   earlierSECShareSnapshotUsed:x.supplementalShareFactUsed});
 }
 if(seen.size!==sourceEvents.records.length)throw Error("RAAS_T79_14_INCOMPLETE_CASES");
 rows.sort((a,b)=>a.year-b.year||a.ticker.localeCompare(b.ticker));
 const accepted=rows.filter(x=>x.status==="UNVALIDATED_ALPACA_PRICE_RESEARCH");
 const stats=x=>{
  const gross=x.map(r=>r.grossReturnPct);
  const net=x.map(r=>r.hypotheticalNetReturnPct);
  return {cases:x.length,provisionalMeanGrossPct:gross.length?round(gross.reduce((a,b)=>a+b,0)/gross.length):null,
   provisionalMedianGrossPct:gross.length?round(median(gross)):null,
   hypotheticalMeanNetPct:net.length?round(net.reduce((a,b)=>a+b,0)/net.length):null,
   positiveGrossCases:gross.filter(v=>v>0).length,negativeGrossCases:gross.filter(v=>v<0).length};
 };
 return {schemaVersion:1,scope:"RAAS_ACTIVE_2024_2025_T79_TO_T14_RESEARCH_AUDIT",
  status:"UNVALIDATED_PROVISIONAL_RETURN_DIAGNOSTIC_ONLY",
  period:"2024-2025",window:{entryLeadCalendarDays:79,exitLeadCalendarDays:14},
  sourceCaseCount:rows.length,rows,
  allProvisional:stats(accepted),byOutcome:{
   APPROVED:stats(accepted.filter(r=>r.actualFdaOutcomeRetrospective==="APPROVED")),
   CRL:stats(accepted.filter(r=>r.actualFdaOutcomeRetrospective==="CRL"))},byYear:{
   2024:stats(accepted.filter(r=>r.year===2024)),
   2025:stats(accepted.filter(r=>r.year===2025))},
  blockedCases:rows.length-accepted.length,
  requiredIndependentTrainIssuers:30,requiredIndependentHoldoutIssuers:30,
  completedFDAFullCensusYears:0,independentlyValidatedTradingCases:0,
  approvedRaasMetrics:0,approvedOptimalWindow:null,
  warnings:["One row per source-backed issuer; overlapping grid windows are not independent trades.",
   "These cases are source-selected approval and CRL examples; they are neither the two-year FDA outcome census nor an unbiased win/loss cohort.",
   "The net result deducts a hypothetical flat 1 percentage point, not verified historical execution costs.",
   "The SEC cover share snapshots and Alpaca raw/adjusted price arithmetic remain unvalidated for share continuity, actions and independent vendor consistency.",
   "SLNO's 2025 goal follows a 2024 formal extension; its revised date must have been public before the entry session.",
   "Historical FDA outcome labels are retrospective for describing cohorts, not features available at trade entry.",
   "No T-79/T-14 statistical optimum or RAAS score is established."]};
}
function csv(result){
 const cols=["ticker","year","originalPdufaGoalDate","revisedPdufaGoalDate",
  "goalFirstPublicDate","actualFdaActionDate","actualFdaOutcomeRetrospective","entryDate","exitDate",
  "status","grossReturnPct","hypotheticalNetReturnPct","entryCapResearchMillions","blocker"];
 const numericFields=new Set(["grossReturnPct","hypotheticalNetReturnPct","entryCapResearchMillions"]);
 const cell=(key,value)=>{
  if(numericFields.has(key)){
   if(value===null||value===undefined)return '""';
   if(typeof value!=="number"||!Number.isFinite(value))
    throw Error("RAAS_T79_14_EXPORT_NON_NUMERIC_RESULT");
   return String(value); // Real Excel/Sheets numeric including negatives, not a formula.
  }
  const s=String(value??"");
  const safe=/^[\s\u0000-\u001f]*[=+\-@]/u.test(s)?"'"+s:s;
  return '"'+safe.replaceAll('"','""')+'"';
 };
 return cols.join(",")+"\n"+result.rows.map(x=>cols.map(k=>cell(k,x[k])).join(",")).join("\n")+"\n";
}
function main(){
 try{
  const input=process.env.RAAS_ACTIVE_SOURCE_RESEARCH_OUTPUT||
   path.join(root,"raas-2024-2025-original-source-research.json");
  const json=process.env.RAAS_T79_14_AUDIT_JSON||path.join(root,"raas-2024-2025-t79-14-audit.json");
  const csvPath=process.env.RAAS_T79_14_AUDIT_CSV||path.join(root,"raas-2024-2025-t79-14-audit.csv");
  const events=JSON.parse(fs.readFileSync(path.join(root,sourcesPath),"utf8"));
  const result=build(JSON.parse(fs.readFileSync(input,"utf8")),events);
  for(const f of [json,csvPath])fs.mkdirSync(path.dirname(f),{recursive:true});
  fs.writeFileSync(json,JSON.stringify(result,null,2)+"\n");
  fs.writeFileSync(csvPath,csv(result));
  console.log(JSON.stringify({status:result.status,sourceCaseCount:result.sourceCaseCount,
   meanGross:result.allProvisional.provisionalMeanGrossPct,
   medianGross:result.allProvisional.provisionalMedianGrossPct,
   byYear:result.byYear,validatedTradingCases:0,approvedRaasMetrics:0}));
  if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
   "### T-79 to T-14 price window: "+result.sourceCaseCount+" UNVALIDATED issuer research leads\n\n"+
   JSON.stringify(result.allProvisional,null,2)+"\n\nNo optimal strategy or RAAS grade.\n");
 }catch(e){console.error("RAAS_T79_14_AUDIT_FATAL_"+String(e.message||e).replace(/[^A-Z0-9_]/g,"_"));process.exitCode=1;}
}
if(require.main===module)main();
module.exports={build,csv};