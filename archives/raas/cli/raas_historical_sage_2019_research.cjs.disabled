#!/usr/bin/env node
"use strict";
/** A 2019 PDUFA + Phase 3 + dated SEC cover-share research case.
 * This source-led study cannot approve returns, trading cases, RAAS scores,
 * issuer-disjoint calibration or full-year PDUFA denominator completeness.
 * The 2019 FDA letter was subject to later DEA scheduling.
 */
const fs=require("node:fs"),path=require("node:path");
const {validateSourceLeads}=require("./raas_historical_event_census_worklist.cjs");
const cap=require("./raas_historical_raw_market_cap_research.cjs");
const {assemble}=require("./raas_historical_candidate_review_queue.cjs");
const windowStudy=require("./raas_historical_provisional_window_grid.cjs");
const {build:earlyShareStudy,validatePreentry}=require("./raas_historical_preentry_share_window_research.cjs");
const root=path.resolve(__dirname,"..");
const FILES={
 primary:"new-platform/frontend/data/raas-historical-2019-primary-source-leads.json",
 shares:"new-platform/frontend/data/raas-2019-sec-cover-share-leads.json",
 earlier:"new-platform/frontend/data/raas-preentry-2019-sec-cover-share-leads.json"
};
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
function verifySources(primary,shares,earlier){
 const events=validateSourceLeads(primary);
 if(events.length!==1||events[0].caseId!=="SAGE|ZULRESSO|NDA211371|2019"||
  events[0].ticker!=="SAGE"||events[0].application!=="NDA 211371"||
  events[0].pdufaTargetDate!=="2019-03-19"||
  events[0].initialPdufaTargetDate!=="2018-12-19"||
  events[0].targetAnnouncementDate!=="2018-11-20"||
  events[0].phase3ReadoutDate!=="2017-11-09"||
  events[0].actualFDAActionDate!=="2019-03-19"||
  events[0].actualFDAOutcome!=="APPROVED"||
  events[0].marketingDeferredPendingDEAScheduling!==true||
  !events[0].nctIds.includes("NCT02942004")||
  !events[0].nctIds.includes("NCT02942017")||
  !Array.isArray(shares.records)||shares.records.length!==1)
  throw Error("RAAS_2019_SAGE_FDA_SOURCE_INVALID");
 const late=cap.checkedLead(shares.records[0],events[0]);
 const previous=validatePreentry({primary,shares,preentry:earlier});
 if(previous.size!==1||!previous.has(events[0].caseId)||
  late.sharesOutstanding!==47092657||
  late.sharesMeasurementDate!=="2019-02-12"||
  late.filedDate!=="2019-02-19"||
  late.firstConservativeEntryDate!=="2019-02-20"||
  previous.get(events[0].caseId).sharesOutstanding!==46887174||
  previous.get(events[0].caseId).filedDate!=="2018-11-06"||
  previous.get(events[0].caseId).firstConservativeEntryDate!=="2018-11-07"||
  !late.needsShareContinuityAudit||!late.needsIndependentPriceCrosscheck)
  throw Error("RAAS_2019_SHARE_CHRONOLOGY_INVALID");
 return {caseId:events[0].caseId,year:2019,ticker:"SAGE",
  originalPdufaAnnouncementSourceUrl:events[0].targetAnnouncementSourceUrl,
  originalPhase3EvidenceSourceUrl:events[0].phase3ReadoutSourceUrl,
  historicalFDAActionSourceUrl:events[0].actualFDAActionSourceUrl,
  initialPdufaTargetDate:events[0].initialPdufaTargetDate,
  revisedPdufaTargetDate:events[0].pdufaTargetDate,
  fdaActionDate:events[0].actualFDAActionDate,
  fdaApprovalLetterMarketingCondition:"DEA_SCHEDULING_REQUIRED_BEFORE_EFFECTIVE_MARKETING",
  priorShareSourceUrl:previous.get(events[0].caseId).sourceUrl,
  laterShareSourceUrl:late.sourceUrl,
  priorPublishedShares:previous.get(events[0].caseId).sharesOutstanding,
  laterPublishedShares:late.sharesOutstanding,
  changeInPublishedCoverShares:late.sharesOutstanding-previous.get(events[0].caseId).sharesOutstanding};
}
const blockedSummary=()=>({sourcePrograms2019:1,priceResearchSessions:0,
 provisional300mTo10bSessions:0,provisionalWindows:0,
 supplementaryEarlierShareWindows:0,entryExitWindowsChecked:0,
 validatedEventTrades:0,approvedRaasScores:0,tenYearCensusComplete:false});
