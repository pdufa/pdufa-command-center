#!/usr/bin/env node
"use strict";
/**
 * Deterministic review-order / evidence blockers for the active 2024–2025
 * historical PDUFA study. Never confuse FDA action year with target year,
 * never treat a current-name sponsor match as contemporaneous equity evidence.
 * Worklist rows are NOT independent companies, clinical events or trades.
 */
const fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"..");
const EXPECTED_SCOPE="RAAS_ACTIVE_2024_2025_FDA_SOURCE_EVIDENCE_TRIAGE_QUEUE";
const DATA_DIR="raas-2024-2025";
const TIERS=Object.freeze([
 "1_ORIGINAL_ISSUER_FDA_SOURCE_REQUIRES_MARKET_AUDIT",
 "2_ARCHIVAL_PDUFA_DATE_NEEDS_ORIGINAL_EVIDENCE",
 "3_RETROSPECTIVE_CRL_NEEDS_PDUFA_TARGET",
 "4_ORIGINAL_FDA_APPROVAL_CURRENT_SPONSOR_MATCH",
 "5_SUPPLEMENTAL_FDA_APPROVAL_CURRENT_SPONSOR_MATCH",
 "6_ORIGINAL_FDA_APPROVAL_SPONSOR_UNMATCHED",
 "7_SUPPLEMENTAL_FDA_APPROVAL_SPONSOR_UNMATCHED"
]);
const sourceSafe=s=>typeof s==="string"&&/^https:\/\//.test(s);
function priority(row){
 if(row.reviewPriority===1&&row.reviewTrack==="ORIGINAL_FDA_AND_ISSUER_SOURCE_LEAD")
  return TIERS[0];
 if(row.reviewPriority===2&&row.reviewTrack==="ARCHIVE_TARGET_DATE_TO_VERIFY")
  return TIERS[1];
 if(row.reviewPriority===3&&row.reviewTrack==="RETROSPECTIVE_FDA_CRL_LETTER")
  return TIERS[2];
 if(row.reviewPriority===4&&row.reviewTrack==="FDA_ORIGINAL_APPROVAL_ACTION")
  return row.preliminaryPresentDayTickerNameLead?TIERS[3]:TIERS[5];
 if(row.reviewPriority===5&&row.reviewTrack==="FDA_SUPPLEMENTAL_APPROVAL_ACTION")
  return row.preliminaryPresentDayTickerNameLead?TIERS[4]:TIERS[6];
 throw Error("RAAS_REVIEW_TIER_UNEXPECTED_TRACK");
}
function reviewChecklist(row){
 const base=[
  "Identify original first-public PDUFA goal disclosure and all revisions",
  "Verify Phase 3 trial, readout and full program indication publicly known before entry",
  "Identify publicly traded US-listed rights holder at each entry session",
  "Reconcile timestamped SEC outstanding shares, new financing, warrants and splits",
  "Cross-check independent raw share price and adjusted split/dividend returns",
  "Censor early action; verify original FDA letter and first-public outcome timing"
 ];
 if(row.reviewPriority===1)return base.slice(2).concat([
  "Verify complete two-year target-year approval, CRL, extension, withdrawal census"
 ]);
 if(row.reviewPriority===2)return base;
 if(row.reviewPriority===3)return [
  "Determine original PDUFA target YEAR; CRL letter ACTION YEAR is not target year",
  "Check first public disclosure of CRL separately from retrospective PDF publication",
  ...base
 ];
 return [
  "Determine whether FDA approval action represents a Phase 3 PDUFA review, not merely a label update",
  "Establish historical ticker and regulatory commercial-rights ownership; current sponsor name alone insufficient",
  ...base
 ];
}
function csvEscape(x){
 const raw=String(x??"");
 const safe=/^[\s\u0000-\u001f]*[=+\-@]/u.test(raw)?"'"+raw:raw;
 return '"'+safe.replaceAll('"','""')+'"';
}
function build(queue){
 if(!queue||queue.scope!==EXPECTED_SCOPE||
  queue.status!=="ALL_OFFICIAL_ACTIONS_AND_ARCHIVE_LEADS_QUEUED_NOT_QUALIFIED_TRADES"||
  JSON.stringify(queue.studyYears)!=="[2024,2025]"||
  !Array.isArray(queue.reviewRows)||queue.reviewRows.length===0||
  queue.fullYearsAudited!==0||queue.validatedHistoricalTradingCases!==0||
  queue.approvedRaasCalibrations!==0||queue.approvedTradingWindow!==null||
  queue.totals?.reviewRows!==queue.reviewRows.length)
  throw Error("RAAS_PRIORITIZATION_INVALID_INCOMPLETE_STUDY");
 const seen=new Set(),rows=[];
 for(const r of queue.reviewRows){
  if(!r||typeof r.id!=="string"||seen.has(r.id)||
   ![2024,2025].includes(r.year)||!Array.isArray(r.blockers)||!r.blockers.length||
   r.historicallyValidatedTrade!==false||r.approvedRaasMetric!==false||
   !Number.isInteger(r.reviewPriority)||r.reviewPriority<1||r.reviewPriority>5||
   !Array.isArray(r.sourceUrls)||r.sourceUrls.some(x=>!sourceSafe(x)))
   throw Error("RAAS_PRIORITIZATION_UNTRUSTED_RESEARCH_ROW");
  const tier=priority(r);
  seen.add(r.id);
  rows.push({
   reviewId:r.id,tier,priority:+tier.charAt(0),
   originalReviewTrack:r.reviewTrack,studyBucketYear:r.year,
   yearBasis:r.yearBasis,
   pdufaTargetFirstPublic:r.originalPublicPdufaTargetDate??null,
   archiveUnverifiedPdufaDate:r.archiveSuggestedPdufaDate??null,
   retrospectiveFdaActionDate:r.retrospectiveActionDate??null,
   applicationNumber:r.applicationNumber??null,
   caseId:r.caseId??null,
   originalKnownTicker:r.reviewPriority===1?r.ticker:null,
   archiveSuggestedTicker:r.reviewPriority===2?r.ticker:null,
   presentDayRegistryTickerLead:r.preliminaryPresentDayTickerNameLead??null,
   historicalIssuerListingConfirmed:false,
   originalPdufaCensusVerified:false,
   outcomePublicDateVerified:false,
   historicalCap300mTo10bConfirmed:false,
   splitAdjustedReturnsIndependentlyVerified:false,
   clinicalPhase3EligibilityConfirmed:false,
   eligibleForScoring:false,validatedTradingCase:false,
   evidenceBlockers:r.blockers,
   reviewerChecks:reviewChecklist(r),
   originalSourceLinks:r.sourceUrls
  });
 }
 rows.sort((a,b)=>a.priority-b.priority||
  a.studyBucketYear-b.studyBucketYear||
  a.reviewId.localeCompare(b.reviewId));
 const tierCounts=Object.fromEntries(TIERS.map(t=>[t,rows.filter(r=>r.tier===t).length]));
 const n=Object.values(tierCounts).reduce((a,b)=>a+b,0);
 if(n!==queue.totals.reviewRows||
  tierCounts[TIERS[0]]!==queue.totals.originalSourceLeads||
  tierCounts[TIERS[1]]!==queue.totals.archiveUnverifiedTargetDateLeads||
  tierCounts[TIERS[2]]!==queue.totals.FDAArchivedCRLLetterLeads||
  tierCounts[TIERS[3]]+tierCounts[TIERS[5]]+
   tierCounts[TIERS[4]]+tierCounts[TIERS[6]]!==queue.totals.FDAApprovalActionLeads)
  throw Error("RAAS_PRIORITIZATION_LOST_OFFICIAL_ACTIONS");
 const yearBasisCounts={};
 for(const row of rows){
  const key=row.yearBasis+"|"+row.studyBucketYear;
  yearBasisCounts[key]=(yearBasisCounts[key]||0)+1;
 }
 return {schemaVersion:1,scope:"RAAS_ACTIVE_2024_2025_EVIDENCE_FIRST_REVIEW_ORDER",
  status:"SOURCE_EVIDENCE_REVIEW_QUEUE_NOT_VALIDATED",
  studyYears:[2024,2025],trainingYear:2024,holdoutYear:2025,
  totalTasks:rows.length,tiers:tierCounts,yearBasisCounts,
  fullPdufaTargetYearsAudited:0,independentlyValidatedTradingCases:0,
  approvedRaasMetrics:0,declaredBestTradingWindow:null,
  independentIssuersForTrain:0,independentIssuersForHoldout:0,
  topTwenty:rows.slice(0,20).map(x=>({id:x.reviewId,tier:x.tier,year:x.studyBucketYear,
   ticker:x.originalKnownTicker||x.archiveSuggestedTicker||x.presentDayRegistryTickerLead,
   evidenceBlockers:x.evidenceBlockers})),
  reviewRows:rows,
  caveats:[
   "Tiers schedule EVIDENCE RESEARCH, not predicted profitable PDUFA trades.",
   "FDA original/supplemental action-year counts and historical PDUFA target-year counts are not one denominator.",
   "Current sponsor name / ticker registry matches never establish historical common-stock listing, rights or market cap.",
   "Source-backed program rows and archival leads may refer to the same regulatory cycle; they must not be counted as separate independent issuers.",
   "The 2024–2025 PDUFA census, the required 30/30 issuer-disjoint holdout and all 60 metric calibrations remain unverified."
  ]};
}
function csvForReview(result){
 const fields=["priority","tier","studyBucketYear","yearBasis","reviewId",
  "originalKnownTicker","archiveSuggestedTicker","presentDayRegistryTickerLead",
  "applicationNumber","caseId","pdufaTargetFirstPublic","archiveUnverifiedPdufaDate",
  "retrospectiveFdaActionDate","evidenceBlockers","reviewerChecks","originalSourceLinks"];
 return fields.join(",")+"\n"+result.reviewRows.map(row=>
  fields.map(k=>csvEscape(Array.isArray(row[k])?row[k].join(" | "):row[k])).join(",")
 ).join("\n")+"\n";
}
function main(){
 try{
  const src=process.env.RAAS_TWO_YEAR_TRIAGE_RESULT||
   path.join(root,DATA_DIR+"-fda-source-review-queue.json");
  const json=process.env.RAAS_REVIEW_PRIORITY_JSON||
   path.join(root,DATA_DIR+"-prioritized-review.json");
  const csv=process.env.RAAS_REVIEW_PRIORITY_CSV||
   path.join(root,DATA_DIR+"-prioritized-review.csv");
  const result=build(JSON.parse(fs.readFileSync(src,"utf8")));
  for(const file of [json,csv])fs.mkdirSync(path.dirname(file),{recursive:true});
  fs.writeFileSync(json,JSON.stringify(result,null,2)+"\n");
  fs.writeFileSync(csv,csvForReview(result));
  console.log(JSON.stringify({status:result.status,total:result.totalTasks,
   tiers:result.tiers,years:result.yearBasisCounts,
   validatedTradingCases:result.independentlyValidatedTradingCases,
   approvedRaasMetrics:result.approvedRaasMetrics}));
  if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(
   process.env.GITHUB_STEP_SUMMARY,"### Active 2024–25 prioritized original FDA source audit\n\n"+
   JSON.stringify(result.tiers,null,2)+"\n\n"+
   "0 independently validated trades, 0 approved RAAS metric scores. No complete PDUFA target year census.\n");
 }catch(e){
  console.error("RAAS_REVIEW_PRIORITY_FATAL_"+String(e.message||e).replace(/[^A-Z0-9_]/g,"_"));
  process.exitCode=1;
 }
}
if(require.main===module)main();
module.exports={priority,reviewChecklist,csvEscape,build,csvForReview};
