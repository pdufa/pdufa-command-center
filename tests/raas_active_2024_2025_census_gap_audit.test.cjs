"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const config=require("../new-platform/frontend/data/raas-active-study-config.json");
const primary=require("../new-platform/frontend/data/raas-active-2024-2025-primary-source-leads.json");
const {build,csv,safeCsv}=require("../scripts/raas_active_2024_2025_census_gap_audit.cjs");
function fixture(){
 const originals=primary.records.map(e=>({
  id:"ORIGINAL|"+e.caseId,caseId:e.caseId,ticker:e.ticker,
  year:+e.pdufaTargetDate.slice(0,4),
  yearBasis:"PUBLICLY_ANNOUNCED_PDUFA_TARGET_YEAR",
  reviewTrack:"ORIGINAL_FDA_AND_ISSUER_SOURCE_LEAD",reviewPriority:1,
  originalPublicPdufaTargetDate:e.pdufaTargetDate,
  retrospectiveActionDate:e.actualFDAActionDate,actualOutcome:e.actualFDAOutcome,
  blockers:["FULL_YEAR_CENSUS_NOT_AUDITED"],
  historicallyValidatedTrade:false,approvedRaasMetric:false
 }));
 const a=[
  ["GERN","2024-06-16"], // same known source, not an independent event
  ["MDGL","2024-03-14"], // same known source, not an independent event
  ["SNDX","2024-08-28"],
  ["SNDX","2024-12-26"], // different target, same issuer
  ["BBIO","2024-11-29"],
  ["BCRX","2025-12-12"],
  ["CAPR","2025-08-31"],
  ["SRRK","2024-09-01"], // same ticker across train and holdout candidate years
 ];
 const archive=a.map(([ticker,dt],i)=>({
  id:"ARCHIVE|"+i+"|"+ticker+"|"+dt,year:+dt.slice(0,4),
  yearBasis:"UNVERIFIED_ARCHIVE_PDUFA_TARGET_YEAR",
  reviewTrack:"ARCHIVE_TARGET_DATE_TO_VERIFY",reviewPriority:2,
  ticker,originalPublicPdufaTargetDate:null,archiveSuggestedPdufaDate:dt,
  blockers:["FIRST_PUBLIC_PDUFA_NOT_VERIFIED"],
  historicallyValidatedTrade:false,approvedRaasMetric:false
 }));
 const fda=[{
  id:"FDA|NDA999999|ORIG|1|2024-09-15",year:2024,reviewTrack:"FDA_ORIGINAL_APPROVAL_ACTION",
  yearBasis:"FDA_APPROVAL_ACTION_YEAR_ONLY",blockers:["FDA_ACTION_NOT_TARGET"],
  historicallyValidatedTrade:false,approvedRaasMetric:false
 }];
 const crl=[{
  id:"CRL|BLA999999|2025-06-01",year:2025,reviewTrack:"RETROSPECTIVE_FDA_CRL_LETTER",
  yearBasis:"FDA_LETTER_ACTION_YEAR_ONLY",blockers:["FDA_ACTION_NOT_TARGET"],
  historicallyValidatedTrade:false,approvedRaasMetric:false
 }];
 const rows=[...originals,...archive,...fda,...crl];
 return {scope:"RAAS_ACTIVE_2024_2025_FDA_SOURCE_EVIDENCE_TRIAGE_QUEUE",
  status:"ALL_OFFICIAL_ACTIONS_AND_ARCHIVE_LEADS_QUEUED_NOT_QUALIFIED_TRADES",
  studyYears:[2024,2025],fullYearsAudited:0,validatedHistoricalTradingCases:0,
  approvedRaasCalibrations:0,approvedTradingWindow:null,
  totals:{reviewRows:rows.length,originalSourceLeads:originals.length,
   archiveUnverifiedTargetDateLeads:archive.length,FDAApprovalActionLeads:1,
   FDAArchivedCRLLetterLeads:1},reviewRows:rows};
}
const make=changes=>build({queue:fixture(),config,primary,...changes});
test("2024/2025 target year counts exclude action year and already-sourced goal duplicates",()=>{
 const x=make();
 assert.equal(x.originalEventSourceCount,primary.records.length);
 assert.equal(x.queueSourceActionRows,17);
 assert.equal(x.fdaRetrospectiveApprovalActionRows,1);
 assert.equal(x.fdaRetrospectiveCRLLetterRows,1);
 assert.equal(x.actionYearRowsNotCountedAsTargetYearDenominator,2);
 assert.equal(x.archivedTargetDateLeadRows,8);
 assert.equal(x.archiveSameGoalDuplicatedSourceRows,2);
 assert.equal(x.unsourcedArchivedTargetReviewTasks,6);
 assert.deepEqual(x.previouslySourcedArchiveOverlaps.map(r=>r.ticker),["GERN","MDGL"]);
 assert.equal(x.annualTargetsAudited,0);
 assert.equal(x.independentlyValidatedTradingCases,0);
 assert.equal(x.calibratedRaasMetrics,0);
 assert.equal(x.approvedOptimalWindow,null);
});
test("Separate event dates for same ticker remain reviews but only one issuer slot",()=>{
 const x=make();
 assert.equal(x.byTargetYear[2024].sourceBackedTargetEvents,4);
 assert.equal(x.byTargetYear[2024].archivedTargetDateRows,6);
 assert.equal(x.byTargetYear[2024].archiveRowsAlreadySameGoalSourced,2);
 assert.equal(x.byTargetYear[2024].archivedUnverifiedDateRows,4);
 assert.equal(x.byTargetYear[2024].newCandidateTickerNamesNotYetSourceBacked,2);
 assert.equal(x.byTargetYear[2024].bestCaseDistinctTickerNamesInCurrentlyLocatedTargetQueue,6);
 assert.equal(x.byTargetYear[2024].minimumAdditionalIssuerDiscoveryBeyondCurrentTargetQueue,24);
 assert.equal(x.byTargetYear[2025].sourceBackedTargetEvents,3);
 assert.equal(x.byTargetYear[2025].archivedUnverifiedDateRows,2);
 assert.equal(x.byTargetYear[2025].newCandidateTickerNamesNotYetSourceBacked,2);
 assert.equal(x.byTargetYear[2025].bestCaseDistinctTickerNamesInCurrentlyLocatedTargetQueue,5);
 assert.equal(x.byTargetYear[2025].minimumAdditionalIssuerDiscoveryBeyondCurrentTargetQueue,25);
 const s=x.sameYearMultipleGoalSameTicker.find(r=>r.ticker==="SNDX");
 assert.deepEqual(s.suggestedDistinctTargetDates,["2024-08-28","2024-12-26"]);
 assert.equal(s.independentIssuerSlotsAllowed,1);
 assert.deepEqual(x.acrossYearCandidateTickerConflicts,["SRRK"]);
 assert.equal(x.nextArchivedTargetSourceReviews[0].year,2025);
 assert.ok(x.nextArchivedTargetSourceReviews.every(r=>!r.eligibleForTrading&&!r.validatedRaasScore));
});
test("Missing official FDA source, tampered intake, partial rows or false calibrated claims fail closed",()=>{
 const q=fixture();q.reviewRows.pop();
 assert.throws(()=>make({queue:q}),/STUDY_OR_QUEUE_INVALID/);
 const a=fixture();a.validatedHistoricalTradingCases=1;
 assert.throws(()=>make({queue:a}),/STUDY_OR_QUEUE_INVALID/);
 const b=fixture();b.reviewRows[0].actualOutcome="CRL"===b.reviewRows[0].actualOutcome?"APPROVED":"CRL";
 assert.throws(()=>make({queue:b}),/PRIMARY_SOURCE_CROSSWALK_FAILED/);
 const c=fixture();c.reviewRows[primary.records.length].originalPublicPdufaTargetDate="2024-06-16";
 assert.throws(()=>make({queue:c}),/ARCHIVE_IS_NOT_SOURCE_EVIDENCE/);
 const d=fixture();d.reviewRows[0].historicallyValidatedTrade=true;
 assert.throws(()=>make({queue:d}),/UNTRUSTED_REVIEW_ROW/);
 const e=fixture();e.reviewRows[primary.records.length+8].reviewTrack="ORIGINAL_FDA_AND_ISSUER_SOURCE_LEAD";
 assert.throws(()=>make({queue:e}),/SOURCE_OR_ACTION_TOTALS_INVALID/);
 const f=structuredClone(primary);f.records[0].historicalCapitalizationAtEntryVerified=true;
 assert.throws(()=>make({primary:f}),/UNTRUSTED_ORIGINAL_EVENT/);
 const wrong={...config,minimumIndependentHoldoutIssuers:0};
 assert.throws(()=>make({config:wrong}),/STUDY_OR_QUEUE_INVALID/);
});
test("A different archival target date on already sourced ticker is NOT silently discarded",()=>{
 const q=fixture();
 const a=q.reviewRows.find(r=>r.reviewTrack==="ARCHIVE_TARGET_DATE_TO_VERIFY"&&r.ticker==="GERN");
 a.archiveSuggestedPdufaDate="2024-12-06";
 const x=make({queue:q});
 assert.equal(x.archiveSameGoalDuplicatedSourceRows,1);
 const g=x.nextArchivedTargetSourceReviews.find(r=>r.ticker==="GERN");
 assert.equal(g.possibleSameIssuerOtherCycle,true);
 assert.equal(x.byTargetYear[2024].bestCaseDistinctTickerNamesInCurrentlyLocatedTargetQueue,6);
});
test("CSV is formula-injection safe, counts all review tasks, and preserves target dates as text",()=>{
 const r=make();
 const s=csv(r);
 assert.equal(s.trim().split("\n").length,1+r.unsourcedArchivedTargetReviewTasks);
 assert.ok(s.includes("UNVERIFIED_ARCHIVE_PDUFA_TARGET_FOR_SOURCE_RESEARCH"));
 assert.ok(s.includes('"2024-08-28"'));
 assert.equal(safeCsv('=HYPERLINK("https://evil.test","open")'),
  '"\'=HYPERLINK(""https://evil.test"",""open"")"');
 assert.equal(safeCsv(" -2"),'"\' -2"');
 r.nextArchivedTargetSourceReviews[0].ticker="=HYPERLINK(1,2)";
 assert.ok(csv(r).includes("'=HYPERLINK(1,2)"));
 assert.throws(()=>csv({scope:"SOMETHING_ELSE"}),/CSV_SOURCE_INVALID/);
});
