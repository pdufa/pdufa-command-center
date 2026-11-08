#!/usr/bin/env node
"use strict";
/**
 * 2017 PTCT Translarna CRL historical research. Distinguish original NDA
 * filing-over-protest, prior refuse-to-file, primary Phase 3 failure,
 * publicly announced PDUFA and first-public CRL disclosure. The *original*
 * FDA CRL letter date remains unverified: 2017-10-25 is a public-disclosure
 * proxy in this research fixture, NOT an independently audited FDA action.
 *
 * No entry/exit trade, final cap eligibility, return or RAAS score is approved.
 */
const fs=require("node:fs"),path=require("node:path");
const {validateSourceLeads}=require("./raas_historical_event_census_worklist.cjs");
const cap=require("./raas_historical_raw_market_cap_research.cjs");
const {assemble}=require("./raas_historical_candidate_review_queue.cjs");
const windows=require("./raas_historical_provisional_window_grid.cjs");
const {build:studyEarlier,validatePreentry}=require("./raas_historical_preentry_share_window_research.cjs");
const root=path.resolve(__dirname,"..");
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const FILES={
 primary:"new-platform/frontend/data/raas-historical-2017-primary-source-leads.json",
 shares:"new-platform/frontend/data/raas-2017-sec-cover-share-leads.json",
 earlier:"new-platform/frontend/data/raas-preentry-2017-sec-cover-share-leads.json"
};
function verifySources(primary,shares,earlier){
 const validated=validateSourceLeads(primary),e=validated[0];
 if(validated.length!==1||e.caseId!=="PTCT|TRANSLARNA|NDA200896|2017"||
  e.ticker!=="PTCT"||e.application!=="NDA 200896"||
  e.pdufaTargetDate!=="2017-10-24"||
  e.targetAnnouncementDate!=="2017-03-06"||
  e.phase3ReadoutDate!=="2015-10-15"||
  e.actualFDAActionDate!=="2017-10-25"||
  e.actualFDAOutcome!=="CRL"||
  e.firstPublicFDAActionAnnouncementDate!=="2017-10-25"||
  e.actualFDAActionDateBasis!=="COMPANY_FIRST_PUBLIC_2017_10_25_DISCLOSURE_NOT_FDA_LETTER_DATE"||
  e.originalFdaCrlLetterDateIndependentlyVerified!==false||
  e.fileOverProtestAfterRefuseToFile!==true||
  e.earlier2016RefuseToFileNotA2017CRL!==true||
  e.phase3OverallIttPrimaryEndpointSignificant!==false||
  e.phase3OverallIttPrimaryEndpointP!==0.213||
  !e.nctIds.includes("NCT01826487")||
  !Array.isArray(shares.records)||shares.records.length!==1)
  throw Error("RAAS_2017_FDA_CRL_OR_TIMING_INVALID");
 const later=cap.checkedLead(shares.records[0],e);
 const previous=validatePreentry({primary,shares,preentry:earlier});
 const first=previous.get(e.caseId);
 if(previous.size!==1||!first||
  later.sharesOutstanding!==41389046||
  later.sharesMeasurementDate!=="2017-08-04"||
  later.filedDate!=="2017-08-09"||
  later.firstConservativeEntryDate!=="2017-08-10"||
  first.sharesOutstanding!==41244004||
  first.sharesMeasurementDate!=="2017-05-05"||
  first.filedDate!=="2017-05-08"||
  first.firstConservativeEntryDate!=="2017-05-09"||
  !later.needsShareContinuityAudit||!later.needsIndependentPriceCrosscheck)
  throw Error("RAAS_2017_DATED_SHARES_SOURCE_INVALID");
 return {caseId:e.caseId,ticker:"PTCT",year:2017,
  originalPublicPdufaGoal:e.pdufaTargetDate,
  originalTargetAnnouncementUrl:e.targetAnnouncementSourceUrl,
  original2015Phase3ResultsUrl:e.phase3ReadoutSourceUrl,
  original2017CrlPublicAnnouncementUrl:e.actualFDAActionSourceUrl,
  fdaOutcome:"CRL",phase3PrimaryIttP:0.213,
  originalFdaLetterDateVerified:false,
  firstPublicCrlDisclosureDate:e.firstPublicFDAActionAnnouncementDate,
  researchActionDateProxy:e.actualFDAActionDate,
  earlierShareSourceUrl:first.sourceUrl,
  laterShareSourceUrl:later.sourceUrl,
  earlierPublishedShares:first.sharesOutstanding,
  laterPublishedShares:later.sharesOutstanding,
  publishedShareCountChange:later.sharesOutstanding-first.sharesOutstanding,
  financingReviewFlag:"2017_EMFLAZA_6_683_598_SHARE_ACQUISITION_PRIOR_TO_THE_TWO_COVER_FACTS"};
}
const emptySummary=()=>({sourcePrograms2017:1,
 priceResearchSessions:0,provisionalCapInRangeSessions:0,
 programWindowPairsEvaluated:0,provisionalCompletePriceWindows:0,
 earlierShareWindowAdds:0,validatedTradingCases:0,approvedRaasScores:0,
 fullTenYearCensusAudited:false});
