#!/usr/bin/env node
"use strict";
/**
 * 2018 AcelRx/DSUVIA historical PDUFA research-only.
 * Public issuer Nov 3 goal and retrospectively described FDA Nov 2 internal goal
 * must remain separate. Never create approved cases, returns, RAAS scores.
 */
const fs=require("node:fs"),path=require("node:path");
const {validateSourceLeads}=require("./raas_historical_event_census_worklist.cjs");
const cap=require("./raas_historical_raw_market_cap_research.cjs");
const {assemble}=require("./raas_historical_candidate_review_queue.cjs");
const win=require("./raas_historical_provisional_window_grid.cjs");
const {build:studyEarlier,validatePreentry}=require("./raas_historical_preentry_share_window_research.cjs");
const root=path.resolve(__dirname,".."),read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const PATHS={
 primary:"new-platform/frontend/data/raas-historical-2018-primary-source-leads.json",
 shares:"new-platform/frontend/data/raas-2018-sec-cover-share-leads.json",
 earlier:"new-platform/frontend/data/raas-preentry-2018-sec-cover-share-leads.json"
};
function verifySources(primary,shares,earlier){
 const events=validateSourceLeads(primary);
 if(events.length!==1||events[0].caseId!=="ACRX|DSUVIA|NDA209128|2018"||
  events[0].ticker!=="ACRX"||events[0].application!=="NDA 209128"||
  events[0].pdufaTargetDate!=="2018-11-03"||
  events[0].targetAnnouncementDate!=="2018-05-24"||
  events[0].fdaInternalGoalFromRetrospectiveReviewDate!=="2018-11-02"||
  events[0].phase3ReadoutDate!=="2016-09-15"||
  events[0].actualFDAActionDate!=="2018-11-02"||
  events[0].priorCRLActionDate!=="2017-10-11"||
  events[0].priorCRLReviewCycleDifferent!==true||
  events[0].remSRequiredOnApproval!==true||
  events[0].actualFDAOutcome!=="APPROVED"||
  !events[0].nctIds.includes("NCT02447848")||
  !Array.isArray(shares.records)||shares.records.length!==1)
  throw Error("RAAS_2018_ACRX_FDA_SOURCE_INVALID");
 const late=cap.checkedLead(shares.records[0],events[0]);
 const prior=validatePreentry({primary,shares,preentry:earlier});
 const early=prior.get(events[0].caseId);
 if(prior.size!==1||!early||
  late.sharesOutstanding!==60599914||
  late.sharesMeasurementDate!=="2018-07-26"||
  late.filedDate!=="2018-08-02"||
  late.firstConservativeEntryDate!=="2018-08-03"||
  early.sharesOutstanding!==51320598||
  early.sharesMeasurementDate!=="2018-05-07"||
  early.filedDate!=="2018-05-10"||
  early.firstConservativeEntryDate!=="2018-05-11"||
  !late.needsShareContinuityAudit||!late.needsIndependentPriceCrosscheck)
  throw Error("RAAS_2018_ACRX_ASOF_SHARES_INVALID");
 return {caseId:events[0].caseId,year:2018,ticker:"ACRX",
  firstLocatedPublicPdufaTarget:"2018-11-03",
  retrospectiveInternalFdaGoalDate:"2018-11-02",
  actualFdaActionDate:"2018-11-02",
  priorCrLActionDate:"2017-10-11",
  targetSourceUrl:events[0].targetAnnouncementSourceUrl,
  retrospectiveFdaGoalSourceUrl:events[0].fdaInternalGoalRetrospectiveReviewSourceUrl,
  phase3SourceUrl:events[0].phase3ReadoutSourceUrl,
  actionSourceUrl:events[0].actualFDAActionSourceUrl,
  oldShareSourceUrl:early.sourceUrl,newShareSourceUrl:late.sourceUrl,
  oldPublishedShares:early.sharesOutstanding,newPublishedShares:late.sharesOutstanding,
  publishedCoverShareIncrease:late.sharesOutstanding-early.sharesOutstanding};
}
const blocked=()=>({sourcePrograms2018:1,priceResearchSessions:0,
 preliminaryCapInRangeSessions:0,windowPairsChecked:0,
 provisionalPriceAndCapWindows:0,addedEarlierShareWindows:0,
 approvedRaasScores:0,validatedTradingCases:0,fullTenYearCensusAudited:false});
