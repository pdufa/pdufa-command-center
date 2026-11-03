#!/usr/bin/env node
"use strict";
/**
 * RAAS active 2024/2025 source-link and true historical price research.
 * This is an isolated ORIGINAL source-lead queue, not the accepted-score
 * or fully validated active 2024/2025 event intake.
 *
 * 2024 MDGL Rezdiffra original NDA: FDA acted on target.
 * 2024 GERN Rytelo original NDA: FDA acted ten days before target.
 * 2024 ARQT Zoryve 0.15% supplemental NDA: FDA acted 2 days AFTER target.
 * 2024 LXRX Zynquista: FDA issued a CRL ON target (older 2019 CRL is a different review).
 * 2025 AXSM Symbravo: FDA acted 1 day BEFORE target.
 * 2025 SLNO Vykat XR: FDA granted three-month extension then acted one day before revised target.
 * 2025 SRRK apitegromab: FDA issued a manufacturing site CRL on its goal date.
 * 2025 CYTK aficamten: FDA formally extended Sep 26 to Dec 26, approved Dec 19.
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
 if(cases.length!==8||shares.records?.length!==8||
  earlier.records?.length!==8||intake.scope!=="RAAS_2024_2025_PDUFA_POINT_IN_TIME_INTAKE"||
  intake.records.some(x=>cases.some(c=>x.caseId===c.caseId)))
  throw Error("RAAS_ACTIVE_SOURCE_LEADS_MUST_NOT_COUNT_AS_ACCEPTED_INTAKE");
 const order=cases.slice().sort((a,b)=>a.pdufaTargetDate.localeCompare(b.pdufaTargetDate));
 const byTicker=new Map(order.map(e=>[e.ticker,e]));
 const arqt=byTicker.get("ARQT"),axsm=byTicker.get("AXSM"),
  mdgl=byTicker.get("MDGL"),gern=byTicker.get("GERN"),
  slno=byTicker.get("SLNO"),lxrx=byTicker.get("LXRX"),
  srrk=byTicker.get("SRRK"),cytk=byTicker.get("CYTK");
 if(byTicker.size!==8||
  cytk?.caseId!=="CYTK|AFICAMTEN_OHCM|NDA219083|2025"||
  cytk.application!=="NDA 219083"||
  cytk.pdufaTargetDate!=="2025-12-26"||
  cytk.originallyAnnouncedPdufaTargetDate!=="2025-09-26"||
  cytk.originalTargetAnnouncementDate!=="2024-12-02"||
  cytk.targetAnnouncementDate!=="2025-05-01"||
  cytk.fdaGoalExtensionAnnouncedDate!=="2025-05-01"||
  cytk.formalGoalExtensionIndependentlyVerified!==true||
  cytk.phase3ReadoutDate!=="2023-12-27"||
  cytk.actualFDAActionDate!=="2025-12-19"||
  cytk.actualFDAOutcome!=="APPROVED"||
  cytk.fdaActionEarlierThanPdufaGoalDays!==7||
  !cytk.nctIds.includes("NCT05186818")||
  srrk?.caseId!=="SRRK|APITEGROMAB_SMA|BLA761463|2025_CRL"||
  srrk.application!=="BLA 761463"||
  srrk.pdufaTargetDate!=="2025-09-22"||
  srrk.targetAnnouncementDate!=="2025-03-25"||
  srrk.phase3ReadoutDate!=="2024-10-07"||
  srrk.actualFDAActionDate!=="2025-09-22"||
  srrk.firstPublicFDAActionAnnouncementDate!=="2025-09-23"||
  srrk.actualFDAOutcome!=="CRL"||
  srrk.phase3PrimaryEndpointMet!==true||
  srrk.fdaLetterRetrospectivelyPublishedAfterAction!==true||
  srrk.primaryOutcomeReason!=="THIRD_PARTY_FILL_FINISH_FACILITY_CGMP_DEFICIENCIES"||
  !srrk.nctIds.includes("NCT05156320")||
  lxrx?.caseId!=="LXRX|ZYNQUISTA_SOTAGLIFLOZIN|NDA210934|2024_CRL"||
  lxrx.application!=="NDA 210934"||
  lxrx.pdufaTargetDate!=="2024-12-20"||
  lxrx.targetAnnouncementDate!=="2024-07-16"||
  lxrx.phase3ReadoutDate!=="2017-06-09"||
  lxrx.actualFDAActionDate!=="2024-12-20"||
  lxrx.actualFDAOutcome!=="CRL"||
  lxrx.previous2019CRLIsSeparateReviewCycle!==true||
  lxrx.priorCRLDate!=="2019-03-22"||
  lxrx.firstPublicFDAActionAnnouncementDate!=="2024-12-20"||
  !lxrx.nctIds.includes("NCT02531035")||
  slno?.caseId!=="SLNO|VYKAT_XR_DCCR|NDA216665|2025"||
  slno.application!=="NDA 216665"||
  slno.pdufaTargetDate!=="2025-03-27"||
  slno.originallyAnnouncedPdufaTargetDate!=="2024-12-27"||
  slno.originalTargetAnnouncementDate!=="2024-08-27"||
  slno.targetAnnouncementDate!=="2024-11-26"||
  slno.fdaGoalExtensionAnnouncedDate!=="2024-11-26"||
  slno.formalGoalExtensionIndependentlyVerified!==true||
  slno.phase3ReadoutDate!=="2023-09-26"||
  slno.actualFDAActionDate!=="2025-03-26"||
  slno.actualFDAOutcome!=="APPROVED"||
  slno.fdaActionEarlierThanPdufaGoalDays!==1||
  !slno.nctIds.includes("NCT03440814")||
  !slno.nctIds.includes("NCT03714373")||
  gern?.caseId!=="GERN|RYTELO_IMETELSTAT|NDA217779|2024"||
  gern.pdufaTargetDate!=="2024-06-16"||
  gern.targetAnnouncementDate!=="2023-08-22"||
  gern.phase3ReadoutDate!=="2023-01-04"||
  gern.actualFDAActionDate!=="2024-06-06"||
  gern.actualFDAOutcome!=="APPROVED"||
  gern.fdaActionEarlierThanPdufaGoalDays!==10||
  gern.application!=="NDA 217779"||
  !gern.nctIds.includes("NCT02598661")||
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
  if(event.ticker==="CYTK"&&(
   old.sharesOutstanding!==119657156||now.sharesOutstanding!==122264929||
   old.firstConservativeEntryDate!=="2025-08-08"||
   now.firstConservativeEntryDate!=="2025-11-06"||difference!==2607773))
   throw Error("RAAS_2025_CYTK_SECURITIES_DISCLOSURE_MISMATCH");
  if(event.ticker==="SRRK"&&(
   old.sharesOutstanding!==94945562||now.sharesOutstanding!==96127265||
   old.firstConservativeEntryDate!=="2025-05-15"||
   now.firstConservativeEntryDate!=="2025-08-07"||difference!==1181703))
   throw Error("RAAS_2025_SRRK_SECURITIES_DISCLOSURE_MISMATCH");
  if(event.ticker==="LXRX"&&(
   old.sharesOutstanding!==361492295||now.sharesOutstanding!==361492295||
   old.firstConservativeEntryDate!=="2024-08-03"||
   now.firstConservativeEntryDate!=="2024-11-14"||difference!==0))
   throw Error("RAAS_2024_LXRX_SECURITIES_DISCLOSURE_MISMATCH");
  if(event.ticker==="SLNO"&&(
   old.sharesOutstanding!==43117432||now.sharesOutstanding!==45857291||
   old.firstConservativeEntryDate!=="2024-11-07"||
   now.firstConservativeEntryDate!=="2025-03-01"||
   difference!==2739859))
   throw Error("RAAS_2025_SLNO_SECURITIES_DISCLOSURE_MISMATCH");
  if(event.ticker==="GERN"&&(
   old.sharesOutstanding!==546059309||now.sharesOutstanding!==593132540||
   old.firstConservativeEntryDate!=="2024-02-29"||
   now.firstConservativeEntryDate!=="2024-05-03"||
   difference!==47073231))
   throw Error("RAAS_2024_GERN_SECURITIES_DISCLOSURE_MISMATCH");
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
  raw.cases?.length!==8||raw.historicallyEligibleTrades!==0||
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
  warnings:["Eight originally sourced programs (including 2024 and 2025 CRLs) out of the 2024–2025 discovery universe; NOT two complete FDA year censuses.",
   "2024 ARQT FDA action July 9 occurred after the company-announced July 7 goal, without independently established formal extension.",
   "2025 AXSM FDA action Jan 30 occurred one day before Jan 31 goal; older 2022 manufacturing CRL was a separate review cycle.",
   "2024 LXRX FDA issued a December 20 CRL on its published PDUFA goal; prior March 2019 CRL was a separate cycle. Historical FDA PDF publication is retrospective and its content cannot be used as a predecision signal.",
   "2025 CYTK aficamten NDA219083 revised its publicly announced original Sep26 2025 goal to Dec26 2025 via a REMS major amendment reported May1 2025, before T-79 entry; FDA approved Dec19 2025, seven calendar days before revised goal. Do not use the historical FDA decision as an entry-time feature.",
   "2025 SRRK apitegromab BLA 761463 received a September 22 2025 manufacturing facility CRL despite positive Phase 3 SAPPHIRE; the company announced it Sept 23 and FDA archive PDF was retrospective, neither can be backdated as pre-decision evidence.",
   "2025 SLNO revised PDUFA March 27 followed Nov 26 2024 formal extension from original Dec 27 2024; FDA acted one day early. C601 Phase 3 primary endpoint failed before C602 randomized withdrawal positive result.",
   "SEC cover snapshots increased by 154,779 MDGL, 47,073,231 GERN, 18,950,801 ARQT, 462,171 AXSM and 2,739,859 SLNO, while LXRX snapshots differ by zero and SRRK increased by 1,181,703 shares, including unresolved pre-funded warrants (NOT proof of daily share continuity). Do not interpolate constant capitalization.",
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
