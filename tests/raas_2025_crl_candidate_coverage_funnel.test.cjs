"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const primary=require("../new-platform/frontend/data/raas-active-2024-2025-primary-source-leads.json");
const extras=require("../new-platform/frontend/data/raas-2025-unanchored-crl-source-leads.json");
const {build,csv,minus}=require("../scripts/raas_2025_crl_candidate_coverage_funnel.cjs");
function fixture(){
 const audit={scope:"RAAS_ACTIVE_2024_2025_T79_TO_T14_RESEARCH_AUDIT",
  status:"UNVALIDATED_PROVISIONAL_RETURN_DIAGNOSTIC_ONLY",
  approvedRaasMetrics:0,independentlyValidatedTradingCases:0,
  completedFDAFullCensusYears:0,approvedOptimalWindow:null,
  sourceCaseCount:primary.records.length,rows:primary.records.map(p=>({
   caseId:p.caseId,ticker:p.ticker,
   actualFdaOutcomeRetrospective:p.actualFDAOutcome,
   entryDate:minus(p.pdufaTargetDate,79),exitDate:minus(p.pdufaTargetDate,14),
   status:"UNVALIDATED_ALPACA_PRICE_RESEARCH",
   validatedTradingCase:false,approvedRaasMetric:false,independentlyVerifiedPrice:false
  }))};
 const previous={
  scope:"RAAS_2025_CRL_CANDIDATE_INCLUSION_EXCLUSION_AUDIT",
  status:"RESEARCH_CRL_CANDIDATE_CHRONOLOGY_AND_CAP_REVIEW_NOT_TRADING_SAMPLE",
  approvedRaasMetrics:0,independentlyValidatedEntryCaps:0,
  auditedCompleteFDA2024And2025YearCensuses:0,
  rows:[
   {ticker:"ALDX",caseId:"ALDX|REPROXALAP_DRY_EYE|NDA216442|2025_04_CRL",
    pdufaTargetDate:"2025-04-02",plannedEntryCalendarDate:"2025-01-13",
    plannedExitCalendarDate:"2025-03-19",status:"EXCLUDED_PROVISIONAL_ENTRY_CAP_OUTSIDE_300M_10B",
    exclusionOrReviewReason:"CAP_OUTSIDE_PROVISIONAL_BAND",
    capResearchMillions:284.05,outcomeRetrospective:"CRL",
    historicalEntryTradeApproved:false,validatedHistoricalCap:false,
    validatedHistoricalReturn:false,eligibleForRaasCalibration:false,
    retrospectiveFDAOutcomeWasKnownAtEntry:false,sourceReviewOnly:true},
   {ticker:"CAPR",caseId:"CAPR|DERAMIOCEL_DMD|BLA125842|2025_07_CRL",
    pdufaTargetDate:"2025-08-31",plannedEntryCalendarDate:"2025-06-13",
    plannedExitCalendarDate:"2025-08-17",phase3ReadoutDate:"2025-12-03",
    status:"EXCLUDED_FROM_PHASE3_COMPLETE_AT_ENTRY_COHORT",
    exclusionOrReviewReason:"PHASE3_READOUT_NOT_PUBLIC_AT_PLANNED_ENTRY",
    capResearchMillions:null,outcomeRetrospective:"CRL",
    historicalEntryTradeApproved:false,validatedHistoricalCap:false,
    validatedHistoricalReturn:false,eligibleForRaasCalibration:false,
    retrospectiveFDAOutcomeWasKnownAtEntry:false,sourceReviewOnly:true}
  ]};
 return {primary:structuredClone(primary),audit,previous,extras:structuredClone(extras)};
}
test("Nine provisional original cases and four separately reviewed 2025 CRLs are visible without upgrading predictions",()=>{
 const result=build(fixture());
 assert.equal(result.distinctFDAReviewCycles,13);
 assert.equal(result.selectedProvisionalPriceResearchCount,9);
 assert.equal(result.rejectedOrBlockedAdditional2025Candidates,4);
 assert.deepEqual(result.byYear,{2024:5,2025:8});
 assert.equal(result.byReviewStatus.SOURCE_SELECTED_PRICE_RESEARCH_NOT_VALIDATED,9);
 assert.equal(result.byReviewStatus.EXCLUDED_PROVISIONAL_ENTRY_CAP_OUTSIDE_300M_10B,1);
 assert.equal(result.byReviewStatus.EXCLUDED_FROM_PHASE3_COMPLETE_AT_ENTRY_COHORT,1);
 assert.equal(result.byReviewStatus.EXCLUDED_PHASE3_CONFIRMATORY_ENROLLING_AT_ENTRY,1);
 assert.equal(result.byReviewStatus.BLOCKED_EXACT_FIRST_PUBLIC_PDUFA_GOAL_NOT_YET_SOURCED,1);
 assert.equal(result.full2024And2025TargetYearCensusesAudited,0);
 assert.equal(result.independentlyValidatedTradingCases,0);
 assert.equal(result.approvedRaasCalibrations,0);
 assert.equal(result.approvedOptimalWindow,null);
 assert.ok(result.rows.every(x=>!x.eligibleHistoricalTradingCase&&!x.approvedRaasMetric));
 const repl=result.rows.find(x=>x.ticker==="REPL");
 assert.equal(repl.originalPublicGoalDate,"2025-07-22");
 assert.equal(repl.plannedEntryDate,"2025-05-04");
 assert.equal(repl.plannedExitDate,"2025-07-08");
 assert.equal(repl.status,"EXCLUDED_PHASE3_CONFIRMATORY_ENROLLING_AT_ENTRY");
 const bhvn=result.rows.find(x=>x.ticker==="BHVN");
 assert.equal(bhvn.originalPublicGoalDate,null);
 assert.equal(bhvn.plannedEntryDate,null);
 assert.equal(bhvn.status,"BLOCKED_EXACT_FIRST_PUBLIC_PDUFA_GOAL_NOT_YET_SOURCED");
});
test("Unknown exact target date cannot be invented by using FDA decision day",()=>{
 const x=fixture();x.extras.records.find(r=>r.ticker==="BHVN").firstPublicExactPdufaTargetDate="2025-11-04";
 assert.throws(()=>build(x),/BHVN_NOT_EXACT_PUBLIC_GOAL/);
});
test("REPL Phase 3 readout cannot be promoted or backdated into original IGNYTE Phase 1/2 BLA",()=>{
 for(const mutate of [
  r=>{r.primaryPivotalStudyPhase="PHASE_3"},
  r=>{r.preEntryConfirmatoryPhase3Status="COMPLETED"},
  r=>{r.relevantPhase3ReadoutPublicAtPlannedEntry=true},
  r=>{r.firstPublicExactPdufaTargetDate="2025-07-21"},
  r=>{r.actualFdaActionDate="2025-07-22"}
 ]){const x=fixture();mutate(x.extras.records.find(r=>r.ticker==="REPL"));
  assert.throws(()=>build(x),/REPL_PHASE3_AND_FDA_ASOF_NOT_VERIFIED/);}
});
test("Reject archived CRL outcome as entry-time approval or duplicate issuer in research",()=>{
 const x=fixture();x.extras.records.find(r=>r.ticker==="REPL").actualOutcomeRetrospective="APPROVED";
 assert.throws(()=>build(x),/EXTRA_CRL_EVIDENCE_UNTRUSTED/);
 const y=fixture();y.primary.records.push({...y.primary.records[0],ticker:"BHVN",caseId:"BHVN|duplicate"});
 y.audit.rows.push({...y.audit.rows[0],ticker:"BHVN",caseId:"BHVN|duplicate"});
 y.audit.sourceCaseCount++;
 assert.throws(()=>build(y),/DUPLICATE_REVIEW|EXTRA_CRL_EVIDENCE_UNTRUSTED/);
});
test("Prior ALDX market-cap exclusion and CAPR late Phase 3 are immutable review gates",()=>{
 const x=fixture();x.previous.rows[0].capResearchMillions=301;
 assert.throws(()=>build(x),/ALDX_CAP_NOT_EXCLUDED/);
 const y=fixture();y.previous.rows[1].status="UNVALIDATED_ALPACA_PRICE_RESEARCH";
 assert.throws(()=>build(y),/CAPR_EARLY_PHASE3_NOT_EXCLUDED/);
});
test("CSV exports thirteen rows with real numerics and spreadsheet injection protection",()=>{
 const x=build(fixture()),text=csv(x);
 assert.equal(text.trim().split("\n").length,14);
 assert.ok(text.includes('284.05'));
 x.rows[0].ticker='=HYPERLINK("https://bad.example","open")';
 assert.ok(csv(x).includes("'=HYPERLINK"));
 x.rows[0].provisionalEntryCapResearchMillions="=2*2";
 assert.throws(()=>csv(x),/NUMERIC_EXPORT_UNSAFE/);
});