async function execute({primary=read(FILES.primary),shares=read(FILES.shares),
 earlier=read(FILES.earlier),key,secret,request=fetch}={}){
 const sourceAudit=verifySources(primary,shares,earlier);
 const base={schemaVersion:1,scope:"RAAS_2017_PTCT_TRANSLARNA_CRL_RESEARCH",
  caseId:sourceAudit.caseId,sourceAudit};
 if(!key||!secret)return {...base,status:"BLOCKED_MISSING_ALPACA_CREDENTIALS",
  summary:emptySummary()};
 let raw;
 try{raw=await cap.execute({key,secret,request,events:primary,shares});}
 catch(error){
  const code=String(error?.message||"");
  if(!/^RAAS_CAP_ALPACA_HTTP_(404|422)$/.test(code)&&
    code!=="RAAS_CAP_INSUFFICIENT_BARS")throw error;
  return {...base,status:"BLOCKED_HISTORICAL_SYMBOL_PRICE_GAP",
   providerGapCode:code,summary:emptySummary(),
   interpretation:"Missing historical vendor bars are not zero stock returns and not evidence of market-cap ineligibility."};
 }
 if(raw.status!=="UNVALIDATED_HISTORICAL_CAP_RESEARCH_ONLY"||
  raw.cases.length!==1||raw.cases[0].caseId!==sourceAudit.caseId||
  raw.historicallyEligibleTrades!==0||raw.approvedRaasRatings!==0)
  throw Error("RAAS_2017_UNTRUSTED_RAW_RESEARCH");
 const queue=assemble({primary,shares,rawCap:raw});
 const priceWindows=windows.build({primary,shares,rawCap:raw});
 const earlierShares=studyEarlier({primary,shares,preentry:earlier,rawCap:raw});
 if(queue.summary.reviewedEligibleTradingEvents!==0||
  priceWindows.summary.independentlyVerifiedEligibleTradingCases!==0||
  earlierShares.summary.independentlyValidatedEventTrades!==0||
  priceWindows.summary.optimalWindowDeclared||earlierShares.summary.optimalWindowDeclared)
  throw Error("RAAS_2017_PREMATURE_TRADE_SCORE_PROMOTION");
 return {...base,status:"2017_CRL_RESEARCH_ONLY",
  summary:{sourcePrograms2017:1,
   priceResearchSessions:raw.rawSessions,
   provisionalCapInRangeSessions:raw.possible300mTo10bResearchSessions,
   programWindowPairsEvaluated:priceWindows.summary.programWindowEvaluations,
   provisionalCompletePriceWindows:priceWindows.summary.provisionalWindowsWithCompletePriceAndTiming,
   earlierShareWindowAdds:earlierShares.summary.newlyMeasurablePreentryWindows,
   validatedTradingCases:0,approvedRaasScores:0,fullTenYearCensusAudited:false},
  sourceReviewQueue:queue.cases,
  mainWindowResearch:priceWindows.cases,
  shareSnapshotWindowResearch:earlierShares.cases,
  rawCapResearch:raw.cases,
  caveats:["The 2017 FDA CRL letter's actual date is NOT independently verified; 2017-10-25 is first public issuer disclosure, a censored research proxy only.",
   "ACT DMD original Phase 3 ITT endpoint p=0.213 did not meet significance; do not select favorable post-hoc subgroup as substitute primary result.",
   "The 2016 Refuse to File was not the 2017 CRL, and the 2024/2026 NDA cycle is unrelated to this 2017 event.",
   "The 2017 EMFLAZA acquisition included 6,683,598 shares issued before these Q1 and Q2 covers; each entry needs separate share and corporate action verification.",
   "A single 2017 negative outcome cannot establish a year denominator, predictive RAAS calibration or investment strategy."]};
}
function main(){
 execute({key:process.env.APCA_API_KEY_ID||process.env.ALPACA_API_KEY_ID,
  secret:process.env.APCA_API_SECRET_KEY||process.env.ALPACA_SECRET_KEY})
 .then(r=>{
  const dest=process.env.RAAS_2017_PTCT_OUTPUT||
   path.join(root,"raas-2017-ptct-translarna-research.json");
  fs.mkdirSync(path.dirname(dest),{recursive:true});
  fs.writeFileSync(dest,JSON.stringify(r,null,2)+"\n");
  const named=r.shareSnapshotWindowResearch?.[0]?.namedWindowDiagnostics?.find(w=>
   w.entryLeadDays===79&&w.exitLeadDays===14);
  console.log(JSON.stringify({status:r.status,...r.summary,
   ticker:r.sourceAudit.ticker,programOutcome:r.sourceAudit.fdaOutcome,
   publicPdufa:r.sourceAudit.originalPublicPdufaGoal,
   publicCrlDisclosure:r.sourceAudit.firstPublicCrlDisclosureDate,
   exactFDAletterDateVerified:r.sourceAudit.originalFdaLetterDateVerified,
   shareIncrease:r.sourceAudit.publishedShareCountChange,
   window79to14:named?.reason??null,priceGap:r.providerGapCode??null}));
  if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
   "### 2017 PTCT Translarna incomplete CRL research only\n\n"+
   JSON.stringify(r.summary,null,2)+"\n\nOriginal FDA CRL-letter date not verified. Never approve trades, returns or RAAS scores.\n");
  if(r.status==="BLOCKED_MISSING_ALPACA_CREDENTIALS")process.exitCode=1;
 }).catch(e=>{
  console.error("RAAS_2017_PTCT_FATAL_"+String(e.message).replace(/[^A-Z0-9_]/g,"_"));
  process.exitCode=1;
 });
}
if(require.main===module)main();
module.exports={verifySources,execute};
