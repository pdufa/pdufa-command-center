#!/usr/bin/env node
"use strict";
/**
 * Build an audit worklist for the 2024–2025 PDUFA target-year study.
 * FDA *action years* are NOT PDUFA target years. A supplementary approval
 * or archived CRL is not a fully sourced Phase 3 / publicly traded event.
 *
 * Keep EVERY official action lead in the queue. Put the two original
 * PDUFA source cases and the archival candidates in separate review tiers,
 * and refuse to promote ANY row into a validated trade or RAAS metric.
 */
const fs=require("node:fs"),path=require("node:path");
const {discoveryQueue,verifyConfig,reviewIntake}=
 require("./raas_active_two_year_study.cjs");
const {rows:csvRows,norm}=require("./raas_match_fda_2016_2019_sponsors.cjs");
const root=path.resolve(__dirname,"..");
const FILES={
 study:"new-platform/frontend/data/raas-active-study-config.json",
 intake:"new-platform/frontend/data/raas-active-2024-2025-pdufa-intake.json",
 known:"new-platform/frontend/data/raas-active-2024-2025-primary-source-leads.json",
 archive:"data/historical_assessed_decisions.csv",
 registry:"data/company_registry.csv"
};
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const yearOf=s=>Number(String(s||"").slice(0,4));
const date=s=>typeof s==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 !Number.isNaN(Date.parse(s+"T00:00:00Z"))&&new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const official=s=>typeof s==="string"&&/^https:\/\//.test(s);
function sponsorIndex(registryCsv){
 const entries=csvRows(registryCsv),byName=new Map();
 for(const x of entries){
  if(x.status!=="OK"||!/^[A-Z][A-Z0-9.-]{0,11}$/.test(x.ticker||""))continue;
  const n=norm(x.company);
  if(!n)continue;
  if(!byName.has(n))byName.set(n,new Set());
  byName.get(n).add(x.ticker);
 }
 return byName;
}
function validateFDA(out,config){
 verifyConfig(config);
 if(out?.scope!=="RAAS_ACTIVE_2024_2025_OFFICIAL_FDA_ACTION_DISCOVERY_NOT_CENSUS"||
  out.status!=="SOURCE_DISCOVERY_COMPLETE_FOR_OFFICIAL_ENDPOINTS_NOT_PDUFA_DENOMINATOR"||
  JSON.stringify(out.studyYears)!=="[2024,2025]"||
  out.actionYearIsNotPdufaTargetYear!==true||
  out.fullFDAEventCensusYearsAudited!==0||
  out.approvedHistoricalTrades!==0||out.approvedRaasCalibrations!==0||
  !Array.isArray(out.approvalActionLeads)||!Array.isArray(out.crlLetterLeads)||
  !Array.isArray(out.originalSourceLeadsCrosscheck)||
  !Array.isArray(out.years)||out.years.length!==2)
  throw Error("RAAS_TWO_YEAR_OFFICIAL_FDA_RESULT_INVALID");
 const byYear=new Map();
 for(const y of out.years){
  if(!config.years.includes(y.year)||byYear.has(y.year)||
   y.completePdufaEventCensus!==false||y.approvedHistoricalTrades!==0||
   y.calibratedRaasMetrics!==0||!Number.isInteger(y.totalFdaApprovalActionLeads)||
   !Number.isInteger(y.archivedCRLLetterLeads))
   throw Error("RAAS_TWO_YEAR_FDA_YEAR_INVALID");
  byYear.set(y.year,y);
 }
 if(byYear.size!==2)throw Error("RAAS_TWO_YEAR_FDA_YEAR_COVERAGE_INVALID");
 const seen=new Set();
 for(const a of out.approvalActionLeads){
  if(!a||seen.has(a.id)||!date(a.actualApprovalDate)||
   !config.years.includes(a.year)||yearOf(a.actualApprovalDate)!==a.year||
   !["ORIG","SUPPL"].includes(a.submissionType)||
   !/^(NDA|BLA)\d{5,6}$/.test(a.applicationNumber)||
   a.id!==[a.applicationNumber,a.submissionType,a.submissionNumber,a.actualApprovalDate].join("|")||
   a.status!=="FDA_APPROVAL_ACTION_DISCOVERY_ONLY"||
   a.approvedHistoricalTrade!==false||a.approvedRaasGrade!==false||
   a.contemporaneousPdufaTargetDate!==null)
   throw Error("RAAS_TWO_YEAR_FDA_APPROVAL_UNTRUSTED");
  seen.add(a.id);
 }
 for(const c of out.crlLetterLeads){
  if(!c||!date(c.letterDate)||!config.years.includes(yearOf(c.letterDate))||
   c.actualFdaActionType!=="CRL"||c.eligibleForRaasCalibration!==false||
   c.preDecisionInformationEligible!==false||
   c.originalPdufaTargetDate!==null||c.originalPublicCRLDisclosureDate!==null)
   throw Error("RAAS_TWO_YEAR_FDA_CRL_UNTRUSTED");
 }
 for(const y of config.years){
  const row=byYear.get(y);
  if(out.approvalActionLeads.filter(a=>a.year===y).length!==row.totalFdaApprovalActionLeads||
   out.crlLetterLeads.filter(a=>yearOf(a.letterDate)===y).length!==row.archivedCRLLetterLeads)
   throw Error("RAAS_TWO_YEAR_FDA_ACTION_COUNTS_MISMATCH");
 }
 return out;
}
function build({discovery,config,archiveCsv,known,intake,registryCsv}){
 validateFDA(discovery,config);
 const check=reviewIntake(intake,config);
 if(check.accepted.length!==0||check.rejected.length!==0||
  check.complete||check.years.some(x=>x.complete)||
  known?.scope!=="RAAS_HISTORICAL_PRIMARY_PDUFA_EVENT_EVIDENCE_RESEARCH"||
  !Array.isArray(known.records))
  throw Error("RAAS_TWO_YEAR_UNAPPROVED_INTAKE_OR_SOURCE_INVALID");
 const archive=discoveryQueue(archiveCsv,config);
 const index=sponsorIndex(registryCsv);
 const officialByApp=new Map();
 for(const a of discovery.approvalActionLeads){
  if(!officialByApp.has(a.applicationNumber))officialByApp.set(a.applicationNumber,[]);
  officialByApp.get(a.applicationNumber).push(a);
 }
 const reviewRows=[];
 for(const lead of known.records){
  if(!date(lead.pdufaTargetDate)||!config.years.includes(yearOf(lead.pdufaTargetDate))||
   lead.reviewStatus!=="SOURCE_LEADS_RESEARCH_ONLY"||
   !official(lead.targetAnnouncementSourceUrl)||!official(lead.phase3ReadoutSourceUrl)||
   !official(lead.actualFDAActionSourceUrl)||!date(lead.actualFDAActionDate))
   throw Error("RAAS_TWO_YEAR_ORIGINAL_SOURCE_LEAD_INVALID");
  const app=/^(NDA|BLA)\s*(\d{5,6})/.exec(lead.application||"");
  const number=app?app[1]+app[2]:null;
  const officialMatches=(officialByApp.get(number)||[]).filter(a=>
   a.actualApprovalDate===lead.actualFDAActionDate&&(
    !lead.application.includes("/")||(
     a.submissionType==="SUPPL"&&
     Number(a.submissionNumber)===
       Number(/\/S-?0*(\d+)/.exec(lead.application)?.[1]))));
  if(lead.actualFDAOutcome==="APPROVED"&&officialMatches.length!==1)
   throw Error("RAAS_TWO_YEAR_ORIGINAL_FDA_ACTION_NOT_INDEPENDENTLY_MATCHED");
  reviewRows.push({id:"ORIGINAL|"+lead.caseId,year:yearOf(lead.pdufaTargetDate),
   yearBasis:"PUBLICLY_ANNOUNCED_PDUFA_TARGET_YEAR",
   reviewTrack:"ORIGINAL_FDA_AND_ISSUER_SOURCE_LEAD",
   reviewPriority:1,ticker:lead.ticker,caseId:lead.caseId,
   drug:lead.drug,applicationNumber:number,
   originalPublicPdufaTargetDate:lead.pdufaTargetDate,
   firstLocatedTargetAnnouncementDate:lead.targetAnnouncementDate,
   phase3ReadoutFirstLocatedDate:lead.phase3ReadoutDate,
   retrospectiveActionDate:lead.actualFDAActionDate,
   actualOutcome:lead.actualFDAOutcome,
   matchedOfficialApprovalActionIds:officialMatches.map(a=>a.id),
   sourceUrls:[lead.targetAnnouncementSourceUrl,
    lead.phase3ReadoutSourceUrl,lead.actualFDAActionSourceUrl],
   blockers:["FIRST_EVER_PUBLIC_PDUFA_TARGET_CENSUS_NOT_ESTABLISHED",
    "HISTORIC_MARKET_CAP_AND_SEC_SHARE_CONTINUITY_NOT_INDEPENDENTLY_VERIFIED",
    "INDEPENDENT_PRICE_CORPORATE_ACTION_AND_TRANSACTION_COST_AUDIT_MISSING",
    "FULL_2024_2025_FDA_EVENT_DENOMINATOR_NOT_AUDITED"],
   currentStage:"ORIGINAL_SOURCE_FOUND_MARKET_CAP_AND_RETURN_UNVALIDATED",
   historicallyValidatedTrade:false,approvedRaasMetric:false});
 }
 if(reviewRows.length!==2)throw Error("RAAS_TWO_YEAR_EXPECTED_SOURCE_LEADS_MISSING");
 const seenArchive=new Set();
 for(const lead of archive){
  const id="ARCHIVE|"+lead.eventKey+"|"+lead.ticker+"|"+lead.pdufaDate;
  if(seenArchive.has(id))throw Error("RAAS_TWO_YEAR_ARCHIVE_DUPLICATE_KEY");seenArchive.add(id);
  reviewRows.push({id,year:yearOf(lead.pdufaDate),
   yearBasis:"UNVERIFIED_ARCHIVE_PDUFA_TARGET_YEAR",reviewTrack:"ARCHIVE_TARGET_DATE_TO_VERIFY",
   reviewPriority:2,ticker:lead.ticker,eventKey:lead.eventKey,
   originalPublicPdufaTargetDate:null,archiveSuggestedPdufaDate:lead.pdufaDate,
   retrospectiveActionDate:null,actualOutcome:null,sourceUrls:[],
   blockers:["FDA_OR_ISSUER_ORIGINAL_PDUFA_NOTICE_NOT_FOUND",
    "FIRST_PUBLIC_PHASE3_READOUT_NOT_VERIFIED",
    "FDA_REGULATORY_REVIEW_CYCLE_AND_OUTCOME_NOT_VERIFIED",
    "FDA_ORIGINAL_OR_CRL_ACTION_MATCH_NOT_PROVEN",
    "US_LISTING_HISTORICAL_MARKET_CAP_PRICE_NOT_VERIFIED"],
   currentStage:"ARCHIVE_UNVERIFIED_DATE",
   historicallyValidatedTrade:false,approvedRaasMetric:false});
 }
 for(const c of discovery.crlLetterLeads){
  const year=yearOf(c.letterDate);
  reviewRows.push({id:"CRL|"+c.caseId,year,yearBasis:"FDA_LETTER_ACTION_YEAR_ONLY",
   reviewTrack:"RETROSPECTIVE_FDA_CRL_LETTER",reviewPriority:3,
   ticker:null,applicationNumber:c.applicationNumber,
   originalPublicPdufaTargetDate:null,retrospectiveActionDate:c.letterDate,
   actualOutcome:"CRL",sourceUrls:[c.sourceUrl],
   blockers:["ACTION_YEAR_IS_NOT_PDUFA_TARGET_YEAR",
    "FIRST_PUBLIC_FDA_CRL_DISCLOSURE_NOT_ESTABLISHED",
    "ORIGINAL_PUBLIC_PDUFA_GOAL_AND_PHASE3_NOT_MATCHED",
    "ISSUER_LISTING_AND_ENTRY_CAP_NOT_VERIFIED"],
   currentStage:"CRL_LETTER_OUTCOME_DISCOVERY_NOT_PREDECISION_EVIDENCE",
   historicallyValidatedTrade:false,approvedRaasMetric:false});
 }
 const stats={currentRegistryExactSingleTickerLeads:0,
  currentRegistryAmbiguousSponsorLeads:0,noRegistrySponsorMatchLeads:0};
 for(const a of discovery.approvalActionLeads){
  const current=[...(index.get(norm(a.sponsorName))||[])].sort();
  if(current.length===1)stats.currentRegistryExactSingleTickerLeads++;
  else if(current.length>1)stats.currentRegistryAmbiguousSponsorLeads++;
  else stats.noRegistrySponsorMatchLeads++;
  reviewRows.push({id:"FDA|"+a.id,year:a.year,
   yearBasis:"FDA_APPROVAL_ACTION_YEAR_ONLY",
   reviewTrack:a.submissionType==="ORIG"?
    "FDA_ORIGINAL_APPROVAL_ACTION":"FDA_SUPPLEMENTAL_APPROVAL_ACTION",
   reviewPriority:a.submissionType==="ORIG"?4:5,
   ticker:null,applicationNumber:a.applicationNumber,
   preliminaryPresentDayTickerNameLead:current.length===1?current[0]:null,
   presentDayTickerIsNotHistoricalListingProof:true,
   originalPublicPdufaTargetDate:null,
   retrospectiveActionDate:a.actualApprovalDate,actualOutcome:"APPROVED",
   sourceUrls:[a.sourceUrl],
   blockers:["ACTION_YEAR_IS_NOT_PDUFA_TARGET_YEAR",
    "IS_THIS_FDA_SUBMISSION_A_PHASE3_PDUFA_PROGRAM_UNVERIFIED",
    "FIRST_PUBLIC_PDUFA_NOTICE_NOT_ESTABLISHED",
    "HISTORIC_ISSUER_RIGHTS_US_LISTING_AND_ENTRY_CAP_UNVERIFIED"],
   currentStage:"FDA_APPROVAL_ACTION_DISCOVERY_NOT_ELIGIBLE_TRADE",
   historicallyValidatedTrade:false,approvedRaasMetric:false});
 }
 reviewRows.sort((a,b)=>a.reviewPriority-b.reviewPriority||
  a.year-b.year||a.id.localeCompare(b.id));
 const counts=Object.fromEntries(config.years.map(year=>[year,{
  originalSourceLeads:reviewRows.filter(r=>r.year===year&&r.reviewPriority===1).length,
  unverifiedArchivePdufaDateLeads:reviewRows.filter(r=>r.year===year&&r.reviewPriority===2).length,
  retrospectiveFDAcrlLettersByActionYear:reviewRows.filter(r=>r.year===year&&r.reviewPriority===3).length,
  originalApprovalActionsByActionYear:reviewRows.filter(r=>r.year===year&&r.reviewPriority===4).length,
  supplementalApprovalActionsByActionYear:reviewRows.filter(r=>r.year===year&&r.reviewPriority===5).length,
  verifiedFullPdufaTargetYearCensus:false,independentlyValidatedHistoricalTrades:0
 }]));
 const total=reviewRows.length;
 if(total!==known.records.length+archive.length+
  discovery.crlLetterLeads.length+discovery.approvalActionLeads.length)
  throw Error("RAAS_TWO_YEAR_REVIEW_QUEUE_COUNT_DRIFT");
 return {schemaVersion:1,scope:"RAAS_ACTIVE_2024_2025_FDA_SOURCE_EVIDENCE_TRIAGE_QUEUE",
  status:"ALL_OFFICIAL_ACTIONS_AND_ARCHIVE_LEADS_QUEUED_NOT_QUALIFIED_TRADES",
  studyYears:[2024,2025],trainingYear:2024,holdoutYear:2025,
  fullYearsAudited:0,validatedHistoricalTradingCases:0,
  approvedRaasCalibrations:0,approvedTradingWindow:null,
  totals:{reviewRows:total,
   originalSourceLeads:known.records.length,
   archiveUnverifiedTargetDateLeads:archive.length,
   FDAApprovalActionLeads:discovery.approvalActionLeads.length,
   FDAArchivedCRLLetterLeads:discovery.crlLetterLeads.length,
   ...stats},
  years:counts,reviewRows,
  caveats:["This worklist combines PDUFA TARGET YEAR for source leads and research archive with FDA ACTION YEAR for retrospective approvals and CRLs. The two year buckets are not a single event denominator.",
   "A present-day company registry name match cannot prove historic US listing, ticker or commercialization rights.",
   "Retrospective supplemental FDA actions include label edits, non-Phase3 changes and unrelated applications; every action remains in the review queue, not a qualifying trial.",
   "The incomplete CRL archive and action-year FDA approval list cannot certify the complete 2024–2025 PDUFA target census.",
   "Do not count FDA actions, 3828 overlapping windows, or archived target rows as independent issuers. The active 2024 training and 2025 issuer-disjoint holdout remain EMPTY.",
   "No validated trade, T-79/T-14 optimal return, or calibrated TOP/BOTTOM RAAS grade follows from this queue."]};
}
function csvForReview(data){
 const fields=["reviewPriority","year","yearBasis","reviewTrack","ticker","caseId","drug",
  "applicationNumber","originalPublicPdufaTargetDate","archiveSuggestedPdufaDate",
  "retrospectiveActionDate","actualOutcome","currentStage","blockers","sourceUrls"];
 const cell=x=>{
  const raw=String(x??"");
  // Quoting a CSV cell alone does NOT neutralize formulas in spreadsheets.
  // Preserve the original text, but prefix a single apostrophe before
  // strings beginning with = + - @ (including after leading whitespace).
  const unsafe=/^[\s\u0000-\u001f]*[=+\-@]/u.test(raw);
  const safe=unsafe?"'"+raw:raw;
  return '"'+safe.replaceAll('"','""')+'"';
 };
 return fields.join(",")+"\n"+
  data.reviewRows.map(r=>fields.map(f=>cell(Array.isArray(r[f])?r[f].join(" | "):r[f])).join(",")).join("\n")+"\n";
}
function main(){
 try{
  const out=process.env.RAAS_ACTIVE_FDA_OUTCOME_DISCOVERY_OUTPUT||
   path.join(root,"raas-active-2024-2025-fda-outcome-discovery.json");
  if(!fs.existsSync(out))throw Error("RAAS_TWO_YEAR_MISSING_LIVE_OFFICIAL_FDA_RESULT");
  const discovered=JSON.parse(fs.readFileSync(out,"utf8"));
  const result=build({discovery:discovered,
   config:JSON.parse(read(FILES.study)),
   intake:JSON.parse(read(FILES.intake)),
   known:JSON.parse(read(FILES.known)),
   archiveCsv:read(FILES.archive),
   registryCsv:read(FILES.registry)});
  const dest=process.env.RAAS_TWO_YEAR_TRIAGE_RESULT||
   path.join(root,"raas-2024-2025-fda-source-review-queue.json");
  const csvPath=process.env.RAAS_TWO_YEAR_TRIAGE_CSV||
   path.join(root,"raas-2024-2025-fda-source-review-queue.csv");
  fs.mkdirSync(path.dirname(dest),{recursive:true});
  fs.mkdirSync(path.dirname(csvPath),{recursive:true});
  fs.writeFileSync(dest,JSON.stringify(result,null,2)+"\n");
  fs.writeFileSync(csvPath,csvForReview(result));
  console.log(JSON.stringify({status:result.status,totals:result.totals,
   years:result.years,fullYearsAudited:0,validatedTrades:0,approvedRaasScores:0}));
  if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
   "### 2024–2025 FDA source/CRL/archival target *triage queue*, no certified trades\n\n"+
   JSON.stringify(result.totals,null,2)+"\n\nAction years and target years MUST NOT be combined as a denominator. 0 RAAS scores.\n");
 }catch(e){
  console.error("RAAS_TWO_YEAR_TRIAGE_FATAL_"+String(e.message||e).replace(/[^A-Z0-9_]/g,"_"));
  process.exitCode=1;
 }
}
if(require.main===module)main();
module.exports={validateFDA,sponsorIndex,build,csvForReview};
