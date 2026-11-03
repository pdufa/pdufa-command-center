#!/usr/bin/env node
"use strict";
/**
 * Research-only 2025 CRL target screening. Unlike outcome-selected return
 * tables, independently log why sourced candidates do NOT enter a 2024–2025
 * Phase 3 / $300M-$10B historical T-79 -> T-14 trade sample.
 *
 * The actual FDA outcome, FDA letter and 2026 retrospective sources are
 * never eligible as pre-decision prediction features. No scan/trade writes.
 */
const fs=require("node:fs"),path=require("node:path");
const {fetchBars}=require("./raas_historical_raw_market_cap_research.cjs");
const root=path.resolve(__dirname,"..");
const SCOPE="RAAS_2025_HISTORICAL_CRL_CANDIDATE_REVIEW_ONLY";
const OUTPUT="RAAS_2025_CRL_CANDIDATE_INCLUSION_EXCLUSION_AUDIT";
const day=s=>typeof s==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 !Number.isNaN(Date.parse(s+"T00:00:00Z"))&&
 new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const url=s=>typeof s==="string"&&/^https:\/\/[^\s/]+\.[^\s/]+/.test(s);
const addDays=(s,n)=>new Date(Date.parse(s+"T00:00:00Z")+n*86400000).toISOString().slice(0,10);
const round=n=>Math.round((n+Number.EPSILON)*100)/100;
function checkSource(x,known){
 if(known!==undefined&&known!==null){
  if(!Array.isArray(known.records))throw Error("RAAS_CRL_REVIEW_TRADING_SOURCE_INVALID");
  if(known.records.some(e=>e.caseId===x.caseId||e.ticker===x.ticker))
   throw Error("RAAS_CRL_REVIEW_ALREADY_IN_PRIMARY_SAMPLE");
 }
 if(!x||!["ALDX|REPROXALAP_DRY_EYE|NDA216442|2025_04_CRL",
                  "CAPR|DERAMIOCEL_DMD|BLA125842|2025_07_CRL"].includes(x.caseId)||
  !/^[A-Z]{3,5}$/.test(x.ticker||"")||
  !day(x.pdufaTargetDate)||!x.pdufaTargetDate.startsWith("2025-")||
  !day(x.targetAnnouncementDate)||!day(x.phase3ReadoutDate)||
  !day(x.actualFDAActionDate)||!day(x.originalPublicActionAnnouncementDate)||
  x.targetAnnouncementDate>=x.pdufaTargetDate||
  x.phase3ReadoutDate<=x.targetAnnouncementDate&&x.phase3ReadoutDate>"2025-12-31"||
  x.actualFDAActionDate>x.originalPublicActionAnnouncementDate||
  x.actualFDAOutcome!=="CRL"||
  !url(x.targetAnnouncementSourceUrl)||!url(x.phase3ReadoutSourceUrl)||
  !url(x.actualFDAActionSourceUrl)||!url(x.originalPublicActionAnnouncementUrl)||
  !x.actualFDAActionSourceUrl.startsWith("https://download.open.fda.gov/crl/")||
  !x.actualFDAActionSourceUrl.endsWith(x.actualFDAActionDate.replaceAll("-","")+".pdf")||
  x.originalPublicFDAOutcomeKnownAtEntry!==false||
  x.studyAcceptedAsValidatedTrade!==false||
  x.fullYearCensusEligibilityProven!==false||
  x.reviewStatus!=="SOURCE_CANDIDATE_RESEARCH_ONLY"||
  x.reviewCyclesMustRemainSeparate!==true||
  x.phase3RegistryStudyIdentityIndependentlyVerified!==false)
  throw Error("RAAS_CRL_REVIEW_CANDIDATE_PROVENANCE_INVALID");
 if(x.ticker==="ALDX"){
  const s=x.shareSource;
  if(x.application!=="NDA 216442"||x.pdufaTargetDate!=="2025-04-02"||
   x.targetAnnouncementDate!=="2024-11-18"||
   x.phase3ReadoutDate!=="2024-08-08"||
   x.actualFDAActionDate!=="2025-04-02"||
   x.originalPublicActionAnnouncementDate!=="2025-04-03"||
   !s||s.cik!=="0001341235"||s.sharesOutstanding!==59549598||
   s.sharesMeasurementDate!=="2024-11-05"||
   s.filedDate!=="2024-11-07"||
   s.firstConservativeEntryDate!=="2024-11-08"||
   s.acceptedAfterCloseET!==true||
   s.sourceStatus!=="DATED_SEC_COVER_RESEARCH_NOT_CONTINUOUS_SHARES"||
   !url(s.sourceUrl)||!url(s.filingIndexUrl))
   throw Error("RAAS_CRL_REVIEW_ALDX_DATED_SEC_OR_CYCLE_INVALID");
 }else{
  if(x.application!=="BLA 125842"||x.pdufaTargetDate!=="2025-08-31"||
   x.targetAnnouncementDate!=="2025-03-04"||
   x.phase3ReadoutDate!=="2025-12-03"||
   x.actualFDAActionDate!=="2025-07-09"||
   x.originalPublicActionAnnouncementDate!=="2025-07-11"||
   x.shareSource!==null)
   throw Error("RAAS_CRL_REVIEW_CAPR_ACTION_OR_PHASE3_INVALID");
 }
}
function summarize(rows){
 const counts={};
 for(const r of rows)counts[r.exclusionOrReviewReason]=(counts[r.exclusionOrReviewReason]||0)+1;
 return counts;
}
async function build({candidates,primarySource=null,key,secret,request=fetch,
 fetcher=fetchBars}={}){
 if(!candidates||candidates.scope!==SCOPE||candidates.schemaVersion!==1||
  !Array.isArray(candidates.records)||candidates.records.length!==2||
  !candidates.records.some(c=>c.ticker==="ALDX")||
  !candidates.records.some(c=>c.ticker==="CAPR"))
  throw Error("RAAS_CRL_REVIEW_SOURCE_INVALID");
 const seen=new Set(),rows=[];
 for(const c of candidates.records){
  checkSource(c,primarySource);
  if(seen.has(c.ticker))throw Error("RAAS_CRL_REVIEW_DUPLICATE_TICKER");
  seen.add(c.ticker);
  const plannedEntry=addDays(c.pdufaTargetDate,-79),
   plannedExit=addDays(c.pdufaTargetDate,-14);
  const base={caseId:c.caseId,ticker:c.ticker,application:c.application,
   pdufaTargetDate:c.pdufaTargetDate,phase3ReadoutDate:c.phase3ReadoutDate,
   plannedEntryCalendarDate:plannedEntry,plannedExitCalendarDate:plannedExit,
   actualFDAActionDateRetrospective:c.actualFDAActionDate,
   outcomeRetrospective:"CRL",
   firstPublicPdufaTargetDate:c.targetAnnouncementDate,
   targetAnnouncementSourceUrl:c.targetAnnouncementSourceUrl,
   phase3ReadoutSourceUrl:c.phase3ReadoutSourceUrl,
   officialFDAOutcomeLetterRetrospectiveUrl:c.actualFDAActionSourceUrl,
   historicalEntryTradeApproved:false,validatedHistoricalCap:false,
   validatedHistoricalReturn:false,eligibleForRaasCalibration:false,
   retrospectiveFDAOutcomeWasKnownAtEntry:false,
   fullFDAEventCensusAudited:false,independentPriceVendorCrosschecked:false,
   sourceReviewOnly:true,computedEntrySession:null,
   rawEntryClose:null,capResearchMillions:null};
  if(c.phase3ReadoutDate>plannedEntry){
   rows.push({...base,status:"EXCLUDED_FROM_PHASE3_COMPLETE_AT_ENTRY_COHORT",
    exclusionOrReviewReason:"PHASE3_READOUT_NOT_PUBLIC_AT_PLANNED_ENTRY"});
   continue;
  }
  if(c.actualFDAActionDate<=plannedExit){
   rows.push({...base,status:"EXCLUDED_EARLY_FDA_ACTION",
    exclusionOrReviewReason:"FDA_ACTION_CENSORED_PLANNED_EXIT"});
   continue;
  }
  if(c.targetAnnouncementDate>plannedEntry){
   rows.push({...base,status:"EXCLUDED_FROM_DISCLOSED_TARGET_AT_ENTRY",
    exclusionOrReviewReason:"PDUFA_TARGET_NOT_PUBLIC_AT_PLANNED_ENTRY"});
   continue;
  }
  if(!c.shareSource||c.shareSource.firstConservativeEntryDate>plannedEntry){
   rows.push({...base,status:"BLOCKED_NO_ENTRY_TIME_SHARE_DISCLOSURE",
    exclusionOrReviewReason:"NO_PUBLIC_SEC_SHARES_BY_ENTRY"});
   continue;
  }
  if(!key||!secret){
   rows.push({...base,status:"BLOCKED_ALPACA_CREDENTIALS",
    exclusionOrReviewReason:"NO_ALPACA_RAW_HISTORICAL_PRICE"});
   continue;
  }
  const bars=await fetcher(c.ticker,c.pdufaTargetDate,plannedEntry,
   addDays(plannedEntry,5),"raw",key,secret,request);
  if(!Array.isArray(bars)||bars.some(b=>!day(b.date)||typeof b.close!=="number"||
   !Number.isFinite(b.close)||b.close<=0))
   throw Error("RAAS_CRL_REVIEW_RAW_ALPACA_INVALID");
  const sessions=bars.filter(b=>b.date>=plannedEntry&&b.date<=addDays(plannedEntry,4))
   .sort((a,b)=>a.date.localeCompare(b.date));
  if(!sessions.length){
   rows.push({...base,status:"BLOCKED_NO_ENTRY_SESSION",
    exclusionOrReviewReason:"NO_ALPACA_SIP_RAW_ENTRY_BAR"});
   continue;
  }
  if(sessions[0].date<c.shareSource.firstConservativeEntryDate||
   sessions[0].date<c.targetAnnouncementDate||
   sessions[0].date<c.phase3ReadoutDate)
   throw Error("RAAS_CRL_REVIEW_LOOKAHEAD_DATE_REJECTED");
  const b=sessions[0],cap=b.close*c.shareSource.sharesOutstanding/1000000;
  const classified=cap<300||cap>10000?
   ["EXCLUDED_PROVISIONAL_ENTRY_CAP_OUTSIDE_300M_10B","CAP_OUTSIDE_PROVISIONAL_BAND"]:
   ["BLOCKED_FOR_FULL_VALIDATION_EVEN_WITH_CAP_IN_BAND","CAP_ONLY_UNVALIDATED"];
  rows.push({...base,computedEntrySession:b.date,rawEntryClose:b.close,
   capResearchMillions:round(cap),secCoverSharesUsed:c.shareSource.sharesOutstanding,
   secShareMeasurementDate:c.shareSource.sharesMeasurementDate,
   secSharesFirstSafeDate:c.shareSource.firstConservativeEntryDate,
   historicalSECSourceUrl:c.shareSource.sourceUrl,
   status:classified[0],exclusionOrReviewReason:classified[1]});
 }
 return {schemaVersion:1,scope:OUTPUT,
  status:"RESEARCH_CRL_CANDIDATE_CHRONOLOGY_AND_CAP_REVIEW_NOT_TRADING_SAMPLE",
  candidateSourceCount:rows.length,rows,
  reasonCounts:summarize(rows),
  2024TrainYearSourceCaseAdditions:0,
  2025HoldoutYearValidatedTradeAdditions:0,
  independentlyValidatedEntryCaps:0,
  auditedCompleteFDA2024And2025YearCensuses:0,
  approvedRaasMetrics:0,approvedOptimalTradingWindow:null,
  warnings:[
   "CAPR's December 2025 pivotal HOPE-3 data cannot be backdated into the pre-July 2025 CRL 2025 review cycle.",
   "Aldeyra's April 2025 CRL is separate from the 2023/2026 review cycles; new clinical data from May 2025 cannot be used before April 2025.",
   "FDA outcome letters are retrospective information; no action/outcome label is included in any pre-entry predictive feature.",
   "ALDX raw historical Alpaca price x November 2024 SEC cover shares is only provisional, not independently validated market cap or 2025 return.",
   "A provisional $300M-$10B capitalization failure must be recorded, not silently dropped, to prevent survivor/eligibility selection bias.",
   "This stand-alone exclusion review does NOT modify the existing nine-case selected research sample, calibrate RAAS or approve a trade."
  ]};
}
function csv(result){
 if(result?.scope!==OUTPUT)throw Error("RAAS_CRL_REVIEW_CSV_INVALID");
 const fields=["ticker","application","pdufaTargetDate","plannedEntryCalendarDate",
  "plannedExitCalendarDate","phase3ReadoutDate","actualFDAActionDateRetrospective",
  "computedEntrySession","rawEntryClose","capResearchMillions","status",
  "exclusionOrReviewReason","historicalSECSourceUrl"];
 const numbers=new Set(["rawEntryClose","capResearchMillions"]);
 const textField=v=>{const t=String(v??"");
  const safe=/^[\s\u0000-\u001f]*[=+\-@]/u.test(t)?"'"+t:t;
  return '"'+safe.replaceAll('"','""')+'"';};
 const cell=(k,v)=>{if(numbers.has(k)){if(v==null)return '""';
  if(typeof v!=="number"||!Number.isFinite(v))
   throw Error("RAAS_CRL_REVIEW_NUMERIC_EXPORT_INVALID");
  return String(v);}return textField(v);};
 return fields.join(",")+"\n"+result.rows.map(x=>
  fields.map(k=>cell(k,x[k])).join(",")).join("\n")+"\n";
}
async function main(){
 try{
  const data=require("../new-platform/frontend/data/raas-2025-adverse-candidate-inclusion-exclusion-leads.json"),
   primary=require("../new-platform/frontend/data/raas-active-2024-2025-primary-source-leads.json"),
   key=process.env.APCA_API_KEY_ID,secret=process.env.APCA_API_SECRET_KEY;
  const report=await build({candidates:data,primarySource:primary,key,secret});
  const out=process.env.RAAS_CRL_CANDIDATE_AUDIT_JSON||
   path.join(root,"raas-2025-crl-candidate-exclusions.json");
  const file=process.env.RAAS_CRL_CANDIDATE_AUDIT_CSV||
   path.join(root,"raas-2025-crl-candidate-exclusions.csv");
  for(const f of [out,file])fs.mkdirSync(path.dirname(f),{recursive:true});
  fs.writeFileSync(out,JSON.stringify(report,null,2)+"\n");
  fs.writeFileSync(file,csv(report));
  console.log(JSON.stringify({status:report.status,reviewCandidates:report.candidateSourceCount,
   reasons:report.reasonCounts,ALDX:report.rows.find(x=>x.ticker==="ALDX"),
   validatedNewTrades:0,approvedRaasMetrics:0}));
  if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
   "### 2025 separately sourced CRL inclusion/exclusion audit (NOT VALIDATED)\n\n"+
   JSON.stringify(report.reasonCounts,null,2)+"\n\n0 validated entries.\n");
  if(report.rows.some(x=>x.status==="BLOCKED_ALPACA_CREDENTIALS"))process.exitCode=1;
 }catch(e){console.error("RAAS_CRL_REVIEW_FATAL_"+String(e.message||e).replace(/[^A-Z0-9_]/g,"_"));process.exitCode=1;}
}
if(require.main===module)main();
module.exports={build,csv,checkSource,addDays};
