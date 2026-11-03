#!/usr/bin/env node
"use strict";
/**
 * Research-only bridge between individually located 2020 FDA sources,
 * historical SEC cover shares, and the 2016–2025 study intake.
 *
 * Generates a review queue, NOT SOURCE_REVIEWED records or numeric RAAS scores.
 * It never mutates the authoritative ten-year intake or approved ratings ledger.
 */
const fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"..");
const {validateSourceLeads}=require("./raas_historical_event_census_worklist.cjs");
const {checkedLead,issuerExposureDiagnostics}=require("./raas_historical_raw_market_cap_research.cjs");
const readJson=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const PRIMARY="new-platform/frontend/data/raas-historical-2020-primary-source-leads.json";
const SHARES="new-platform/frontend/data/raas-2020-sec-cover-share-leads.json";
const RAAS_CAP_SCOPE="RAAS_HISTORIC_RAW_CAP_RESEARCH";
function assemble({primary,shares,rawCap=null}){
 const events=validateSourceLeads(primary);
 if(!shares||shares.scope!=="RAAS_MANUALLY_LOCATED_SEC_HISTORIC_COMMON_SHARE_RESEARCH"||
   !Array.isArray(shares.records))throw Error("RAAS_REVIEW_QUEUE_INVALID_SHARE_INPUT");
 const eventByCase=new Map(events.map(e=>[e.caseId,e])),shareByCase=new Map();
 for(const s of shares.records){
  if(!s||shareByCase.has(s.caseId)||!eventByCase.has(s.caseId))
   throw Error("RAAS_REVIEW_QUEUE_UNMATCHED_OR_DUPLICATE_SHARES");
  checkedLead(s,eventByCase.get(s.caseId));shareByCase.set(s.caseId,s);
 }
 if(rawCap!==null && (!rawCap||rawCap.scope!==RAAS_CAP_SCOPE||
  rawCap.status!=="UNVALIDATED_HISTORICAL_CAP_RESEARCH_ONLY"||
  !Array.isArray(rawCap.cases)||rawCap.approvedRaasRatings!==0||
  rawCap.historicallyEligibleTrades!==0))
  throw Error("RAAS_REVIEW_QUEUE_INVALID_RAW_RESEARCH_SCOPE");
 const rawByCase=new Map();
 for(const c of rawCap?.cases??[]){
  const event=eventByCase.get(c?.caseId);
  if(!event||rawByCase.has(c.caseId)||!shareByCase.has(c.caseId)||
   c.ticker!==event.ticker||c.pdufaTargetDate!==event.pdufaTargetDate||
   c.actualFDAActionDate!==event.actualFDAActionDate||
   c.status!=="RAW_MARKET_CAP_DIAGNOSTICS_NOT_PROVEN_TRADING_ELIGIBILITY"||
   c.approvedRaasRatings!==0||c.eventTradeCasesValidated!==0||
   !Array.isArray(c.observations))throw Error("RAAS_REVIEW_QUEUE_UNTRUSTED_RAW_CASE");
  for(const o of c.observations){
   if(!o||!/^\d{4}-\d{2}-\d{2}$/.test(o.session)||
    o.beforeActualFDAAction!==(o.session<event.actualFDAActionDate)||
    (o.within300mTo10bUnreviewed===true&&
      (o.historicMarketCapResearchMillions===null||
       o.historicMarketCapResearchMillions<300||
       o.historicMarketCapResearchMillions>10000)))
    throw Error("RAAS_REVIEW_QUEUE_RAW_PRE_ACTION_GUARD");
  }
  rawByCase.set(c.caseId,c);
 }
 const queue=events.map(e=>{
  const s=shareByCase.get(e.caseId),r=rawByCase.get(e.caseId);
  const observations=(r?.observations??[]).filter(o=>o.beforeActualFDAAction===true &&
   o.historicMarketCapResearchMillions!==null);
  const provisionalInRangeSessions=observations.filter(o=>o.within300mTo10bUnreviewed===true).length;
  const blockers=[
   "FULL_2016_2025_EVENT_CENSUS_AND_MISSING_OUTCOMES",
   "FIRST_EVER_PUBLIC_PDUFA_DATE_AUDIT",
   "PROGRAM_APPLICATION_AND_REVIEW_CYCLE_VALIDATION",
   "HISTORICAL_ISSUER_LISTING_ADR_CORPORATE_ACTION_AUDIT",
   "INDEPENDENT_PRICE_AND_ENTRY_DAY_CAP_AUDIT",
   "FDA_ACTION_DISCLOSURE_TIMING_AND_EARLY_EXIT_CENSOR",
   "ISSUER_DISJOINT_TRAIN_HOLDOUT_VALIDATION",
   "60_RAAS_METRIC_CALIBRATION_APPROVAL"
  ];
  if(!s)blockers.unshift("MISSING_DATED_US_COMMON_SHARE_OR_ADR_CONVERSION_SOURCE");
  if(!r)blockers.unshift("MISSING_LIVE_ALPACA_RAW_CAP_RESEARCH");
  if(r&&provisionalInRangeSessions===0)blockers.unshift("NO_PROVISIONAL_PRE_ACTION_IN_RANGE_SESSIONS");
  return {caseId:e.caseId,ticker:e.ticker,programId:e.programId,
   application:e.application,nctIds:e.nctIds,
   pdufaTargetDate:e.pdufaTargetDate,firstLocatedPublicTargetDate:e.targetAnnouncementDate,
   firstLocatedPublicTargetSourceUrl:e.targetAnnouncementSourceUrl,
   phase3ReadoutDate:e.phase3ReadoutDate,phase3ReadoutSourceUrl:e.phase3ReadoutSourceUrl,
   actualFDAActionDate:e.actualFDAActionDate,actualFDAOutcome:e.actualFDAOutcome,
   actualFDAActionSourceUrl:e.actualFDAActionSourceUrl,
   shareSourceAvailable:Boolean(s),sharesMeasurementDate:s?.sharesMeasurementDate??null,
   shareSourcePublishedAt:s?.filedDate??null,shareSourceFirstSafeResearchDate:s?.firstConservativeEntryDate??null,
   shareSourceUrl:s?.sourceUrl??null,
   observedPreActionResearchSessions:observations.length,
   provisionalPreAction300mTo10bSessions:provisionalInRangeSessions,
   reviewedEligibleTradingEvents:0,approvedRaasScores:0,
   tenYearIntakeStatus:"DO_NOT_PROMOTE_REQUIRES_INDEPENDENT_REVIEW",
   pendingVerification: blockers};
 });
 const exposed=issuerExposureDiagnostics(events);
 const withShares=new Set(queue.filter(c=>c.shareSourceAvailable).map(c=>c.ticker));
 const withRaw=new Set(queue.filter(c=>rawByCase.has(c.caseId)).map(c=>c.ticker));
 return {schemaVersion:1,scope:"RAAS_2016_2025_HISTORICAL_INTAKE_REVIEW_QUEUE",
  status:"RESEARCH_EVIDENCE_NOT_APPROVED_ELIGIBILITY",
  summary:{sourcePrograms:queue.length,distinctSourceIssuers:exposed.distinctResearchIssuers,
   sameIssuerOverlappingPairs:exposed.overlappingSameIssuerPairs,
   datedShareResearchPrograms:queue.filter(c=>c.shareSourceAvailable).length,
   distinctIssuersWithShareResearch:withShares.size,
   liveRawCapResearchPrograms:rawByCase.size,
   distinctIssuersWithRawResearch:withRaw.size,
   provisionalPreAction300mTo10bSessions:queue.reduce((n,c)=>n+c.provisionalPreAction300mTo10bSessions,0),
   reviewedEligibleTradingEvents:0,approvedRaasScores:0,
   fullTenYearCensusAudited:false},
  cases:queue,
  interpretation:"Case-level source review queue only; provisional capitalization sessions are not valid trades, 10-year market-cap proof, holdouts, or RAAS metric calibration. Do not merge these records into approved intake without independent point-in-time review."};
}
function main(){
 const primary=readJson(PRIMARY),shares=readJson(SHARES);
 const rawPath=process.env.RAAS_RAW_CAP_OUTPUT;
 let rawCap=null;
 if(rawPath&&fs.existsSync(rawPath)){
  const payload=JSON.parse(fs.readFileSync(rawPath,"utf8"));
  if(payload.status==="BLOCKED_MISSING_ALPACA_CREDENTIALS")rawCap=null;
  else rawCap=payload;
 }
 const result=assemble({primary,shares,rawCap});
 const output=process.env.RAAS_INTAKE_REVIEW_QUEUE_OUTPUT||
  path.join(root,"raas-historical-intake-review-queue.json");
 fs.mkdirSync(path.dirname(output),{recursive:true});
 fs.writeFileSync(output,JSON.stringify(result,null,2)+"\n");
 const summary={...result.summary,status:result.status};
 process.stdout.write(JSON.stringify(summary)+"\n");
 if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
  "### Historical RAAS intake audit queue (not approved)\n\n"+
  JSON.stringify(summary,null,2)+"\n\nNo RAAS score or ten-year trade is approved.\n");
}
if(require.main===module)try{main()}catch(e){
 console.error("RAAS_INTAKE_REVIEW_QUEUE_FATAL_"+String(e.message).replace(/[^A-Z0-9_]/g,"_"));
 process.exitCode=1;
}
module.exports={assemble};