async function execute({primary=read(FILES.primary),shares=read(FILES.shares),
 earlier=read(FILES.earlier),key,secret,request=fetch}={}){
 const sources=verifySources(primary,shares,earlier);
 const basis={schemaVersion:1,scope:"RAAS_2019_SAGE_ZULRESSO_HISTORICAL_RESEARCH",sources};
 if(!key||!secret)return {...basis,status:"BLOCKED_MISSING_ALPACA_CREDENTIALS",
  summary:blockedSummary(),caveats:["Missing provider authentication is not evidence of missing historical prices."]};
 let raw;
 try{raw=await cap.execute({key,secret,request,events:primary,shares});}
 catch(err){
  // A delisted/acquired issuer may be unavailable through as-of symbols.
  // Record the explicit evidence gap without inventing a return. Other errors
  // (especially HTTP 401, 403, 429, 5xx and malformed responses) stay fatal.
  const code=String(err?.message||"");
  if(!/^RAAS_CAP_ALPACA_HTTP_(404|422)$/.test(code)&&
   code!=="RAAS_CAP_INSUFFICIENT_BARS")
   throw err;
  return {...basis,status:"BLOCKED_HISTORICAL_PRICE_OR_SYMBOL_UNAVAILABLE",
   summary:blockedSummary(),providerGapCode:code,
   caveats:["Failed to establish the historical SAGE ticker bars as of the original 2019 FDA review. This is not a zero return or exclusion of delisted companies.","Preserve original FDA 2019 target and dated SEC share-source facts for alternate authorized vendor reconciliation."]};
 }
 if(raw.status!=="UNVALIDATED_HISTORICAL_CAP_RESEARCH_ONLY"||
  raw.cases.length!==1||raw.cases[0].caseId!==sources.caseId||
  raw.historicallyEligibleTrades!==0||raw.approvedRaasRatings!==0)
  throw Error("RAAS_2019_PRICE_SOURCE_OUTSIDE_RESEARCH_SCOPE");
 const audit=assemble({primary,shares,rawCap:raw});
 const windows=windowStudy.build({primary,shares,rawCap:raw});
 const earlierWindows=earlyShareStudy({primary,shares,preentry:earlier,rawCap:raw});
 if(audit.summary.reviewedEligibleTradingEvents!==0||
  windows.summary.independentlyVerifiedEligibleTradingCases!==0||
  earlierWindows.summary.independentlyValidatedEventTrades!==0||
  windows.summary.optimalWindowDeclared||earlierWindows.summary.optimalWindowDeclared)
  throw Error("RAAS_2019_SCORE_PROMOTION_FORBIDDEN");
 return {...basis,status:"2019_SAGE_PRICE_RESEARCH_NOT_CALIBRATION_READY",
  summary:{sourcePrograms2019:1,priceResearchSessions:raw.rawSessions,
   provisional300mTo10bSessions:raw.possible300mTo10bResearchSessions,
   provisionalWindows:windows.summary.provisionalWindowsWithCompletePriceAndTiming,
   supplementaryEarlierShareWindows:earlierWindows.summary.newlyMeasurablePreentryWindows,
   entryExitWindowsChecked:windows.summary.programWindowEvaluations,
   validatedEventTrades:0,approvedRaasScores:0,tenYearCensusComplete:false},
  originalSourceAudit:audit.cases,
  primaryShareWindowDiagnostics:windows.cases,
  earlyShareWindowDiagnostics:earlierWindows.cases,
  rawCapResearch:raw.cases,
  caveats:["One NDA from 2019 does not represent a complete 2019 PDUFA outcome census.",
   "Nov 2018 REMS extension replaces the original December target and was public before the studied entry window.",
   "FDA letter dated March 19 2019 explicitly conditions legal drug marketing on later DEA controlled-substance scheduling.",
   "No approved trade return, point-in-time corporate-action/share audit, or issuer-disjoint calibration."]};
}
function main(){
 const env=process.env;
 execute({key:env.APCA_API_KEY_ID||env.ALPACA_API_KEY_ID,
  secret:env.APCA_API_SECRET_KEY||env.ALPACA_SECRET_KEY})
 .then(r=>{
  const out=env.RAAS_2019_SAGE_OUTPUT||path.join(root,"raas-2019-sage-zulresso-research.json");
  fs.mkdirSync(path.dirname(out),{recursive:true});
  fs.writeFileSync(out,JSON.stringify(r,null,2)+"\n");
  console.log(JSON.stringify({status:r.status,...r.summary,
   caseId:r.sources.caseId,shareCountChange:r.sources.changeInPublishedCoverShares,
   priceProviderGap:r.providerGapCode??null,
   window79to14:r.earlyShareWindowDiagnostics?.[0]?.namedWindowDiagnostics.find(x=>
    x.entryLeadDays===79&&x.exitLeadDays===14)?.reason??null}));
  if(env.GITHUB_STEP_SUMMARY)fs.appendFileSync(env.GITHUB_STEP_SUMMARY,
   "### SAGE 2019 FDA original source and price research only\n\n"+
   JSON.stringify(r.summary,null,2)+"\n\n0 verified trades or RAAS scores. DEA market authorization caveat applies.\n");
  if(r.status==="BLOCKED_MISSING_ALPACA_CREDENTIALS")process.exitCode=1;
 }).catch(e=>{
  console.error("RAAS_2019_SAGE_FATAL_"+String(e.message).replace(/[^A-Z0-9_]/g,"_"));
  process.exitCode=1;
 });
}
if(require.main===module)main();
module.exports={verifySources,execute};
