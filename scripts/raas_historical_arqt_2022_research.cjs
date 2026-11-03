#!/usr/bin/env node
"use strict";
/**
 * Additional 2022 FDA program: ARQT/Zoryve 0.3% plaque psoriasis.
 * Point-in-time PDUFA/Phase3 source and SEC raw-share/price research only.
 * No historical trading case, score, or 2016–2025 coverage is approved.
 */
const fs=require("node:fs"),path=require("node:path");
const {validateSourceLeads}=require("./raas_historical_event_census_worklist.cjs");
const cap=require("./raas_historical_raw_market_cap_research.cjs");
const {assemble}=require("./raas_historical_candidate_review_queue.cjs");
const windowStudy=require("./raas_historical_provisional_window_grid.cjs");
const {build:earlyShareStudy,validatePreentry}=require("./raas_historical_preentry_share_window_research.cjs");
const root=path.resolve(__dirname,"..");
const F={
 primary:"new-platform/frontend/data/raas-historical-2022-primary-source-leads.json",
 shares:"new-platform/frontend/data/raas-2022-sec-cover-share-leads.json",
 earlier:"new-platform/frontend/data/raas-preentry-2022-sec-cover-share-leads.json"
};
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
function verifySources(primary,shares,earlier){
 const events=validateSourceLeads(primary);
 if(events.length!==1||events[0].ticker!=="ARQT"||
  events[0].caseId!=="ARQT|ZORYVE_CREAM|NDA215985|2022"||
  events[0].application!=="NDA 215985"||
  events[0].pdufaTargetDate!=="2022-07-29"||
  events[0].actualFDAActionDate!=="2022-07-29"||
  events[0].targetAnnouncementDate!=="2021-12-22"||
  events[0].phase3ReadoutDate!=="2021-02-01"||
  events[0].actualFDAOutcome!=="APPROVED"||
  !events[0].nctIds.includes("NCT04211363")||
  !events[0].nctIds.includes("NCT04211389")||
  !Array.isArray(shares.records)||shares.records.length!==1)
  throw Error("RAAS_2022_PRIMARY_IDENTITY_INVALID");
 const s=cap.checkedLead(shares.records[0],events[0]);
 const prior=validatePreentry({primary,shares,preentry:earlier});
 if(prior.size!==1||!prior.has(events[0].caseId)||
  s.sharesOutstanding!==51417963||
  s.sharesMeasurementDate!=="2022-04-29"||
  s.filedDate!=="2022-05-05"||
  s.firstConservativeEntryDate!=="2022-05-06"||
  prior.get(events[0].caseId).sharesOutstanding!==50380254||
  prior.get(events[0].caseId).filedDate!=="2022-02-22"||
  prior.get(events[0].caseId).firstConservativeEntryDate!=="2022-02-23"||
  !s.needsShareContinuityAudit||!s.needsIndependentPriceCrosscheck)
  throw Error("RAAS_2022_SHARE_SOURCE_INVALID");
 return {caseId:events[0].caseId,year:2022,ticker:"ARQT",
  originalFDAApprovalUrl:events[0].actualFDAActionSourceUrl,
  originalPdufaAnnouncementUrl:events[0].targetAnnouncementSourceUrl,
  originalPhase3ReadoutUrl:events[0].phase3ReadoutSourceUrl,
  earlierShareFactUrl:prior.get(events[0].caseId).sourceUrl,
  laterShareFactUrl:s.sourceUrl,
  earlierShares:prior.get(events[0].caseId).sharesOutstanding,
  laterShares:s.sharesOutstanding,
  changeInPublishedCoverShares:s.sharesOutstanding-prior.get(events[0].caseId).sharesOutstanding};
}
async function execute({primary=read(F.primary),shares=read(F.shares),
 earlier=read(F.earlier),key,secret,request=fetch}={}){
 const sources=verifySources(primary,shares,earlier);
 if(!key||!secret)return {schemaVersion:1,scope:"RAAS_2022_ARQT_ZORYVE_HISTORICAL_RESEARCH",
  status:"BLOCKED_MISSING_ALPACA_CREDENTIALS",sources,
  summary:{sourcePrograms2022:1,priceResearchSessions:0,preliminaryWindows:0,
   validatedEventTrades:0,approvedRaasScores:0,tenYearCensusComplete:false}};
 const raw=await cap.execute({key,secret,request,events:primary,shares});
 if(raw.status!=="UNVALIDATED_HISTORICAL_CAP_RESEARCH_ONLY"||
  raw.cases.length!==1||raw.cases[0].caseId!==sources.caseId||
  raw.historicallyEligibleTrades!==0||raw.approvedRaasRatings!==0)
  throw Error("RAAS_2022_LIVE_DATA_NOT_RESEARCH_ONLY");
 const review=assemble({primary,shares,rawCap:raw});
 const windows=windowStudy.build({primary,shares,rawCap:raw});
 const shareChronology=earlyShareStudy({primary,shares,preentry:earlier,rawCap:raw});
 if(review.summary.reviewedEligibleTradingEvents!==0||
  windows.summary.independentlyVerifiedEligibleTradingCases!==0||
  shareChronology.summary.independentlyValidatedEventTrades!==0||
  windows.summary.optimalWindowDeclared||shareChronology.summary.optimalWindowDeclared)
  throw Error("RAAS_2022_SCORE_PROMOTION_FORBIDDEN");
 return {schemaVersion:1,scope:"RAAS_2022_ARQT_ZORYVE_HISTORICAL_RESEARCH",
  status:"2022_RESEARCH_ONLY_NOT_CALIBRATION_READY",sources,
  summary:{sourcePrograms2022:1,priceResearchSessions:raw.rawSessions,
   provisional300mTo10bSessions:raw.possible300mTo10bResearchSessions,
   provisionalWindows:windows.summary.provisionalWindowsWithCompletePriceAndTiming,
   newlyMeasurableEarlierShareWindows:shareChronology.summary.newlyMeasurablePreentryWindows,
   windowsChecked:windows.summary.programWindowEvaluations,
   validatedEventTrades:0,approvedRaasScores:0,tenYearCensusComplete:false},
  sourceAudit:review.cases,perCaseWindowDiagnostics:windows.cases,
  earlierShareWindowDiagnostics:shareChronology.cases,rawCapResearch:raw.cases,
  caveats:["Only one 2022 case; not a complete 2022 approval, CRL, withdrawal or extension census.",
   "No independent as-of raw price / share-class / split / dilution reconciliation.",
   "Issuer annual and quarterly cover shares are dated snapshots, not continuous outstanding share histories.",
   "No real PDUFA entry/exit edge or RAAS calibration is approved."]};
}
function main(){
 const env=process.env;
 execute({key:env.APCA_API_KEY_ID||env.ALPACA_API_KEY_ID,
  secret:env.APCA_API_SECRET_KEY||env.ALPACA_SECRET_KEY}).then(r=>{
  const dest=env.RAAS_2022_ARQT_OUTPUT||path.join(root,"raas-2022-arqt-zoryve-research.json");
  fs.mkdirSync(path.dirname(dest),{recursive:true});
  fs.writeFileSync(dest,JSON.stringify(r,null,2)+"\n");
  const w=r.perCaseWindowDiagnostics?.[0]?.namedWindowDiagnostics.find(x=>
   x.entryLeadDays===79&&x.exitLeadDays===14);
  console.log(JSON.stringify({status:r.status,...r.summary,
   caseId:r.sources.caseId,publishedCoverShareChange:r.sources.changeInPublishedCoverShares,
   window79to14:w?.reason??null}));
  if(env.GITHUB_STEP_SUMMARY)fs.appendFileSync(env.GITHUB_STEP_SUMMARY,
   "### 2022 ARQT NDA215985 research-only case\n\n"+
   JSON.stringify(r.summary,null,2)+"\n\nNo validated trades, 10-year census or RAAS metric score.\n");
  if(r.status==="BLOCKED_MISSING_ALPACA_CREDENTIALS")process.exitCode=1;
 }).catch(e=>{console.error("RAAS_2022_ARQT_FATAL_"+String(e.message).replace(/[^A-Z0-9_]/g,"_"));process.exitCode=1;});
}
if(require.main===module)main();
module.exports={verifySources,execute};
