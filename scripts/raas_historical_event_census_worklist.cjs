#!/usr/bin/env node
"use strict";
/** Unified 2016–2025 historical event worklist.
 * 2016–2019 original FDA approvals and 2020–2025 retrospective "event dates"
 * do NOT equal point-in-time PDUFA target announcements. Preserve independent
 * FDA action date separately and expose mismatches, never manufacture trades.
 */
const fs=require("node:fs"),path=require("node:path");
const {rows}=require("./raas_match_fda_2016_2019_sponsors.cjs");
const root=path.resolve(__dirname,"..");
const day=x=>typeof x==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&
 !Number.isNaN(Date.parse(x+"T00:00:00Z"))&&new Date(x+"T00:00:00Z").toISOString().slice(0,10)===x;
const url=x=>typeof x==="string"&&/^https:\/\/[^\s/]+\.[^\s/]+/i.test(x);
const YEARS=Array.from({length:10},(_,i)=>2016+i);
function validateSourceLeads(input) {
 if(!input||input.scope!=="RAAS_HISTORICAL_PRIMARY_PDUFA_EVENT_EVIDENCE_RESEARCH"||
  input.schemaVersion!==1||!Array.isArray(input.records))throw Error("RAAS_PRIMARY_EVENT_SOURCE_INVALID");
 const seen=new Set(),out=[];
 for(const r of input.records) {
  if(!r||!r.caseId||seen.has(r.caseId)||!r.programId||
   !/^[A-Z][A-Z0-9.-]{0,11}$/.test(r.ticker||"")||
   !Array.isArray(r.nctIds)||!r.nctIds.length||r.nctIds.some(x=>!/^NCT\d{8}$/.test(x))||
   !day(r.pdufaTargetDate)||!day(r.targetAnnouncementDate)||
   !day(r.phase3ReadoutDate)||!day(r.actualFDAActionDate)||
   r.targetAnnouncementDate>=r.pdufaTargetDate ||
   r.phase3ReadoutDate>=r.pdufaTargetDate||
   !url(r.targetAnnouncementSourceUrl)||!url(r.phase3ReadoutSourceUrl)||
   !url(r.actualFDAActionSourceUrl)||!url(r.nctSourceUrl)||
   !url(r.contemporaneousTradingListingSourceUrl)||
   !r.firstLocatedNotFirstEverPublicDisclosure||
   r.historicalCapitalizationAtEntryVerified!==false||
   r.reviewStatus!=="SOURCE_LEADS_RESEARCH_ONLY"||
   !YEARS.includes(+r.pdufaTargetDate.slice(0,4)))
   throw Error("RAAS_PRIMARY_EVENT_SOURCE_INVALID");
  seen.add(r.caseId);
  out.push(r);
 }
 return out;
}
function parseArchive(csv){
 const raw=rows(csv);
 const out=[],seen=new Set();
 for(const r of raw){
  const k=r.event_key,t=r.ticker,d=r.pdufa_date;
  if(!k||!t||!/^[A-Z][A-Z0-9.-]{0,11}$/.test(t)||!day(d)||
   d<"2016-01-01"||d>"2025-12-31"||seen.has(k))continue;
  seen.add(k);
  out.push({source:"PRIOR_RETROSPECTIVE_DATE",key:k,ticker:t,
   archiveDate:d,claimedOutcome:r.actual_outcome||null,
   status:"UNVERIFIED_HISTORICAL_TARGET_DATE",sourceUrl:null});
 }
 return out;
}
function consolidate(input){
 const archive=parseArchive(input.archiveCsv);
 const leads=validateSourceLeads(input.primaryLeads);
 if(!input.approvalDiscovery ||
  input.approvalDiscovery.scope!=="FDA_DRUGS_AT_FDA_2016_2019_APPROVAL_DISCOVERY_NOT_PDUFA_CENSUS"||
  !Array.isArray(input.approvalDiscovery.candidates))throw Error("RAAS_FDA_ARCHIVE_INVALID");
 const leadByArchive=new Map();
 for(const r of leads){
  if(r.archivedEventKey && !leadByArchive.has(r.archivedEventKey))
   leadByArchive.set(r.archivedEventKey,r);
 }
 const candidates=[];
 for(const a of archive){
  const matched=leadByArchive.get(a.key);
  candidates.push({...a,
   primarySourceCaseId:matched?.caseId??null,
   pdufaTargetDate:matched?.pdufaTargetDate??null,
   firstLocatedTargetDisclosureDate:matched?.targetAnnouncementDate??null,
   actualFDAActionDate:matched?.actualFDAActionDate??null,
   actualOutcome:matched?.actualFDAOutcome??null,
   archiveDateMatchesTarget:matched?a.archiveDate===matched.pdufaTargetDate:null,
   archiveDateMatchesAction:matched?a.archiveDate===matched.actualFDAActionDate:null,
   targetEvidenceUrl:matched?.targetAnnouncementSourceUrl??null,
   phase3EvidenceUrl:matched?.phase3ReadoutSourceUrl??null,
   actionEvidenceUrl:matched?.actualFDAActionSourceUrl??null,
   nctIds:matched?.nctIds??[],
   historicalMarketCapAtEntryVerified:false,
   needsIssuerReview:!matched?.contemporaneousTradingListingSourceUrl,
   eligibleForCalibration:false,
   remainingGates:["FIRST_EVER_PUBLIC_PDUFA_DATE_AUDIT","EXACT_ENTRY_DAY_MARKET_CAP","EARLY_ACTION_CENSOR","RELEVANT_PROGRAM_IDENTITY","FULL_YEAR_OUTCOME_CENSUS","PROSPECTIVE_RATING_HISTORY"]});
 }
 const sourceOrphans=leads.filter(r=>!archive.some(a=>a.key===r.archivedEventKey));
 for(const c of input.approvalDiscovery.candidates) {
  if(!c||c.status!=="FDA_APPROVAL_DISCOVERY_ONLY"||!day(c.actualApprovalDate)||
   +c.actualApprovalDate.slice(0,4)<2016||+c.actualApprovalDate.slice(0,4)>2019||
   !url(c.fdaRecordUrl))throw Error("RAAS_FDA_ARCHIVE_INVALID");
  candidates.push({source:"FDA_ORIGINAL_APPROVAL_DISCOVERY",key:c.id,
   ticker:null,archiveDate:null,actualFDAActionDate:c.actualApprovalDate,
   application:c.applicationNumber,sponsor:c.sponsorName,
   pdufaTargetDate:null,firstLocatedTargetDisclosureDate:null,
   targetEvidenceUrl:null,actionEvidenceUrl:c.fdaRecordUrl,
   actualOutcome:"APPROVED",nctIds:[],
   historicalMarketCapAtEntryVerified:false,
   eligibleForCalibration:false,status:"NOT_PDUFA_EVENT_ISSUER_UNVERIFIED",
   remainingGates:["PUBLIC_COMPANY_IDENTITY","PDUFA_DATE_ORIGINAL_PUBLICATION","PHASE3_READOUT_PUBLICATION",
    "HISTORICAL_MARKET_CAP","CRL_AND_EXTENSION_DENOMINATOR"]});
 }
 for(const r of sourceOrphans)candidates.push({source:"LOCATED_PRIMARY_SOURCES_NO_ARCHIVE_JOIN",
  key:r.caseId,ticker:r.ticker,archiveDate:null,pdufaTargetDate:r.pdufaTargetDate,
  actualFDAActionDate:r.actualFDAActionDate,firstLocatedTargetDisclosureDate:r.targetAnnouncementDate,
  targetEvidenceUrl:r.targetAnnouncementSourceUrl,actionEvidenceUrl:r.actualFDAActionSourceUrl,
  nctIds:r.nctIds,historicalMarketCapAtEntryVerified:false,
  eligibleForCalibration:false,status:"NEEDS_ARCHIVE_RECONCILIATION"});
 const mismatches=candidates.filter(c=>c.primarySourceCaseId&&c.archiveDateMatchesTarget===false);
 const coverage=Object.fromEntries(YEARS.map(y=>[y,{sourceLeads:leads.filter(r=>+r.pdufaTargetDate.slice(0,4)===y).length,
  archiveCandidates:archive.filter(r=>+r.archiveDate.slice(0,4)===y).length,
  fdaApprovalLeads:candidates.filter(r=>r.source==="FDA_ORIGINAL_APPROVAL_DISCOVERY"&&
   +r.actualFDAActionDate.slice(0,4)===y).length,
  completePdufaCensus:false,verifiedHistoricalMarketCaps:0,
  calibratedRaasMetrics:0}]));
 return {scope:"RAAS_2016_2025_HISTORICAL_SOURCE_BACKFILL_WORKLIST",
  status:"INCOMPLETE_RESEARCH_UNIVERSE",
  summary:{archiveCandidates:archive.length,
   fdaApprovalLeads:candidates.filter(c=>c.source==="FDA_ORIGINAL_APPROVAL_DISCOVERY").length,
   primaryTargetSourceLeads:leads.length,
   archiveDateNotTrueTarget:mismatches.length,
   historicallyEligibleTrades:0,
   approvedRaasMetrics:0,
   fullCensusYears:0},
  archiveTargetMismatches:mismatches.map(c=>({key:c.key,ticker:c.ticker,
   previouslyLabeledDate:c.archiveDate,verifiedTargetDate:c.pdufaTargetDate,
   actualActionDate:c.actualFDAActionDate,sourceUrl:c.targetEvidenceUrl})),
  coverage,candidates,
  disclaimers:["FDA action date and announced PDUFA goal date must be held in independent fields.",
    "FDA original approval discovery misses CRLs and withdrawals and does not establish PDUFA market eligibility.",
    "Source records establish located issuer facts but are not complete first-ever public disclosure audits.",
    "No entry-day historical capitalization, adjusted/raw price reconciliation or issuer-disjoint RAAS validation is asserted.",
    "Never publish a numeric RAAS score based on unreviewed event candidates."]};
}
if(require.main===module){
 try{
  const approvalPath=process.env.RAAS_FDA_BACKFILL_OUTPUT||path.join(root,"raas-fda-2016-2019-discovery.json");
  const archiveCsv=fs.readFileSync(path.join(root,"data/historical_assessed_decisions.csv"),"utf8");
  const primaryLeads=JSON.parse(fs.readFileSync(path.join(root,
   "new-platform/frontend/data/raas-historical-2020-primary-source-leads.json"),"utf8"));
  const approvalDiscovery=JSON.parse(fs.readFileSync(approvalPath,"utf8"));
  const result=consolidate({archiveCsv,primaryLeads,approvalDiscovery});
  const output=process.env.RAAS_EVENT_WORKLIST_OUTPUT||path.join(root,"raas-historical-event-worklist.json");
  fs.writeFileSync(output,JSON.stringify(result,null,2)+"\n");
  const summary={status:result.status,...result.summary,archiveTargetMismatches:result.archiveTargetMismatches};
  process.stdout.write(JSON.stringify(summary)+"\n");
  if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
   "### 2016–2025 historical FDA event and PDUFA evidence worklist\n\n"+
   JSON.stringify(summary,null,2)+"\n\nNo metrics auto-approved or trades qualified.\n");
 }catch(e){console.error("RAAS_WORKLIST_FATAL_"+String(e.message));process.exitCode=1;}
}
module.exports={validateSourceLeads,parseArchive,consolidate};
