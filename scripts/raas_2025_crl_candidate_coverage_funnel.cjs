#!/usr/bin/env node
"use strict";

// Permanent retirement: no historical artifact writer may execute as a command.
if (require.main === module) { process.stderr.write("RAAS_PERMANENTLY_RETIRED: this archived command cannot run or modify historical records.\n"); process.exit(78); }

/**
 * Research-only ledger: all 2024-25 originally sourced historical return
 * examples plus sourced FDA CRL candidates that did NOT pass the same
 * as-of Phase 3, original PDUFA goal and market-cap screening rules.
 *
 * A CONVENIENCE COVERAGE FUNNEL, NOT a complete FDA PDUFA target-year census.
 * Never use retrospective CRL outcome as a prospective entry-time metric.
 */
const fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"..");
const PRIMARY="RAAS_HISTORICAL_PRIMARY_PDUFA_EVENT_EVIDENCE_RESEARCH";
const AUDIT="RAAS_ACTIVE_2024_2025_T79_TO_T14_RESEARCH_AUDIT";
const PREVIOUS="RAAS_2025_CRL_CANDIDATE_INCLUSION_EXCLUSION_AUDIT";
const SOURCE="RAAS_2025_PDUFA_CRL_UNRESOLVED_OR_PREPHASE3_RESEARCH";
const OUT="RAAS_2024_2025_HISTORIC_PDUFA_CANDIDATE_COVERAGE_FUNNEL_ONLY";
const day=x=>typeof x==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&
 new Date(x+"T00:00:00Z").toISOString().slice(0,10)===x;
const url=x=>typeof x==="string"&&/^https:\/\/[^/\s]+\.[^/\s]+/.test(x);
const minus=(s,n)=>new Date(Date.parse(s+"T00:00:00Z")-n*86400000)
 .toISOString().slice(0,10);
