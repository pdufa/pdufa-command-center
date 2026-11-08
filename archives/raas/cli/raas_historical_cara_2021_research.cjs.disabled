#!/usr/bin/env node
"use strict";
/**
 * One additional 2021 program for the incomplete 2016–2025 PDUFA research
 * universe, independent of the 2020 case queue. All trading windows, cap
 * estimates, issuer share snapshots and returns remain unvalidated.
 */
const fs=require("node:fs"),path=require("node:path");
const {validateSourceLeads}=require("./raas_historical_event_census_worklist.cjs");
const cap=require("./raas_historical_raw_market_cap_research.cjs");
const {assemble}=require("./raas_historical_candidate_review_queue.cjs");
const windowStudy=require("./raas_historical_provisional_window_grid.cjs");
const {build:earlyShareStudy,validatePreentry}=require("./raas_historical_preentry_share_window_research.cjs");
const root=path.resolve(__dirname,"..");
const FILES={
 primary:"new-platform/frontend/data/raas-historical-2021-primary-source-leads.json",
 shares:"new-platform/frontend/data/raas-2021-sec-cover-share-leads.json",
 earlier:"new-platform/frontend/data/raas-preentry-2021-sec-cover-share-leads.json"
};
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
function verifySources(primary,shares,earlier){
 const events=validateSourceLeads(primary);
 if(events.length!==1||events[0].ticker!=="CARA"||
  events[0].caseId!=="CARA|KORSUVA|NDA214916|2021"||
  events[0].application!=="NDA 214916"||
  events[0].pdufaTargetDate!=="2021-08-23"||
  events[0].actualFDAActionDate!=="2021-08-23"||
  events[0].actualFDAOutcome!=="APPROVED"||
  events[0].targetAnnouncementDate!=="2021-03-08"||
  events[0].phase3ReadoutDate!=="2020-04-21"||
  !events[0].nctIds.includes("NCT03636269")||
  !events[0].nctIds.includes("NCT03422653")||
  !Array.isArray(shares.records)||shares.records.length!==1)
  throw Error("RAAS_2021_SOURCE_PROGRAM_IDENTITY_INVALID");
 const cover=cap.checkedLead(shares.records[0],events[0]);
 const previous=validatePreentry({primary,shares,preentry:earlier});
 if(previous.size!==1||!previous.has(events[0].caseId)||
  cover.sharesOutstanding!==50052011||
  cover.sharesMeasurementDate!=="2021-05-06"||
  cover.filedDate!=="2021-05-10"||
  cover.firstConservativeEntryDate!=="2021-05-11"||
  previous.get(events[0].caseId).sharesOutstanding!==49876763||
  previous.get(events[0].caseId).filedDate!=="2021-02-25"||
  previous.get(events[0].caseId).firstConservativeEntryDate!=="2021-02-26"||
  !cover.needsShareContinuityAudit||!cover.needsIndependentPriceCrosscheck)
  throw Error("RAAS_2021_HISTORICAL_SHARE_CHRONOLOGY_INVALID");
 return {caseId:events[0].caseId,year:2021,ticker:events[0].ticker,
  originalFDAApprovalSourceUrl:events[0].actualFDAActionSourceUrl,
  originalPdufaSourceUrl:events[0].targetAnnouncementSourceUrl,
  originalPhase3SourceUrl:events[0].phase3ReadoutSourceUrl,
  lastPreEntryShareFactSourceUrl:cover.sourceUrl,
  earlierShareFactSourceUrl:previous.get(events[0].caseId).sourceUrl,
  earlierPublishedShares:previous.get(events[0].caseId).sharesOutstanding,
  laterPublishedShares:cover.sharesOutstanding,
  publishedShareCountChange:cover.sharesOutstanding-previous.get(events[0].caseId).sharesOutstanding};
}
async function execute({primary=read(FILES.primary),shares=read(FILES.shares),
 earlier=read(FILES.earlier),key,secret,request=fetch}={}){
 const sources=verifySources(primary,shares,earlier);
 if(!key||!secret)return {schemaVersion:1,
  scope:"RAAS_2021_CARA_KORSUVA_HISTORICAL_RESEARCH",
  status:"BLOCKED_MISSING_ALPACA_CREDENTIALS",sources,
  summary:{sourcePrograms2021:1,programsWithDated2021Shares:1,
   priceResearchSessions:0,provisionalWindows:0,validatedEventTrades:0,
   approvedRaasScores:0,tenYearCensusComplete:false}};
 const raw=await cap.execute({key,secret,request,events:primary,shares});
 if(raw.status!=="UNVALIDATED_HISTORICAL_CAP_RESEARCH_ONLY"||
  raw.cases.length!==1||raw.cases[0].caseId!==sources.caseId||
  raw.historicallyEligibleTrades!==0||raw.approvedRaasRatings!==0)
  throw Error("RAAS_2021_LIVE_RAW_CAP_NOT_IN_RESEARCH_STATE");
 const review=assemble({primary,shares,rawCap:raw});
 const windows=windowStudy.build({primary,shares,rawCap:raw});
 const shareChronology=earlyShareStudy({primary,shares,preentry:earlier,rawCap:raw});
 if(review.summary.reviewedEligibleTradingEvents!==0||
  windows.summary.independentlyVerifiedEligibleTradingCases!==0||
  shareChronology.summary.independentlyValidatedEventTrades!==0||
  windows.summary.optimalWindowDeclared||shareChronology.summary.optimalWindowDeclared)
  throw Error("RAAS_2021_UNAPPROVED_RESEARCH_PROMOTION");
 return {schemaVersion:1,scope:"RAAS_2021_CARA_KORSUVA_HISTORICAL_RESEARCH",
  status:"2021_RESEARCH_ONLY_NOT_CALIBRATION_READY",sources,
  summary:{sourcePrograms2021:1,programsWithDated2021Shares:1,
   priceResearchSessions:raw.rawSessions,
   provisional300mTo10bSessions:raw.possible300mTo10bResearchSessions,
   provisionalWindows:windows.summary.provisionalWindowsWithCompletePriceAndTiming,
   entryExitWindowsChecked:windows.summary.programWindowEvaluations,
   validatedEventTrades:0,approvedRaasScores:0,tenYearCensusComplete:false},
  sourceAudit:review.cases,
  perCaseWindowDiagnostics:windows.cases,
  shareSnapshotResearch:shareChronology.cases,
  rawCapResearch:raw.cases,
  caveats:["One source-linked 2021 FDA program cannot establish a complete 2021 cohort or 10-year performance.",
   "SEC cover facts do not establish daily diluted share counts, rights, float or stock-split treatment.",
   "Alpaca raw and adjusted prices require independent corporate-action and vendor reconciliation.",
   "Do not select, rank or recommend entry/exit strategies from these unapproved study observations."]};
}
function main(){
 const env=process.env;
 execute({key:env.APCA_API_KEY_ID||env.ALPACA_API_KEY_ID,
  secret:env.APCA_API_SECRET_KEY||env.ALPACA_SECRET_KEY})
 .then(r=>{
  const out=env.RAAS_2021_CARA_OUTPUT||path.join(root,"raas-2021-cara-korsuva-research.json");
  fs.mkdirSync(path.dirname(out),{recursive:true});
  fs.writeFileSync(out,JSON.stringify(r,null,2)+"\n");
  console.log(JSON.stringify({status:r.status,...r.summary,
   ticker:r.sources.ticker,
   publishedShareCountChange:r.sources.publishedShareCountChange,
   window79to14:r.perCaseWindowDiagnostics?.[0]?.namedWindowDiagnostics.find(x=>
    x.entryLeadDays===79&&x.exitLeadDays===14)?.reason??null}));
  if(env.GITHUB_STEP_SUMMARY)fs.appendFileSync(env.GITHUB_STEP_SUMMARY,
   "### 2021 CARA FDA program: source and market-cap research only\n\n"+
   JSON.stringify(r.summary,null,2)+"\n\nNo verified trades, holdout or RAAS score.\n");
  if(r.status==="BLOCKED_MISSING_ALPACA_CREDENTIALS")process.exitCode=1;
 }).catch(e=>{
  console.error("RAAS_2021_CARA_FATAL_"+String(e.message).replace(/[^A-Z0-9_]/g,"_"));
  process.exitCode=1;
 });
}
if(require.main===module)main();
module.exports={verifySources,execute};