async function execute({primary=read(PATHS.primary),shares=read(PATHS.shares),
 earlier=read(PATHS.earlier),key,secret,request=fetch}={}){
 const sources=verifySources(primary,shares,earlier);
 const base={schemaVersion:1,scope:"RAAS_2018_ACRX_DSUVIA_HISTORICAL_RESEARCH",sources};
 if(!key||!secret)return {...base,status:"BLOCKED_MISSING_ALPACA_CREDENTIALS",
  summary:blocked()};
 let raw;
 try{raw=await cap.execute({key,secret,request,events:primary,shares});}
 catch(err){
  const msg=String(err?.message||"");
  if(!/^RAAS_CAP_ALPACA_HTTP_(404|422)$/.test(msg)&&
   msg!=="RAAS_CAP_INSUFFICIENT_BARS")throw err;
  return {...base,status:"BLOCKED_ASOF_SYMBOL_OR_PRICE_HISTORY_UNAVAILABLE",
   providerGapCode:msg,summary:blocked(),
   caveat:"The renamed issuer or as-of ticker could not be resolved by the configured vendor. Do not treat price unavailability as a trading loss or exclude it from the study denominator."};
 }
 if(raw.status!=="UNVALIDATED_HISTORICAL_CAP_RESEARCH_ONLY"||
  raw.cases.length!==1||raw.cases[0].caseId!==sources.caseId||
  raw.historicallyEligibleTrades!==0||raw.approvedRaasRatings!==0)
  throw Error("RAAS_2018_UNTRUSTED_PRICE_RESEARCH");
 const queue=assemble({primary,shares,rawCap:raw});
 const windows=win.build({primary,shares,rawCap:raw});
 const earlierWindows=studyEarlier({primary,shares,preentry:earlier,rawCap:raw});
 if(queue.summary.reviewedEligibleTradingEvents!==0||
  windows.summary.independentlyVerifiedEligibleTradingCases!==0||
  earlierWindows.summary.independentlyValidatedEventTrades!==0||
  windows.summary.optimalWindowDeclared||earlierWindows.summary.optimalWindowDeclared)
  throw Error("RAAS_2018_UNAPPROVED_TRADE_OR_GRADE_PROMOTION");
 return {...base,status:"2018_ACRX_RAW_CAP_RESEARCH_NOT_ELIGIBILITY",
  summary:{sourcePrograms2018:1,priceResearchSessions:raw.rawSessions,
   preliminaryCapInRangeSessions:raw.possible300mTo10bResearchSessions,
   windowPairsChecked:windows.summary.programWindowEvaluations,
   provisionalPriceAndCapWindows:windows.summary.provisionalWindowsWithCompletePriceAndTiming,
   addedEarlierShareWindows:earlierWindows.summary.newlyMeasurablePreentryWindows,
   approvedRaasScores:0,validatedTradingCases:0,fullTenYearCensusAudited:false},
  intakeReview:queue.cases,windowResearch:windows.cases,
  shareSnapshotsAndWindows:earlierWindows.cases,rawCapResearch:raw.cases,
  caveats:["One source-linked 2018 program is not the complete FDA event denominator.",
   "Issuer publicly announced November 3 PDUFA target; retrospective FDA internal goal was November 2; approval November 2. Do not rewrite original public target with action date.",
   "October 2017 DSUVIA CRL belongs to previous review cycle; not a separate issuer.",
   "Two SEC covers demonstrate 9.28m shares of growth and require actual offering/share/split reconciliation.",
   "Entry outside $300m–$10b is an excluded/provisional historical finding, never a fabricated positive trade or score.",
   "FDA decision and source evidence published after entry cannot become predictive features."]};
}
function main(){
 execute({key:process.env.APCA_API_KEY_ID||process.env.ALPACA_API_KEY_ID,
  secret:process.env.APCA_API_SECRET_KEY||process.env.ALPACA_SECRET_KEY})
 .then(x=>{
  const dest=process.env.RAAS_2018_ACRX_OUTPUT||
   path.join(root,"raas-2018-acrx-dsuvia-research.json");
  fs.mkdirSync(path.dirname(dest),{recursive:true});
  fs.writeFileSync(dest,JSON.stringify(x,null,2)+"\n");
  const named=x.shareSnapshotsAndWindows?.[0]?.namedWindowDiagnostics?.find(y=>
   y.entryLeadDays===79&&y.exitLeadDays===14);
  console.log(JSON.stringify({status:x.status,...x.summary,
   caseId:x.sources.caseId,
   reportedShareIncrease:x.sources.publishedCoverShareIncrease,
   plannedPublicTarget:x.sources.firstLocatedPublicPdufaTarget,
   fdaRetrospectiveGoal:x.sources.retrospectiveInternalFdaGoalDate,
   actionDate:x.sources.actualFdaActionDate,
   window79to14Reason:named?.reason??null,
   priceProviderGap:x.providerGapCode??null}));
  if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
   "### 2018 ACRX DSUVIA research: company PDUFA Nov 3 vs retrospective FDA goal Nov 2\n\n"+
   JSON.stringify(x.summary,null,2)+"\n\nNO historically approved trades or RAAS grades.\n");
  if(x.status==="BLOCKED_MISSING_ALPACA_CREDENTIALS")process.exitCode=1;
 }).catch(e=>{
  console.error("RAAS_2018_ACRX_FATAL_"+String(e.message).replace(/[^A-Z0-9_]/g,"_"));
  process.exitCode=1;
 });
}
if(require.main===module)main();
module.exports={verifySources,execute};
