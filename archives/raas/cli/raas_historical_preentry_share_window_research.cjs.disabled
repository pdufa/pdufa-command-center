#!/usr/bin/env node
"use strict";
/**
 * Analyze previously unmeasurable early PDUFA windows from dated SEC 2019
 * annual cover facts. This is supplementary RESEARCH, not evidence that share
 * counts were constant, nor a validated historical return or RAAS score.
 */
const fs=require("node:fs"),path=require("node:path");
const {checkedLead}=require("./raas_historical_raw_market_cap_research.cjs");
const {assemble}=require("./raas_historical_candidate_review_queue.cjs");
const {allWindows,NAMED_WINDOWS}=require("./raas_historical_provisional_window_grid.cjs");
const prior=require("./raas_alpaca_historical_price_study.cjs");
const root=path.resolve(__dirname,"..");
const readJson=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const PATHS={
 primary:"new-platform/frontend/data/raas-historical-2020-primary-source-leads.json",
 shares:"new-platform/frontend/data/raas-2020-sec-cover-share-leads.json",
 preentry:"new-platform/frontend/data/raas-preentry-2020-sec-cover-share-leads.json"
};
const rnd=n=>Math.round((n+Number.EPSILON)*100)/100;
const addDays=(s,n)=>new Date(Date.parse(s+"T00:00:00Z")+n*86400000).toISOString().slice(0,10);
function validatePreentry({primary,shares,preentry}){
 if(preentry?.scope!=="RAAS_MANUALLY_LOCATED_PRE_ENTRY_SEC_SHARES_RESEARCH"||
  !Array.isArray(preentry.records))throw Error("RAAS_PREENTRY_SCOPE_INVALID");
 const byEvent=new Map(primary.records.map(e=>[e.caseId,e]));
 const byLatest=new Map(shares.records.map(s=>[s.caseId,s]));
 const out=new Map();
 for(const earlier of preentry.records){
  const event=byEvent.get(earlier?.caseId),later=byLatest.get(earlier?.caseId);
  if(!event||!later||out.has(earlier.caseId))
   throw Error("RAAS_PREENTRY_DUPLICATE_OR_UNMATCHED_CASE");
  checkedLead(earlier,event);
  checkedLead(later,event);
  if(earlier.ticker!==later.ticker||earlier.cik!==later.cik||
   earlier.venue!==later.venue||
   earlier.shareClass!==later.shareClass||
   earlier.sourceUrl===later.sourceUrl||
   earlier.firstConservativeEntryDate>=later.firstConservativeEntryDate||
   earlier.filedDate>=later.filedDate||
   earlier.sharesMeasurementDate>=later.sharesMeasurementDate||
   earlier.firstConservativeEntryDate>=event.actualFDAActionDate)
   throw Error("RAAS_PREENTRY_WRONG_CHRONOLOGY_OR_SHARE_CLASS");
  out.set(earlier.caseId,earlier);
 }
 return out;
}
function validateBars(rawCase,event,later){
 if(!rawCase)return null;
 if(rawCase.caseId!==event.caseId||rawCase.ticker!==event.ticker||
  rawCase.pdufaTargetDate!==event.pdufaTargetDate||
  rawCase.actualFDAActionDate!==event.actualFDAActionDate||
  rawCase.status!=="RAW_MARKET_CAP_DIAGNOSTICS_NOT_PROVEN_TRADING_ELIGIBILITY"||
  rawCase.eventTradeCasesValidated!==0||rawCase.approvedRaasRatings!==0||
  rawCase.shareFactSourceUrl!==later.sourceUrl||
  rawCase.conservativeEligibleInformationDate!==later.firstConservativeEntryDate||
  rawCase.originalSharesMeasurementDate!==later.sharesMeasurementDate||
  !Array.isArray(rawCase.observations))
  throw Error("RAAS_PREENTRY_RAW_CASE_IDENTITY_INVALID");
 let priorSession="";
 for(const o of rawCase.observations){
  if(typeof o.session!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(o.session)||
   priorSession>=o.session||
   !Number.isFinite(o.rawClose)||o.rawClose<=0||
   !Number.isFinite(o.adjustedClose)||o.adjustedClose<=0||
   o.beforeActualFDAAction!==(o.session<event.actualFDAActionDate)||
   o.sourceUrl!==later.sourceUrl)
   throw Error("RAAS_PREENTRY_RAW_BAR_INVALID");
  const published=o.session>=
   [later.firstConservativeEntryDate,event.targetAnnouncementDate,event.phase3ReadoutDate].sort().at(-1);
  const expected=o.rawClose*later.sharesOutstanding/1000000;
  if(published?(
   !Number.isFinite(o.historicMarketCapResearchMillions)||
   Math.abs(o.historicMarketCapResearchMillions-expected)>0.011||
   o.within300mTo10bUnreviewed!==(expected>=300&&expected<=10000)
  ):(o.historicMarketCapResearchMillions!==null||
      o.within300mTo10bUnreviewed!==null))
   throw Error("RAAS_PREENTRY_LEGACY_CAP_CONTRADICTION");
  priorSession=o.session;
 }
 return rawCase.observations;
}
function evaluate(event,rows,earlier,later,e,x){
 const plannedEntry=prior.minusDays(event.pdufaTargetDate,e),
  plannedExit=prior.minusDays(event.pdufaTargetDate,x);
 const base={entryLeadDays:e,exitLeadDays:x,actualEntryDate:null,actualExitDate:null,
  historicalSharesSourceUsed:null,shareFactFirstSafeDate:null,
  supplementalShareFactUsed:false,provisionalEntryCapMillions:null,
  provisionalGrossReturnPct:null,provisionalNetReturnPct:null,
  validated:false,studyEligible:false};
 if(!rows)return {...base,reason:"MISSING_LIVE_ALPACA_RAW_PRICES"};
 const entry=rows.find(o=>o.session>=plannedEntry&&o.session<=addDays(plannedEntry,4));
 const exit=[...rows].reverse().find(o=>o.session<=plannedExit&&o.session>=addDays(plannedExit,-4));
 const dates={actualEntryDate:entry?.session??null,actualExitDate:exit?.session??null};
 if(!entry||!exit)return {...base,...dates,reason:"MISSING_ENTRY_OR_EXIT_SESSION"};
 if(entry.session>=exit.session)return {...base,...dates,reason:"ENTRY_NOT_BEFORE_EXIT"};
 if(entry.session<event.targetAnnouncementDate||entry.session<event.phase3ReadoutDate)
  return {...base,...dates,reason:"PDUFA_OR_PHASE3_NOT_PUBLIC_AT_ENTRY"};
 if(exit.session>=event.actualFDAActionDate)
  return {...base,...dates,reason:"EARLY_FDA_ACTION_CENSORS_EXIT"};
 const shares=[earlier,later].filter(Boolean)
  .filter(s=>s.firstConservativeEntryDate<=entry.session)
  .sort((a,b)=>b.firstConservativeEntryDate.localeCompare(a.firstConservativeEntryDate));
 const source=shares[0];
 if(!source)return {...base,...dates,reason:"NO_DATED_SHARE_SOURCE_KNOWN_AT_ENTRY"};
 const cap=entry.rawClose*source.sharesOutstanding/1000000;
 const details={historicalSharesSourceUsed:source.sourceUrl,
  shareFactFirstSafeDate:source.firstConservativeEntryDate,
  supplementalShareFactUsed:Boolean(earlier&&source.sourceUrl===earlier.sourceUrl)};
 if(cap<300||cap>10000)
  return {...base,...dates,...details,reason:"PROVISIONAL_ENTRY_CAP_OUTSIDE_300M_10B"};
 const gross=rnd((exit.adjustedClose/entry.adjustedClose-1)*100);
 return {...base,...dates,...details,provisionalEntryCapMillions:rnd(cap),
  provisionalGrossReturnPct:gross,provisionalNetReturnPct:rnd(gross-1),
  status:"UNVALIDATED_ADDITIONAL_PREENTRY_WINDOW_RESEARCH",
  reason:"NEEDS_SHARE_CONTINUITY_SPLIT_AND_INDEPENDENT_PRICE_AUDIT"};
}
function build({primary,shares,preentry,rawCap=null}){
 const queue=assemble({primary,shares,rawCap});
 const earlierByCase=validatePreentry({primary,shares,preentry});
 const events=new Map(primary.records.map(e=>[e.caseId,e]));
 const later=new Map(shares.records.map(s=>[s.caseId,s]));
 const research=new Map((rawCap?.cases??[]).map(c=>[c.caseId,c]));
 const grid=allWindows();
 const cases=queue.cases.map(c=>{
  const event=events.get(c.caseId),recent=later.get(c.caseId),
   earlier=earlierByCase.get(c.caseId),r=research.get(c.caseId);
  const bars=recent&&r?validateBars(r,event,recent):null;
  let newlyMeasurable=0,provisional=0;
  const blockers={};
  for(const w of grid){
   const result=evaluate(event,bars,earlier,recent,w.entryLeadDays,w.exitLeadDays);
   blockers[result.reason]=(blockers[result.reason]||0)+1;
   if(result.status==="UNVALIDATED_ADDITIONAL_PREENTRY_WINDOW_RESEARCH"){
    provisional++;
    if(result.supplementalShareFactUsed)newlyMeasurable++;
   }
  }
  const namedWindowDiagnostics=NAMED_WINDOWS.map(w=>
   evaluate(event,bars,earlier,recent,w.entryLeadDays,w.exitLeadDays));
  return {caseId:c.caseId,ticker:c.ticker,pdufaTargetDate:c.pdufaTargetDate,
   actualFDAActionDate:c.actualFDAActionDate,
   earlierShareSource:earlier?.sourceUrl??null,
   earlierShareFactPublishedAt:earlier?.filedDate??null,
   earlierSharesOutstanding:earlier?.sharesOutstanding??null,
   laterShareSource:recent?.sourceUrl??null,
   laterSharesOutstanding:recent?.sharesOutstanding??null,
   publishedCoverShareCountChange:earlier&&recent?
    recent.sharesOutstanding-earlier.sharesOutstanding:null,
   publishedShareCountChangePct:earlier&&recent?
    rnd((recent.sharesOutstanding/earlier.sharesOutstanding-1)*100):null,
   programGridWindowsChecked:grid.length,
   unvalidatedPriceAndCapWindows:provisional,
   newlyMeasurablePreentryWindows:newlyMeasurable,
   reasonCounts:blockers,namedWindowDiagnostics,eligibleTradingCases:0,
   approvedRaasScores:0};
 });
 return {schemaVersion:1,scope:"RAAS_EARLIER_SEC_PUBLISHED_SHARE_PREENTRY_DIAGNOSTICS",
  status:rawCap?"UNVALIDATED_SUPPLEMENTAL_SHARE_PRICE_RESEARCH_ONLY":"BLOCKED_NO_LIVE_ALPACA_RESEARCH",
  summary:{sourcePrograms:cases.length,
   earlyCoverShareSourcePrograms:earlierByCase.size,
   gridWindowsChecked:cases.reduce((n,c)=>n+c.programGridWindowsChecked,0),
   newlyMeasurablePreentryWindows:cases.reduce((n,c)=>n+c.newlyMeasurablePreentryWindows,0),
   independentlyValidatedEventTrades:0,approvedRaasScores:0,
   fullTenYearCensusAudited:false,optimalWindowDeclared:false},
  cases,caveat:"SEC cover facts are point-in-time publicly known numbers, not proved daily float/shares; raw price x cover shares is provisional capitalization. Neither individual cases nor dependent issuer windows constitute a 2016–2025 backtest or validated trading advice."};
}
function main(){
 const primary=readJson(PATHS.primary),shares=readJson(PATHS.shares),
  preentry=readJson(PATHS.preentry);
 const rawPath=process.env.RAAS_RAW_CAP_OUTPUT;
 const rawCap=rawPath&&fs.existsSync(rawPath)?JSON.parse(fs.readFileSync(rawPath,"utf8")):null;
 const result=build({primary,shares,preentry,
  rawCap:rawCap?.status==="BLOCKED_MISSING_ALPACA_CREDENTIALS"?null:rawCap});
 const output=process.env.RAAS_PREENTRY_OUTPUT||
  path.join(root,"raas-supplemental-preentry-share-windows.json");
 fs.mkdirSync(path.dirname(output),{recursive:true});
 fs.writeFileSync(output,JSON.stringify(result,null,2)+"\n");
 console.log(JSON.stringify({status:result.status,...result.summary,
  requested79to14:result.cases.map(c=>({ticker:c.ticker,caseId:c.caseId,
   reason:c.namedWindowDiagnostics.find(w=>w.entryLeadDays===79&&w.exitLeadDays===14)?.reason,
   supplementalSharesUsed:c.namedWindowDiagnostics.find(w=>w.entryLeadDays===79&&w.exitLeadDays===14)?.supplementalShareFactUsed}))}));
 if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
  "### Newly located pre-entry SEC cover shares (research only)\n\n"+
   JSON.stringify(result.summary,null,2)+"\n\nStill zero verified trades or RAAS calibrations.\n");
}
if(require.main===module)try{main()}catch(e){
 console.error("RAAS_PREENTRY_RESEARCH_FATAL_"+String(e.message).replace(/[^A-Z0-9_]/g,"_"));
 process.exitCode=1;
}
module.exports={validatePreentry,validateBars,evaluate,build};
