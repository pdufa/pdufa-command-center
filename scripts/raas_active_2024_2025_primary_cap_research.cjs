#!/usr/bin/env node
"use strict";
/**
 * RAAS active 2024/2025 source-link and true historical price research.
 * This is an isolated ORIGINAL source-lead queue, not the accepted-score
 * or fully validated active 2024/2025 event intake.
 *
 * 2024 MDGL Rezdiffra original NDA: FDA acted on target.\n * 2024 ARQT Zoryve 0.15% supplemental NDA: FDA acted 2 days AFTER target.
 * 2025 AXSM Symbravo: FDA acted 1 day BEFORE target.
 * PDUFA target, Phase 3 readout, SEC share publication, FDA action
 * and previous application review cycle must remain separated.
 */
const fs=require("node:fs"),path=require("node:path");
const {validateSourceLeads}=require("./raas_historical_event_census_worklist.cjs");
const cap=require("./raas_historical_raw_market_cap_research.cjs");
const {assemble}=require("./raas_historical_candidate_review_queue.cjs");
const windows=require("./raas_historical_provisional_window_grid.cjs");
const {validatePreentry,build:earlierStudy}=require("./raas_historical_preentry_share_window_research.cjs");
const root=path.resolve(__dirname,"..");
const paths={
 events:"new-platform/frontend/data/raas-active-2024-2025-primary-source-leads.json",
 shares:"new-platform/frontend/data/raas-active-2024-2025-sec-cover-share-leads.json",
 earlier:"new-platform/frontend/data/raas-active-2024-2025-preentry-sec-share-leads.json",
 intake:"new-platform/frontend/data/raas-active-2024-2025-pdufa-intake.json"
};
const load=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
function verify(events,shares,earlier,intake){
 const cases=validateSourceLeads(events);
 if(cases.length!==3||shares.records?.length!==3||
  earlier.records?.length!==3||intake.scope!=="RAAS_2024_2025_PDUFA_POINT_IN_TIME_INTAKE"||
  intake.records.some(x=>cases.some(c=>x.caseId===c.caseId)))
  throw Error("RAAS_ACTIVE_SOURCE_LEADS_MUST_NOT_COUNT_AS_ACCEPTED_INTAKE");
 const order=cases.slice().sort((a,b)=>a.pdufaTargetDate.localeCompare(b.pdufaTargetDate));
 const byTicker=new Map(order.map(e=>[e.ticker,e]));
 const arqt=byTicker.get("ARQT"),axsm=byTicker.get("AXSM"),mdgl=byTicker.get("MDGL");
 if(byTicker.size!==3||
  mdgl?.caseId!=="MDGL|REZDIFFRA|NDA217785|2024"||
  mdgl.pdufaTargetDate!=="2024-03-14"||
  mdgl.targetAnnouncementDate!=="2023-09-13"||
  mdgl.phase3ReadoutDate!=="2022-12-19"||
  mdgl.actualFDAActionDate!=="2024-03-14"||
  mdgl.actualFDAOutcome!=="APPROVED"||
  mdgl.acceleratedApproval!==true||
  !mdgl.nctIds.includes("NCT03900429")||
  arqt?.caseId!=="ARQT|ZORYVE015_AD|NDA215985_S007|2024"||
  arqt.ticker!=="ARQT"||arqt.pdufaTargetDate!=="2024-07-07"||
  arqt.targetAnnouncementDate!=="2023-11-29"||
  arqt.phase3ReadoutDate!=="2022-12-12"||
  arqt.actualFDAActionDate!=="2024-07-09"||
  arqt.fdaDecisionAfterPdufaGoalDays!==2||
  arqt.formalGoalExtensionIndependentlyVerified!==false||
  arqt.actualFDAOutcome!=="APPROVED"||
  !arqt.nctIds.includes("NCT04773587")||
  !arqt.nctIds.includes("NCT04773600")||
  axsm.caseId!=="AXSM|SYMBRAVO|NDA215431|2025"||
  axsm.ticker!=="AXSM"||axsm.pdufaTargetDate!=="2025-01-31"||
  axsm.targetAnnouncementDate!=="2024-09-04"||
  axsm.phase3ReadoutDate!=="2020-04-06"||
  axsm.actualFDAActionDate!=="2025-01-30"||
  axsm.fdaActionEarlierThanPdufaGoalDays!==1||
  axsm.previousCRLAddressedInResubmission!==true||
  axsm.initial2022CRLNot2025Outcome!==true||
  !axsm.nctIds.includes("NCT03896009")||
  !axsm.nctIds.includes("NCT04163185"))
  throw Error("RAAS_ACTIVE_ORIGINAL_TARGET_ACTION_IDENTITY_INVALID");
 const prior=validatePreentry({primary:events,shares,preentry:earlier});
 const laterByCase=new Map(shares.records.map(s=>[s.caseId,s]));
 const diffs=[];
 for(const event of order){
  const now=cap.checkedLead(laterByCase.get(event.caseId),event);
  const old=prior.get(event.caseId);
  if(!old||now.firstConservativeEntryDate<=old.firstConservativeEntryDate||
   old.venue!=="NASDAQ"||now.venue!=="NASDAQ"||
   !now.needsShareContinuityAudit||!now.needsIndependentPriceCrosscheck)
   throw Error("RAAS_ACTIVE_SEC_COVER_SHARE_CHRONOLOGY_INVALID");
  const difference=now.sharesOutstanding-old.sharesOutstanding;
  if(event.ticker==="MDGL"&&(
   old.sharesOutstanding!==19742646||now.sharesOutstanding!==19897425||
   old.firstConservativeEntryDate!=="2023-11-07"||
   now.firstConservativeEntryDate!=="2024-02-29"||
   difference!==154779))
   throw Error("RAAS_2024_MDGL_SECURITIES_DISCLOSURE_MISMATCH");
  if(event.ticker==="ARQT"&&(
   old.sharesOutstanding!==96813363||now.sharesOutstanding!==115764164||
   old.firstConservativeEntryDate!=="2024-02-28"||
   now.firstConservativeEntryDate!=="2024-05-15"||
   difference!==18950801))
   throw Error("RAAS_2024_SECURITIES_DISCLOSURE_MISMATCH");
  if(event.ticker==="AXSM"&&(
   old.sharesOutstanding!==48000205||now.sharesOutstanding!==48462376||
   old.firstConservativeEntryDate!=="2024-08-06"||
   now.firstConservativeEntryDate!=="2024-11-13"||
   difference!==462171))
   throw Error("RAAS_2025_SECURITIES_DISCLOSURE_MISMATCH");
  diffs.push({year:+event.pdufaTargetDate.slice(0,4),caseId:event.caseId,
   ticker:event.ticker,pdufaTargetDate:event.pdufaTargetDate,
   actualFDAActionDate:event.actualFDAActionDate,
   earlierShares:old.sharesOutstanding,laterShares:now.sharesOutstanding,
   earlierSECSource:old.sourceUrl,laterSECSource:now.sourceUrl,
   reportedCoverShareChange:difference,
   eligibleForApprovedTrading:false,
   firstPublicPdufaSource:event.targetAnnouncementSourceUrl,
   phase3Source:event.phase3ReadoutSourceUrl,
   outcomeSource:event.actualFDAActionSourceUrl});
 }
 return diffs;
}
async function execute({events=load(paths.events),shares=load(paths.shares),
 earlier=load(paths.earlier),intake=load(paths.intake),key,secret,request=fetch}={}){
 const sourceLeads=verify(events,shares,earlier,intake);
 const base={schemaVersion:1,scope:"RAAS_ACTIVE_2024_2025_ORIGINAL_SOURCE_LEADS_AND_ALPACA_CAP_RESEARCH",
  studyStartDate:"2024-01-01",studyEndDate:"2025-12-31",
  sourceLeads,sourceLeadCount:sourceLeads.length,
  sourceLeadYears:[2024,2025],
  reviewedIntakeCases:intake.records.length,
  validatedTradingCases:0,approvedRaasMetrics:0,fullYearCensusesAudited:0,
  selectedOptimalWindow:null,allResearchOnly:true};
 if(!key||!secret)return {...base,status:"BLOCKED_MISSING_ALPACA_CREDENTIALS",
  rawHistoricalSessions:0,plannedWindowPairsExamined:0,
  provisionalPrimaryWindowRows:0,provisionalEarlierShareWindows:0};
 const raw=await cap.execute({key,secret,request,events,shares});
 if(raw.status!=="UNVALIDATED_HISTORICAL_CAP_RESEARCH_ONLY"||
  raw.cases?.length!==3||raw.historicallyEligibleTrades!==0||
  raw.approvedRaasRatings!==0)
  throw Error("RAAS_ACTIVE_RAW_CAP_PRICE_RESEARCH_INVALID");
 const queue=assemble({primary:events,shares,rawCap:raw});
 const w=windows.build({primary:events,shares,rawCap:raw});
 const e=earlierStudy({primary:events,shares,preentry:earlier,rawCap:raw});
 if(queue.summary.reviewedEligibleTradingEvents!==0||
  w.summary.independentlyVerifiedEligibleTradingCases!==0||
  e.summary.independentlyValidatedEventTrades!==0||
  w.summary.optimalWindowDeclared||e.summary.optimalWindowDeclared)
  throw Error("RAAS_ACTIVE_UNVERIFIED_SOURCE_PROMOTION_FORBIDDEN");
 return {...base,status:"2024_2025_SOURCE_LEADS_UNVALIDATED_PRICE_RESEARCH",
  rawHistoricalSessions:raw.rawSessions,
  provisionalCapIn300mTo10bResearchSessions:raw.possible300mTo10bResearchSessions,
  plannedWindowPairsExamined:w.summary.programWindowEvaluations,
  provisionalPrimaryWindowRows:w.summary.provisionalWindowsWithCompletePriceAndTiming,
  provisionalEarlierShareWindows:e.summary.newlyMeasurablePreentryWindows,
  caseResearch:e.cases.map(c=>({
   caseId:c.caseId,ticker:c.ticker,year:+c.pdufaTargetDate.slice(0,4),
   provisionalWindows:c.unvalidatedPriceAndCapWindows,
   earlierShareSourceRows:c.newlyMeasurablePreentryWindows,
   namedWindow79to14:c.namedWindowDiagnostics.find(x=>
    x.entryLeadDays===79&&x.exitLeadDays===14)||null,
   missingAudit:"SEC_SHARE_CONTINUITY_SPLITS_INDEPENDENT_PRICE_VENDOR_2024_2025_CENSUS"})),
  priceDataRawAndAdjusted:raw.cases,
  sourceQueue:queue.cases,
  warnings:["Three originally sourced programs out of the 2024–2025 discovery universe; NOT two complete FDA year censuses.",
   "2024 ARQT FDA action July 9 occurred after the company-announced July 7 goal, without independently established formal extension.",
   "2025 AXSM FDA action Jan 30 occurred one day before Jan 31 goal; older 2022 manufacturing CRL was a separate review cycle.",
   "SEC shares increased by 154,779 MDGL, 18,950,801 ARQT and 462,171 AXSM between dated snapshots. Do not interpolate constant capitalization.",
   "A qualifying price bar is not an independently validated historical issuer, trading fill or RAAS prediction."]};
}
function main(){
 execute({key:process.env.APCA_API_KEY_ID||process.env.ALPACA_API_KEY_ID,
  secret:process.env.APCA_API_SECRET_KEY||process.env.ALPACA_SECRET_KEY})
 .then(r=>{
  const out=process.env.RAAS_ACTIVE_SOURCE_RESEARCH_OUTPUT||
   path.join(root,"raas-2024-2025-original-case-price-research.json");
  fs.mkdirSync(path.dirname(out),{recursive:true});
  fs.writeFileSync(out,JSON.stringify(r,null,2)+"\n");
  const summary={status:r.status,sourceLeads:r.sourceLeadCount,
   years:r.sourceLeadYears,rawHistoricalSessions:r.rawHistoricalSessions,
   capInRangeResearchSessions:r.provisionalCapIn300mTo10bResearchSessions??0,
   gridRows:r.plannedWindowPairsExamined,
   provisionalEarlierShareWindows:r.provisionalEarlierShareWindows,
   validatedTradingCases:0,approvedRaasMetrics:0};
  console.log(JSON.stringify(summary));
  if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
   "### Active 2024/2025 original case research leads (NOT qualified backtest)\n\n"+
   JSON.stringify(summary,null,2)+"\n\nNo case enters approved trading/RAAS intake.\n");
  if(r.status==="BLOCKED_MISSING_ALPACA_CREDENTIALS")process.exitCode=1;
 }).catch(e=>{
  console.error("RAAS_ACTIVE_ORIGINAL_CASES_FATAL_"+String(e.message).replace(/[^A-Z0-9_]/g,"_"));
  process.exitCode=1;
 });
}
if(require.main===module)main();
module.exports={verify,execute};
