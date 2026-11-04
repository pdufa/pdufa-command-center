#!/usr/bin/env node
"use strict";
/**
 * Active 2024–2025 PDUFA TARGET-YEAR census gap audit (research only).
 *
 * Treat official FDA APPROVAL / CRL ACTION YEAR, archival suggested PDUFA
 * TARGET YEAR, and original issuer-sourced PDUFA TARGET YEAR as distinct.
 * Reconcile archived ticker+goal pairs already in original evidence; keep
 * separate same-issuer goals as review tasks but NEVER double-count issuer
 * independence. Not a complete FDA census, trading backtest or RAAS score.
 */
const fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"..");
const SRC="RAAS_ACTIVE_2024_2025_FDA_SOURCE_EVIDENCE_TRIAGE_QUEUE";
const OUT="RAAS_ACTIVE_2024_2025_TARGET_CENSUS_GAP_AUDIT";
const day=x=>typeof x==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&
 new Date(x+"T00:00:00Z").toISOString().slice(0,10)===x;
const ticker=x=>typeof x==="string"&&/^[A-Z][A-Z0-9.-]{0,11}$/.test(x);
const key=(t,d)=>t+"|"+d;
function safeCsv(x){
 const s=String(x??"");
 const safe=/^[\s\u0000-\u001f]*[=+\-@]/u.test(s)?"'"+s:s;
 return '"'+safe.replaceAll('"','""')+'"';
}
function build({queue,config,primary,supplemental=[]}={}){
 if(!queue||queue.scope!==SRC||
  queue.status!=="ALL_OFFICIAL_ACTIONS_AND_ARCHIVE_LEADS_QUEUED_NOT_QUALIFIED_TRADES"||
  JSON.stringify(queue.studyYears)!=="[2024,2025]"||
  queue.fullYearsAudited!==0||queue.validatedHistoricalTradingCases!==0||
  queue.approvedRaasCalibrations!==0||queue.approvedTradingWindow!==null||
  !Array.isArray(queue.reviewRows)||queue.totals?.reviewRows!==queue.reviewRows.length||
  config?.scope!=="RAAS_ACTIVE_2024_2025_TWO_YEAR_PDUFA_STUDY"||
  JSON.stringify(config.years)!=="[2024,2025]"||
  config.trainYear!==2024||config.holdoutYear!==2025||
  !Number.isInteger(config.minimumIndependentTrainIssuers)||
  !Number.isInteger(config.minimumIndependentHoldoutIssuers)||
  config.minimumIndependentTrainIssuers<1||config.minimumIndependentHoldoutIssuers<1||
  primary?.scope!=="RAAS_HISTORICAL_PRIMARY_PDUFA_EVENT_EVIDENCE_RESEARCH"||
  !Array.isArray(primary.records)||
  !Number.isInteger(queue.totals.originalSourceLeads)||
  !Number.isInteger(queue.totals.archiveUnverifiedTargetDateLeads)||
  !Number.isInteger(queue.totals.FDAApprovalActionLeads)||
  !Number.isInteger(queue.totals.FDAArchivedCRLLetterLeads)||
  !Array.isArray(supplemental))
  throw Error("RAAS_CENSUS_GAP_STUDY_OR_QUEUE_INVALID");
 const tracks={
  ORIGINAL_FDA_AND_ISSUER_SOURCE_LEAD:[],
  ARCHIVE_TARGET_DATE_TO_VERIFY:[],
  RETROSPECTIVE_FDA_CRL_LETTER:[],
  FDA_ORIGINAL_APPROVAL_ACTION:[],
  FDA_SUPPLEMENTAL_APPROVAL_ACTION:[]
 };
 const seenIds=new Set();
 for(const r of queue.reviewRows){
  if(!r||!Object.hasOwn(tracks,r.reviewTrack)||
   typeof r.id!=="string"||!r.id||seenIds.has(r.id)||
   ![2024,2025].includes(r.year)||
   r.historicallyValidatedTrade!==false||r.approvedRaasMetric!==false||
   !Array.isArray(r.blockers)||r.blockers.length===0)
   throw Error("RAAS_CENSUS_GAP_UNTRUSTED_REVIEW_ROW");
  seenIds.add(r.id);
  tracks[r.reviewTrack].push(r);
 }
 const originals=tracks.ORIGINAL_FDA_AND_ISSUER_SOURCE_LEAD;
 const archived=tracks.ARCHIVE_TARGET_DATE_TO_VERIFY;
 const approvals=[...tracks.FDA_ORIGINAL_APPROVAL_ACTION,
  ...tracks.FDA_SUPPLEMENTAL_APPROVAL_ACTION];
 const crls=tracks.RETROSPECTIVE_FDA_CRL_LETTER;
 if(originals.length!==primary.records.length||
  originals.length!==queue.totals.originalSourceLeads||
  archived.length!==queue.totals.archiveUnverifiedTargetDateLeads||
  approvals.length!==queue.totals.FDAApprovalActionLeads||
  crls.length!==queue.totals.FDAArchivedCRLLetterLeads||
  originals.length+archived.length+approvals.length+crls.length!==queue.totals.reviewRows)
  throw Error("RAAS_CENSUS_GAP_SOURCE_OR_ACTION_TOTALS_INVALID");
 const goalsByYear=new Map([[2024,new Map()],[2025,new Map()]]);
 const originalByCase=new Map();
 for(const e of primary.records){
  if(!e||!ticker(e.ticker)||!day(e.pdufaTargetDate)||!e.caseId||
   ![2024,2025].includes(+e.pdufaTargetDate.slice(0,4))||
   e.reviewStatus!=="SOURCE_LEADS_RESEARCH_ONLY"||
   e.historicalCapitalizationAtEntryVerified!==false||
   originalByCase.has(e.caseId))
   throw Error("RAAS_CENSUS_GAP_UNTRUSTED_ORIGINAL_EVENT");
  originalByCase.set(e.caseId,e);
  const y=+e.pdufaTargetDate.slice(0,4),k=key(e.ticker,e.pdufaTargetDate);
  if(goalsByYear.get(y).has(k))
   throw Error("RAAS_CENSUS_GAP_DUPLICATED_ORIGINAL_GOAL");
  goalsByYear.get(y).set(k,e.caseId);
 }
 // Supplemental source-linked issuer notices are research leads, not cases
 // independently matched by the official FDA action crosswalk above.
 const pendingByGoal=new Map(),pendingByCase=new Map();
 for(const e of supplemental){
  const k=key(e?.ticker,e?.pdufaTargetDate),y=+String(e?.pdufaTargetDate||"").slice(0,4);
  const phase3=e?.phase3ReadoutDate||e?.phase3EvidenceDate;
  const outcome=e?.actualFDAActionSourceUrl||e?.outcomeSourceUrl;
  const src=x=>typeof x==="string"&&x.startsWith("https://");
  if(!e||!ticker(e.ticker)||!e.caseId||![2024,2025].includes(y)||
   !day(e.pdufaTargetDate)||!day(e.targetAnnouncementDate)||
   e.targetAnnouncementDate>=e.pdufaTargetDate||
   !day(phase3)||phase3>=e.pdufaTargetDate||
   !day(e.actualFDAActionDate)||!src(e.targetAnnouncementSourceUrl)||
   !src(e.phase3ReadoutSourceUrl||e.phase3EvidenceSourceUrl)||!src(outcome)||
   !["SOURCE_LEADS_RESEARCH_ONLY",
     "SOURCE_DATES_RECORDED_MARKET_CAP_AND_PRICE_INDEPENDENT_CHECK_PENDING"].includes(e.reviewStatus||e.asOfStatus)||
   e.historicalCapitalizationAtEntryVerified===true||
   e.historicalEntryMarketCap300m10bValidated===true||
   e.approvedAsTradingCase===true||pendingByGoal.has(k)||pendingByCase.has(e.caseId)||
   originalByCase.has(e.caseId)||goalsByYear.get(y).has(k))
   throw Error("RAAS_CENSUS_GAP_ADDITIONAL_SOURCE_INVALID_OR_DUPLICATED");
  pendingByGoal.set(k,e);pendingByCase.set(e.caseId,e);
  goalsByYear.get(y).set(k,e.caseId);
 }
 const originalTickers=new Map([[2024,new Set()],[2025,new Set()]]);
 for(const r of originals){
  const e=originalByCase.get(r.caseId);
  if(!e||r.id!=="ORIGINAL|"+e.caseId||r.ticker!==e.ticker||
   r.year!==+e.pdufaTargetDate.slice(0,4)||
   r.originalPublicPdufaTargetDate!==e.pdufaTargetDate||
   r.retrospectiveActionDate!==e.actualFDAActionDate||
   r.actualOutcome!==e.actualFDAOutcome||
   r.yearBasis!=="PUBLICLY_ANNOUNCED_PDUFA_TARGET_YEAR"||
   !["APPROVED","CRL"].includes(r.actualOutcome))
   throw Error("RAAS_CENSUS_GAP_PRIMARY_SOURCE_CROSSWALK_FAILED");
  originalTickers.get(r.year).add(r.ticker);
 }
 for(const e of pendingByGoal.values())originalTickers.get(+e.pdufaTargetDate.slice(0,4)).add(e.ticker);
 const archivedGoalKeys=new Set();
 const duplicates=[],unverified=[];
 for(const r of archived){
  if(!ticker(r.ticker)||!day(r.archiveSuggestedPdufaDate)||
   r.year!==+r.archiveSuggestedPdufaDate.slice(0,4)||
   r.yearBasis!=="UNVERIFIED_ARCHIVE_PDUFA_TARGET_YEAR"||
   r.originalPublicPdufaTargetDate!==null||
   r.reviewPriority!==2)
   throw Error("RAAS_CENSUS_GAP_ARCHIVE_IS_NOT_SOURCE_EVIDENCE");
  const k=key(r.ticker,r.archiveSuggestedPdufaDate),y=r.year;
  const match=goalsByYear.get(y).get(k)??null;
  if(match){
   duplicates.push({id:r.id,year:y,ticker:r.ticker,
    archiveSuggestedPdufaDate:r.archiveSuggestedPdufaDate,
    matchedOriginalCaseId:match,classification:pendingByGoal.has(k)?
     "ADDITIONAL_SOURCE_LINKED_PENDING_INDEPENDENT_FDA_MATCH":
     "ALREADY_SOURCED_SAME_TICKER_AND_TARGET"});
  } else {
   const repeated=archivedGoalKeys.has(k);
   archivedGoalKeys.add(k);
   unverified.push({id:r.id,year:y,ticker:r.ticker,
    archiveSuggestedPdufaDate:r.archiveSuggestedPdufaDate,
    status:repeated?"REPEATED_UNVERIFIED_ARCHIVE_GOAL":
     "UNVERIFIED_ARCHIVE_PDUFA_TARGET_FOR_SOURCE_RESEARCH",
    possibleSameIssuerOtherCycle:originalTickers.get(y).has(r.ticker),
    firstPublicPdufaGoalConfirmed:false,phase3EligibilityConfirmed:false,
    actualFdaOutcomeMatched:false,historicalListingVerified:false,
    cap300mTo10bVerified:false,independentReturnVerified:false,
    eligibleForTrading:false,validatedRaasScore:false,
    requiredNextEvidence:[
     "Independent original issuer/FDA PDUFA target disclosure and revisions",
     "Phase 3 program, clinical results and exact NDA/BLA indication",
     "FDA approval, CRL, extension or withdrawal review-cycle outcome",
     "Historical U.S. equity rights, listing and dated SEC share disclosures",
     "Independent raw and adjusted price, split and financing audit"
    ]});
  }
 }
 const years={};
 for(const [y,minIssuers] of [[2024,config.minimumIndependentTrainIssuers],
  [2025,config.minimumIndependentHoldoutIssuers]]){
  const orig=originals.filter(r=>r.year===y);
  const sourceKeys=new Set(orig.map(r=>r.ticker));
  const pending=[...pendingByGoal.values()].filter(e=>+e.pdufaTargetDate.slice(0,4)===y);
  const pendingKeys=new Set(pending.map(e=>e.ticker));
  const a=archived.filter(r=>r.year===y);
  const dup=duplicates.filter(r=>r.year===y);
  const un=unverified.filter(r=>r.year===y);
  const notYet=new Set(un.map(r=>r.ticker).filter(t=>!sourceKeys.has(t)&&!pendingKeys.has(t)));
  const all=new Set([...sourceKeys,...pendingKeys,...notYet]);
  years[y]={
   role:y===2024?"TRAIN":"ISSUER_DISJOINT_HOLDOUT",
   sourceBackedTargetEvents:orig.length,
   sourceBackedDistinctTickers:sourceKeys.size,
   additionalSourceLinkedResearchCases:pending.length,
   additionalSourceLinkedResearchDistinctTickers:pendingKeys.size,
   combinedKnownSourceLinkedDistinctTickers:new Set([...sourceKeys,...pendingKeys]).size,
   archivedTargetDateRows:a.length,
   archiveRowsAlreadySameGoalSourced:dup.length,
   archivedUnverifiedDateRows:un.length,
   archivedUnverifiedDistinctTickers:new Set(un.map(r=>r.ticker)).size,
   newCandidateTickerNamesNotYetSourceBacked:notYet.size,
   bestCaseDistinctTickerNamesInCurrentlyLocatedTargetQueue:all.size,
   requiredIndependentVerifiedIssuers:minIssuers,
   minimumAdditionalIssuerDiscoveryBeyondCurrentTargetQueue:
    Math.max(0,minIssuers-all.size),
   actualIndependentlyValidatedIssuers:0,
   completeTargetYearCensus:false,
   noTickersAreApprovedTradingCases:true
  };
 }
 const namedYears=new Map();
 for(const [k,v] of Object.entries(years))namedYears.set(+k,v);
 const byTickerYears=new Map();
 for(const y of [2024,2025]){
  const tickers=new Set([
   ...originals.filter(r=>r.year===y).map(r=>r.ticker),
   ...unverified.filter(r=>r.year===y).map(r=>r.ticker),
   ...[...pendingByGoal.values()].filter(e=>+e.pdufaTargetDate.slice(0,4)===y).map(e=>e.ticker)
  ]);
  for(const t of tickers){
   if(!byTickerYears.has(t))byTickerYears.set(t,new Set());
   byTickerYears.get(t).add(y);
  }
 }
 const crossYearCandidates=[...byTickerYears].filter(([,y])=>y.size===2)
  .map(([ticker])=>ticker).sort();
 const sameYearMultiGoals=[];
 for(const y of [2024,2025]){
  const m=new Map();
  for(const x of [...originals.filter(r=>r.year===y).map(r=>({
    ticker:r.ticker,date:r.originalPublicPdufaTargetDate,
    reviewId:r.id
   })),...[...pendingByGoal.values()].filter(e=>+e.pdufaTargetDate.slice(0,4)===y).map(e=>({
    ticker:e.ticker,date:e.pdufaTargetDate,reviewId:"SOURCE_LINKED|"+e.caseId
   })),...unverified.filter(r=>r.year===y).map(r=>({
    ticker:r.ticker,date:r.archiveSuggestedPdufaDate,reviewId:r.id
   }))]){
   if(!m.has(x.ticker))m.set(x.ticker,[]);
   m.get(x.ticker).push(x);
  }
  for(const [ticker,records] of m){
   const distinct=new Set(records.map(r=>r.date));
   if(distinct.size>1)sameYearMultiGoals.push({year:y,ticker,
    suggestedDistinctTargetDates:[...distinct].sort(),
    archiveRowCount:records.length,
    independentIssuerSlotsAllowed:1,
    classification:"SAME_TICKER_NOT_INDEPENDENT_REPLICATES"});
  }
 }
 const queueOrder=unverified.slice().sort((a,b)=>{
  const ga=years[a.year].minimumAdditionalIssuerDiscoveryBeyondCurrentTargetQueue;
  const gb=years[b.year].minimumAdditionalIssuerDiscoveryBeyondCurrentTargetQueue;
  return gb-ga||b.year-a.year||
   a.archiveSuggestedPdufaDate.localeCompare(b.archiveSuggestedPdufaDate)||
   a.ticker.localeCompare(b.ticker)||a.id.localeCompare(b.id);
 });
 return {schemaVersion:1,scope:OUT,
  status:"INCOMPLETE_PDUFA_TARGET_CENSUS_RESEARCH_ONLY",
  trainYear:2024,holdoutYear:2025,
  originalEventSourceCount:originals.length,
  additionalSourceLinkedResearchLeadCount:pendingByGoal.size,
  additionalSourceLinkedResearchLeads:[...pendingByGoal.values()].map(e=>({
   caseId:e.caseId,ticker:e.ticker,pdufaTargetDate:e.pdufaTargetDate,
   studyYear:+e.pdufaTargetDate.slice(0,4),
   status:"SOURCE_LINKED_PENDING_FDA_MATCH_MARKET_CAP_AND_CENSUS_AUDIT",
   validatedTrade:false,completeCensus:false,approvedRaasMetric:false
  })),
  annualTargetsAudited:0,independentlyValidatedTradingCases:0,
  calibratedRaasMetrics:0,approvedOptimalWindow:null,
  queueSourceActionRows:queue.totals.reviewRows,
  fdaRetrospectiveApprovalActionRows:approvals.length,
  fdaRetrospectiveCRLLetterRows:crls.length,
  actionYearRowsNotCountedAsTargetYearDenominator:approvals.length+crls.length,
  archivedTargetDateLeadRows:archived.length,
  archiveSameGoalDuplicatedSourceRows:duplicates.length,
  unsourcedArchivedTargetReviewTasks:unverified.length,
  byTargetYear:years,
  acrossYearCandidateTickerConflicts:crossYearCandidates,
  sameYearMultipleGoalSameTicker:sameYearMultiGoals,
  previouslySourcedArchiveOverlaps:duplicates,
  nextArchivedTargetSourceReviews:queueOrder,
  warnings:[
   "An archived suggested date is not a verified PDUFA goal, qualifying Phase 3 trial or proven trading opportunity.",
   "Approval ACTION YEAR and CRL LETTER YEAR are never added to PDUFA TARGET YEAR candidate counts.",
   "Source-backed case rows are unvalidated as trades, capitalization, and prospective predictive scores.",
   "The best-case ticker count is only a capacity bound within the CURRENT source/archival target queue. It is not a census size or a verified issuer sample.",
   "One issuer can have multiple distinct application goals or dates; those never constitute independent train/holdout issuers.",
   "Cross-year candidate ticker conflicts need issuer-disjoint group assignment and cannot be used in both calibration and holdout.",
   "The archived candidates may be ineligible, dates may be wrong, and many unlocated PDUFA cases remain to be discovered.",
   "Full calendar-year 2024 and 2025 target censuses, 30/30 independent issuer qualification, return validation and all RAAS metrics remain pending."
  ]};
}
function csv(result){
 if(!result||result.scope!==OUT)throw Error("RAAS_CENSUS_GAP_CSV_SOURCE_INVALID");
 const cols=["year","ticker","archiveSuggestedPdufaDate","id","status",
  "possibleSameIssuerOtherCycle","firstPublicPdufaGoalConfirmed",
  "phase3EligibilityConfirmed","actualFdaOutcomeMatched","historicalListingVerified",
  "cap300mTo10bVerified","independentReturnVerified","eligibleForTrading","requiredNextEvidence"];
 return cols.join(",")+"\n"+result.nextArchivedTargetSourceReviews.map(r=>
  cols.map(k=>safeCsv(Array.isArray(r[k])?r[k].join(" | "):r[k])).join(",")
 ).join("\n")+"\n";
}
function main(){
 try{
  const queuePath=process.env.RAAS_TWO_YEAR_TRIAGE_RESULT||
   path.join(root,"raas-2024-2025-source-review-queue.json");
  const cfgPath=process.env.RAAS_CENSUS_GAP_CONFIG||
   path.join(root,"new-platform/frontend/data/raas-active-study-config.json");
  const srcPath=process.env.RAAS_CENSUS_GAP_PRIMARY||
   path.join(root,"new-platform/frontend/data/raas-active-2024-2025-primary-source-leads.json");
  const jsonPath=process.env.RAAS_CENSUS_GAP_JSON||
   path.join(root,"raas-2024-2025-census-gap-audit.json");
  const csvPath=process.env.RAAS_CENSUS_GAP_CSV||
   path.join(root,"raas-2024-2025-next-target-review.csv");
  const extraPaths=[
   "new-platform/frontend/data/raas-2024-2025-expanded-candidate-source-leads.json",
   "new-platform/frontend/data/raas-2025-three-phase3-fda-price-research-leads.json",
   "new-platform/frontend/data/raas-2025-cort-relacorilant-fda-phase3-source-lead.json"];
  const supplemental=extraPaths.flatMap(p=>
   JSON.parse(fs.readFileSync(path.join(root,p),"utf8")).records);
  const r=build({
   queue:JSON.parse(fs.readFileSync(queuePath,"utf8")),
   config:JSON.parse(fs.readFileSync(cfgPath,"utf8")),
   primary:JSON.parse(fs.readFileSync(srcPath,"utf8")),
   supplemental
  });
  for(const out of [jsonPath,csvPath])fs.mkdirSync(path.dirname(out),{recursive:true});
  fs.writeFileSync(jsonPath,JSON.stringify(r,null,2)+"\n");
  fs.writeFileSync(csvPath,csv(r));
  const summary={status:r.status,
   totalOfficialActionYearRowsExcludedFromPdufaDenominator:
    r.actionYearRowsNotCountedAsTargetYearDenominator,
   archivedLeads:r.archivedTargetDateLeadRows,
   alreadySourcedArchiveDuplicate:r.archiveSameGoalDuplicatedSourceRows,
   additionalSourceLinkedResearchLeads:r.additionalSourceLinkedResearchLeadCount,
   unsourcedArchiveReviewTasks:r.unsourcedArchivedTargetReviewTasks,
   train:r.byTargetYear[2024],holdout:r.byTargetYear[2025],
   validatedTradingCases:r.independentlyValidatedTradingCases,approvedRaasMetrics:0};
  console.log(JSON.stringify(summary));
  if(process.env.GITHUB_STEP_SUMMARY)
   fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
    "### Source-deduplicated 2024–2025 target-year census gap (NOT VALIDATED)\n\n"+
    JSON.stringify(summary,null,2)+"\n\n"+
    "FDA action-year rows excluded from target-year cohort; one issuer one independent group.\n");
 }catch(e){
  console.error("RAAS_CENSUS_GAP_FATAL_"+String(e.message||e).replace(/[^A-Z0-9_]/g,"_"));
  process.exitCode=1;
 }
}
if(require.main===module)main();
module.exports={build,csv,safeCsv};