function assertCandidate(c,originalIds){
 if(!c||!["BHVN","REPL"].includes(c.ticker)||
  originalIds.has(c.ticker)||typeof c.caseId!=="string"||!c.caseId||
  !["NASDAQ","NYSE"].includes(c.venue)||
  !day(c.actualFdaActionDate)||c.actualFdaActionDate.slice(0,4)!=="2025"||
  !day(c.actionFirstPublicAnnouncementDate)||
  c.actionFirstPublicAnnouncementDate<c.actualFdaActionDate||
  !url(c.actionFirstPublicAnnouncementUrl)||
  c.actualOutcomeRetrospective!=="CRL"||
  c.historicalTradingCaseValidated!==false||
  c.validatedHistoricalCap!==false||c.approvedRaasCalibration!==false||
  c.shareSource!==null)
  throw Error("RAAS_2025_EXTRA_CRL_EVIDENCE_UNTRUSTED");
 if(c.ticker==="REPL"){
  if(c.caseId!=="REPL|RP1_ADVANCED_MELANOMA|BLA125827|2025_CRL"||
   c.application!=="BLA 125827"||
   c.firstPublicExactPdufaTargetDate!=="2025-07-22"||
   c.firstPublicExactPdufaAnnouncementDate!=="2025-01-21"||
   !url(c.firstPublicExactPdufaAnnouncementUrl)||
   c.primaryPivotalStudyPhase!=="PHASE_1_2"||
   c.primaryPivotalStudyNct!=="NCT03767348"||
   c.confirmatoryPhase3Nct!=="NCT06264180"||
   c.firstConfirmatoryPhase3PatientDosedDate!=="2024-08-13"||
   !url(c.firstConfirmatoryPhase3PatientSourceUrl)||
   c.preEntryPublicPhase3EvidenceDate!=="2025-02-12"||
   !url(c.preEntryPublicPhase3EvidenceUrl)||
   c.preEntryConfirmatoryPhase3Status!=="ENROLLING_NO_COMPLETED_READOUT"||
   c.relevantPhase3ReadoutPublicAtPlannedEntry!==false||
   c.firstLocatedReadoutDate!==null||
   c.actualFdaActionDate!=="2025-07-21"||
   c.actionFirstPublicAnnouncementDate!=="2025-07-22"||
   c.reviewGate!=="EXCLUDE_PHASE3_CONFIRMATORY_NOT_COMPLETED")
   throw Error("RAAS_REPL_PHASE3_AND_FDA_ASOF_NOT_VERIFIED");
  const entry=minus(c.firstPublicExactPdufaTargetDate,79);
  const exit=minus(c.firstPublicExactPdufaTargetDate,14);
  if(c.firstPublicExactPdufaAnnouncementDate>entry||
   c.preEntryPublicPhase3EvidenceDate>entry||
   c.firstConfirmatoryPhase3PatientDosedDate>entry||
   c.actualFdaActionDate<=entry||
   exit<=entry||c.actualFdaActionDate>c.firstPublicExactPdufaTargetDate)
   throw Error("RAAS_REPL_TIMELINE_INVALID");
  return {caseId:c.caseId,ticker:c.ticker,year:2025,
   pdufaTargetKnownAtEntry:true,originalPublicGoalDate:c.firstPublicExactPdufaTargetDate,
   plannedEntryDate:entry,plannedExitDate:exit,
   fdaOutcomeRetrospective:"CRL",
   clinicalSourceUrl:c.preEntryPublicPhase3EvidenceUrl,
   actionDisclosureUrl:c.actionFirstPublicAnnouncementUrl,
   status:"EXCLUDED_PHASE3_CONFIRMATORY_ENROLLING_AT_ENTRY",
   reason:"PIVOTAL_BLA_SUPPORTED_BY_PHASE1_2_NOT_COMPLETED_CONFIRMATORY_PHASE3",
   eligibleHistoricalTradingCase:false,validatedHistoricalCap:false,
   approvedRaasMetric:false};
 }
 if(c.caseId!=="BHVN|TRORILUZOLE_SCA|NDA210862|2025_CRL"||
  c.application!=="NDA 210862"||
  c.firstPublicExactPdufaTargetDate!==null||
  c.firstPublicExactPdufaAnnouncementDate!==null||
  c.firstPublicExactPdufaAnnouncementUrl!==null||
  c.originalPublicExpectedTargetPeriod!=="2025-Q3"||
  c.originalExpectedPeriodEvidenceDate!=="2025-03-03"||
  !url(c.originalExpectedPeriodSourceUrl)||
  c.extensionFirstPublicDate!=="2025-05-14"||
  c.extensionMonths!==3||
  c.extensionPublicExpectedTargetPeriod!=="2025-Q4"||
  !url(c.extensionSourceUrl)||
  c.phase3PublicStatus!=="REQUIRES_STUDY_AND_ASOF_EVIDENCE_REVIEW"||
  c.phase3ExactNctFirstLocated!==null||
  c.actualFdaActionDate!=="2025-11-04"||
  c.actionFirstPublicAnnouncementDate!=="2025-11-04"||
  c.reviewGate!=="BLOCK_EXACT_PUBLIC_PDUFA_GOAL_NOT_ESTABLISHED")
  throw Error("RAAS_BHVN_NOT_EXACT_PUBLIC_GOAL_OR_FDA_CYCLE");
 return {caseId:c.caseId,ticker:c.ticker,year:2025,
  pdufaTargetKnownAtEntry:false,originalPublicGoalDate:null,
  plannedEntryDate:null,plannedExitDate:null,
  originalPublicExpectedTargetPeriod:c.originalPublicExpectedTargetPeriod,
  extendedPublicExpectedTargetPeriod:c.extensionPublicExpectedTargetPeriod,
  fdaOutcomeRetrospective:"CRL",
  clinicalSourceUrl:null,actionDisclosureUrl:c.actionFirstPublicAnnouncementUrl,
  status:"BLOCKED_EXACT_FIRST_PUBLIC_PDUFA_GOAL_NOT_YET_SOURCED",
  reason:"QUARTER_IS_NOT_EXACT_PDUFA_TARGET_DATE",
  eligibleHistoricalTradingCase:false,validatedHistoricalCap:false,
  approvedRaasMetric:false};
}
function build({primary,audit,previous,extras}={}){
 if(primary?.scope!==PRIMARY||!Array.isArray(primary.records)||
  audit?.scope!==AUDIT||
  audit.status!=="UNVALIDATED_PROVISIONAL_RETURN_DIAGNOSTIC_ONLY"||
  audit.approvedRaasMetrics!==0||audit.independentlyValidatedTradingCases!==0||
  audit.completedFDAFullCensusYears!==0||audit.approvedOptimalWindow!==null||
  !Array.isArray(audit.rows)||audit.sourceCaseCount!==primary.records.length||
  previous?.scope!==PREVIOUS||
  previous.status!=="RESEARCH_CRL_CANDIDATE_CHRONOLOGY_AND_CAP_REVIEW_NOT_TRADING_SAMPLE"||
  previous.approvedRaasMetrics!==0||previous.independentlyValidatedEntryCaps!==0||
  previous.auditedCompleteFDA2024And2025YearCensuses!==0||
  !Array.isArray(previous.rows)||previous.rows.length!==2||
  extras?.scope!==SOURCE||!Array.isArray(extras.records)||extras.records.length!==2)
  throw Error("RAAS_CRL_FUNNEL_SOURCE_GRADE_INVALID");
 const originalTickers=new Set(),originalCases=new Set();
 const priorByCase=new Map(audit.rows.map(r=>[r.caseId,r]));
 if(priorByCase.size!==audit.rows.length)throw Error("RAAS_CRL_FUNNEL_RESEARCH_DUPLICATED");
 const rows=[];
 for(const x of primary.records){
  if(!x?.caseId||originalCases.has(x.caseId)||originalTickers.has(x.ticker)||
   !["APPROVED","CRL"].includes(x.actualFDAOutcome)||
   x.historicalCapitalizationAtEntryVerified!==false||
   x.reviewStatus!=="SOURCE_LEADS_RESEARCH_ONLY"||
   !day(x.pdufaTargetDate)||
   x.pdufaTargetDate.slice(0,4)!=="2024"&&
   x.pdufaTargetDate.slice(0,4)!=="2025")
   throw Error("RAAS_CRL_FUNNEL_ORIGINAL_SOURCE_INVALID");
  const a=priorByCase.get(x.caseId);
  if(!a||a.ticker!==x.ticker||
   a.actualFdaOutcomeRetrospective!==x.actualFDAOutcome||
   !["UNVALIDATED_ALPACA_PRICE_RESEARCH","BLOCKED_RESEARCH_WINDOW"].includes(a.status)||
   a.validatedTradingCase!==false||a.approvedRaasMetric!==false||
   a.independentlyVerifiedPrice!==false)
   throw Error("RAAS_CRL_FUNNEL_ORIGINAL_RESEARCH_MISMATCH");
  originalCases.add(x.caseId);originalTickers.add(x.ticker);
  rows.push({caseId:x.caseId,ticker:x.ticker,year:+x.pdufaTargetDate.slice(0,4),
   status:"SOURCE_SELECTED_PRICE_RESEARCH_NOT_VALIDATED",
   reason:"SELECTED_ISSUER_SAMPLE_NOT_FULL_PDUFA_CENSUS_OR_VERIFIED_TRADES",
   pdufaTargetKnownAtEntry:true,originalPublicGoalDate:x.pdufaTargetDate,
   plannedEntryDate:a.entryDate,plannedExitDate:a.exitDate,
   fdaOutcomeRetrospective:x.actualFDAOutcome,
   eligibleHistoricalTradingCase:false,validatedHistoricalCap:false,
   approvedRaasMetric:false});
 }
 const missing=[];
 for(const c of previous.rows){
  if(!["ALDX","CAPR"].includes(c.ticker)||!c.caseId||
   originalTickers.has(c.ticker)||
   c.historicalEntryTradeApproved!==false||c.validatedHistoricalCap!==false||
   c.validatedHistoricalReturn!==false||c.eligibleForRaasCalibration!==false||
   c.retrospectiveFDAOutcomeWasKnownAtEntry!==false||
   c.sourceReviewOnly!==true||c.outcomeRetrospective!=="CRL")
   throw Error("RAAS_CRL_FUNNEL_PREVIOUS_CANDIDATE_INVALID");
  if(missing.some(x=>x.ticker===c.ticker))throw Error("RAAS_CRL_FUNNEL_DUPLICATE_REVIEW");
  if(c.ticker==="CAPR"){
   if(c.status!=="EXCLUDED_FROM_PHASE3_COMPLETE_AT_ENTRY_COHORT"||
    c.exclusionOrReviewReason!=="PHASE3_READOUT_NOT_PUBLIC_AT_PLANNED_ENTRY"||
    c.phase3ReadoutDate<="2025-07-09")
    throw Error("RAAS_CRL_FUNNEL_CAPR_EARLY_PHASE3_NOT_EXCLUDED");
  }else if(c.status!=="EXCLUDED_PROVISIONAL_ENTRY_CAP_OUTSIDE_300M_10B"||
    c.exclusionOrReviewReason!=="CAP_OUTSIDE_PROVISIONAL_BAND"||
    !Number.isFinite(c.capResearchMillions)||c.capResearchMillions>=300)
   throw Error("RAAS_CRL_FUNNEL_ALDX_CAP_NOT_EXCLUDED");
  missing.push(c);
  rows.push({caseId:c.caseId,ticker:c.ticker,year:2025,
   status:c.status,reason:c.exclusionOrReviewReason,
   pdufaTargetKnownAtEntry:true,originalPublicGoalDate:c.pdufaTargetDate,
   plannedEntryDate:c.plannedEntryCalendarDate,plannedExitDate:c.plannedExitCalendarDate,
   fdaOutcomeRetrospective:"CRL",
   provisionalEntryCapResearchMillions:c.capResearchMillions,
   eligibleHistoricalTradingCase:false,validatedHistoricalCap:false,approvedRaasMetric:false});
 }
 const extraTickers=new Set();
 for(const x of extras.records){
  if(originalTickers.has(x.ticker)||missing.some(m=>m.ticker===x.ticker)||
   extraTickers.has(x.ticker))throw Error("RAAS_CRL_FUNNEL_DUPLICATE_REVIEW");
  extraTickers.add(x.ticker);
  rows.push(assertCandidate(x,originalTickers));
 }
 if(extraTickers.size!==2||!extraTickers.has("REPL")||!extraTickers.has("BHVN"))
  throw Error("RAAS_CRL_FUNNEL_MISSING_CASES");
 if(rows.length!==primary.records.length+4)
  throw Error("RAAS_CRL_FUNNEL_UNMATCHED_SOURCE_COUNT");
 const byStatus={};
 for(const x of rows)byStatus[x.status]=(byStatus[x.status]||0)+1;
 return {schemaVersion:1,scope:OUT,
  status:"INCOMPLETE_SELECTED_SOURCE_RESEARCH_AND_EXCLUSION_LEDGER_ONLY",
  distinctFDAReviewCycles:rows.length,
  selectedProvisionalPriceResearchCount:primary.records.length,
  rejectedOrBlockedAdditional2025Candidates:4,
  byYear:{2024:rows.filter(x=>x.year===2024).length,
   2025:rows.filter(x=>x.year===2025).length},
  byReviewStatus:byStatus,rows,
  full2024And2025TargetYearCensusesAudited:0,
  independentlyValidatedTradingCases:0,
  approvedRaasCalibrations:0,
  approvedOptimalWindow:null,
  warnings:[
   "This is a sourced research-and-exclusion ledger, not a complete 2024/2025 FDA PDUFA denominator.",
   "Retrospective FDA outcomes are included for review classification only, never prediction features at entry.",
   "ALDX marginal $300M cap screen uses raw Alpaca close and a dated SEC cover snapshot; no continuous-cap proof.",
   "CAPR and REPL lacked published completed pivotal confirmatory Phase 3 results as of planned entry.",
   "BHVN public issuer/SEC materials located to date disclose quarter only, NOT an exact revised PDUFA calendar date.",
   "No verified trades, FDA full-year censuses, calibrated RAAS scores, or statistically optimal trade windows are established."
  ]};
}
function csv(result){
 if(result?.scope!==OUT)throw Error("RAAS_CRL_FUNNEL_CSV_GRADE_INVALID");
 const columns=["year","ticker","status","reason","originalPublicGoalDate",
  "plannedEntryDate","plannedExitDate","fdaOutcomeRetrospective",
  "provisionalEntryCapResearchMillions","caseId"];
 const numeric=new Set(["year","provisionalEntryCapResearchMillions"]);
 const esc=(k,v)=>{
  if(numeric.has(k)){if(v===null||v===undefined)return "";
   if(typeof v!=="number"||!Number.isFinite(v))
    throw Error("RAAS_CRL_FUNNEL_NUMERIC_EXPORT_UNSAFE");
   return String(v);}
  const s=String(v??""),safe=/^[\s\u0000-\u001f]*[=+\-@]/u.test(s)?"'"+s:s;
  return '"'+safe.replaceAll('"','""')+'"';
 };
 return columns.join(",")+"\n"+result.rows.map(r=>columns.map(k=>esc(k,r[k])).join(",")).join("\n")+"\n";
}
function main(){
 try{
  const read=(env,file)=>JSON.parse(fs.readFileSync(process.env[env]||
   path.join(root,file),"utf8"));
  const r=build({
   primary:read("RAAS_CRL_FUNNEL_PRIMARY","new-platform/frontend/data/raas-active-2024-2025-primary-source-leads.json"),
   audit:read("RAAS_T79_14_AUDIT_JSON","raas-2024-2025-t79-14-audit.json"),
   previous:read("RAAS_CRL_CANDIDATE_AUDIT_JSON","raas-2025-crl-candidate-exclusions.json"),
   extras:read("RAAS_CRL_FUNNEL_EXTRA_SOURCE","new-platform/frontend/data/raas-2025-unanchored-crl-source-leads.json")
  });
  const j=process.env.RAAS_CRL_FUNNEL_JSON||path.join(root,"raas-2024-2025-crl-candidate-coverage-funnel.json"),
   c=process.env.RAAS_CRL_FUNNEL_CSV||path.join(root,"raas-2024-2025-crl-candidate-coverage-funnel.csv");
  for(const f of [j,c])fs.mkdirSync(path.dirname(f),{recursive:true});
  fs.writeFileSync(j,JSON.stringify(r,null,2)+"\n");
  fs.writeFileSync(c,csv(r));
  const summary={status:r.status,candidateReviewCycles:r.distinctFDAReviewCycles,
   selectedOriginalResearch:r.selectedProvisionalPriceResearchCount,
   additionalExcludedOrBlocked:r.rejectedOrBlockedAdditional2025Candidates,
   byYear:r.byYear,byStatus:r.byReviewStatus,
   validatedTrades:0,calibratedRaas:0};
  console.log(JSON.stringify(summary));
  if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
   "### 2024-25 FDA historic research vs excluded/blocked CRL candidate ledger\n\n"+
   JSON.stringify(summary,null,2)+"\n\nNOT a complete FDA PDUFA event population.\n");
 }catch(e){console.error("RAAS_CRL_FUNNEL_FATAL_"+
  String(e.message||e).replace(/[^A-Z0-9_]/g,"_"));process.exitCode=1;}
}
if(require.main===module)main();
module.exports={build,csv,assertCandidate,minus};
