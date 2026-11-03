#!/usr/bin/env node
"use strict";
/**
 * Research-only 2016–2025 PDUFA entry/exit diagnostics for currently sourced
 * 2020 cases. NEVER constructs SOURCE_REVIEWED entries or ranks an optimum.
 * Return estimates remain unaudited for splits, issuer rights, price provider,
 * survivorship, share count continuity, liquidity and trade execution.
 */
const fs=require("node:fs"),path=require("node:path");
const {assemble}=require("./raas_historical_candidate_review_queue.cjs");
const prior=require("./raas_alpaca_historical_price_study.cjs");
const root=path.resolve(__dirname,"..");
const PRIMARY="new-platform/frontend/data/raas-historical-2020-primary-source-leads.json";
const SHARES="new-platform/frontend/data/raas-2020-sec-cover-share-leads.json";
const readJson=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const rnd=n=>Math.round((n+Number.EPSILON)*100)/100;
const day=s=>typeof s==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const addDays=(s,n)=>new Date(Date.parse(s+"T00:00:00Z")+n*86400000).toISOString().slice(0,10);
const NAMED_WINDOWS=Object.freeze([
 {entryLeadDays:90,exitLeadDays:30},
 {entryLeadDays:79,exitLeadDays:14},
 {entryLeadDays:60,exitLeadDays:14},
 {entryLeadDays:45,exitLeadDays:14},
 {entryLeadDays:30,exitLeadDays:7},
 {entryLeadDays:21,exitLeadDays:3},
 {entryLeadDays:14,exitLeadDays:3}
]);
function allWindows(){
 const out=[];
 for(let entry=90;entry>=4;entry--)for(let exit=3;exit<entry;exit++)
  out.push({entryLeadDays:entry,exitLeadDays:exit});
 return out;
}
function guardedObservations(share,event,research){
 if(!research)return null;
 if(!Array.isArray(research.observations)||research.observations.length<30||
  research.source!=="ALPACA_SIP_RAW_CLOSE_X_SEC_COVER_SHARES"||
  research.priceReturnSource!=="ALPACA_SIP_ADJUSTMENT_ALL_SEPARATE"||
  research.shareFactSourceUrl!==share.sourceUrl||
  research.shareFactFiledDate!==share.filedDate||
  research.conservativeEligibleInformationDate!==share.firstConservativeEntryDate||
  research.originalSharesMeasurementDate!==share.sharesMeasurementDate)
  throw Error("RAAS_WINDOW_SOURCE_META_INVALID");
 const evidenceDay=[share.firstConservativeEntryDate,
  event.targetAnnouncementDate,event.phase3ReadoutDate].sort().at(-1);
 let prev=null;const observations=[];
 for(const o of research.observations){
  if(!o||!day(o.session)||(prev!==null && o.session<=prev)||
   !Number.isFinite(o.rawClose)||o.rawClose<=0||
   !Number.isFinite(o.adjustedClose)||o.adjustedClose<=0||
   o.sourceUrl!==share.sourceUrl ||
   o.beforeActualFDAAction!==(o.session<event.actualFDAActionDate))
   throw Error("RAAS_WINDOW_UNTRUSTED_PRICE_ROW");
  const expectedCap=o.rawClose*share.sharesOutstanding/1000000;
  const inRange=expectedCap>=300&&expectedCap<=10000;
  const published=o.session>=evidenceDay;
  if(published?(
    o.sharesOutstandingKnownFromFiling!==share.sharesOutstanding ||
    !Number.isFinite(o.historicMarketCapResearchMillions)||
    Math.abs(o.historicMarketCapResearchMillions-expectedCap)>0.011||
    o.within300mTo10bUnreviewed!==inRange||
    o.sourceStatus!=="RESEARCH_ONLY_NEEDS_SHARE_CLASS_AND_CORPORATE_ACTION_AUDIT"
  ):(
    o.sharesOutstandingKnownFromFiling!==null||
    o.historicMarketCapResearchMillions!==null||
    o.within300mTo10bUnreviewed!==null||
    o.sourceStatus!=="PRE_DISCLOSURE_OR_MISSING_FACT"
  ))throw Error("RAAS_WINDOW_CAP_OR_ASOF_CONTRADICTION");
  prev=o.session;observations.push(o);
 }
 return observations;
}
function evaluate(event,observations,entryLeadDays,exitLeadDays){
 if(!Number.isInteger(entryLeadDays)||!Number.isInteger(exitLeadDays)||
  entryLeadDays>90||entryLeadDays<=exitLeadDays||exitLeadDays<3)
  throw Error("RAAS_WINDOW_LEADS_INVALID");
 const plannedEntry=prior.minusDays(event.pdufaTargetDate,entryLeadDays);
 const plannedExit=prior.minusDays(event.pdufaTargetDate,exitLeadDays);
 const base={entryLeadDays,exitLeadDays,plannedEntryDate:plannedEntry,
  plannedExitDate:plannedExit,actualEntryDate:null,actualExitDate:null,
  studyEligible:false,validated:false,provisionalNetReturnPct:null,
  provisionalGrossReturnPct:null,provisionalEntryCapMillions:null};
 if(!observations)return {...base,reason:"MISSING_LIVE_ALPACA_RAW_CAP_RESEARCH"};
 const entry=observations.find(o=>o.session>=plannedEntry&&o.session<=addDays(plannedEntry,4));
 const exit=[...observations].reverse().find(o=>o.session<=plannedExit&&o.session>=addDays(plannedExit,-4));
 const dates={actualEntryDate:entry?.session??null,actualExitDate:exit?.session??null};
 if(!entry||!exit)return {...base,...dates,reason:"MISSING_ENTRY_OR_EXIT_SESSION"};
 if(entry.session>=exit.session)return {...base,...dates,reason:"ENTRY_NOT_BEFORE_EXIT"};
 if(entry.session<event.targetAnnouncementDate||entry.session<event.phase3ReadoutDate)
  return {...base,...dates,reason:"PDUFA_OR_PHASE3_NOT_PUBLIC_AT_ENTRY"};
 if(exit.session>=event.actualFDAActionDate)
  return {...base,...dates,reason:"EARLY_FDA_ACTION_CENSORS_EXIT"};
 if(entry.historicMarketCapResearchMillions===null)
  return {...base,...dates,reason:"SEC_SHARE_SOURCE_NOT_PUBLIC_AT_ENTRY"};
 if(entry.within300mTo10bUnreviewed!==true)
  return {...base,...dates,reason:"PROVISIONAL_ENTRY_CAP_OUTSIDE_300M_TO_10B"};
 if(!Number.isFinite(entry.adjustedClose)||!Number.isFinite(exit.adjustedClose)||
  entry.adjustedClose<=0||exit.adjustedClose<=0)
  throw Error("RAAS_WINDOW_ADJUSTED_PRICE_INVALID");
 const gross=rnd((exit.adjustedClose/entry.adjustedClose-1)*100);
 return {...base,...dates,
  status:"UNVALIDATED_RESEARCH_WINDOW_ONLY",
  reason:"NEEDS_SPLIT_SHARE_CONTINUITY_AND_INDEPENDENT_PRICE_AUDIT",
  provisionalEntryCapMillions:entry.historicMarketCapResearchMillions,
  provisionalGrossReturnPct:gross,provisionalNetReturnPct:rnd(gross-1)};
}
function build({primary,shares,rawCap=null}){
 const queue=assemble({primary,shares,rawCap});
 const eByCase=new Map(primary.records.map(e=>[e.caseId,e]));
 const sByCase=new Map(shares.records.map(s=>[s.caseId,s]));
 const rByCase=new Map((rawCap?.cases??[]).map(c=>[c.caseId,c]));
 const grid=allWindows();
 const cases=queue.cases.map(c=>{
  const event=eByCase.get(c.caseId),share=sByCase.get(c.caseId),research=rByCase.get(c.caseId);
  const observations=share&&research?guardedObservations(share,event,research):null;
  const counts={};
  let unvalidated=0;
  for(const g of grid){
   const a=evaluate(event,observations,g.entryLeadDays,g.exitLeadDays);
   counts[a.reason]=(counts[a.reason]||0)+1;
   if(a.status==="UNVALIDATED_RESEARCH_WINDOW_ONLY")unvalidated++;
  }
  return {caseId:c.caseId,ticker:c.ticker,pdufaTargetDate:c.pdufaTargetDate,
   actualFDAActionDate:c.actualFDAActionDate,
   gridWindowsChecked:grid.length,provisionalWindowsWithCompletePriceAndTiming:unvalidated,
   blockedWindows:grid.length-unvalidated,
   reasonCounts:counts,
   namedWindowDiagnostics:NAMED_WINDOWS.map(w=>evaluate(event,observations,
    w.entryLeadDays,w.exitLeadDays)),
   approvedStudyRows:0,approvedRaasScores:0,
   status:"RESEARCH_ONLY_NO_HISTORIC_ELIGIBILITY_OR_OPTIMUM"};
 });
 const byIssuer=new Map();
 for(const c of cases){
  if(!byIssuer.has(c.ticker))byIssuer.set(c.ticker,[]);
  byIssuer.get(c.ticker).push(c.caseId);
 }
 return {schemaVersion:1,scope:"RAAS_2016_2025_PROVISIONAL_PRICE_WINDOW_DIAGNOSTICS",
  status:rawCap?"UNVALIDATED_HISTORIC_WINDOWS_RESEARCH_ONLY":"BLOCKED_NO_LIVE_RAW_RESEARCH",
  configuration:{studyYears:"2016-2025",entryLeadDays:"90..4",
   exitLeadDays:"3..entry-1",tradingSessionSearch:"entry day through +4 calendar days; exit day through -4 calendar days",
   transactionCostAssumptionPercentagePoints:1,capitalizationRangeUSDmillions:[300,10000],
   firstLocatedDisclosureIsNotProofOfFirstEver:true,
   marketCapSource:"SEC_UNRECONCILED_COVER_SHARES_X_ALPACA_SIP_RAW_CLOSE",
   returnSource:"ALPACA_SIP_ADJUSTMENT_ALL_UNRECONCILED"},
  summary:{sourcePrograms:cases.length,distinctResearchIssuers:byIssuer.size,
   programWindowEvaluations:cases.reduce((a,c)=>a+c.gridWindowsChecked,0),
   provisionalWindowsWithCompletePriceAndTiming:cases.reduce((a,c)=>a+c.provisionalWindowsWithCompletePriceAndTiming,0),
   independentlyVerifiedEligibleTradingCases:0,approvedRaasScores:0,
   fullTenYearCensusAudited:false,optimalWindowDeclared:false},
  cases,issuerExposureGroups:[...byIssuer].filter(([,ids])=>ids.length>1)
   .map(([ticker,caseIds])=>({ticker,caseIds,
    note:"OVERLAPPING_PROGRAMS_ARE_NOT_INDEPENDENT_TRADES"})),
  caveat:"No historical entry-day market-cap share-continuity audit, no independent price validation, no full 2016–2025 event census, no validated backtest, no optimal 79-to-14 or other entry/exit recommendation."};
}
function main(){
 const primary=readJson(PRIMARY),shares=readJson(SHARES);
 const rawPath=process.env.RAAS_RAW_CAP_OUTPUT;
 const rawCap=rawPath&&fs.existsSync(rawPath)?JSON.parse(fs.readFileSync(rawPath,"utf8")):null;
 const result=build({primary,shares,rawCap:rawCap?.status==="BLOCKED_MISSING_ALPACA_CREDENTIALS"?null:rawCap});
 const dest=process.env.RAAS_WINDOW_RESEARCH_OUTPUT||
  path.join(root,"raas-provisional-window-diagnostics.json");
 fs.mkdirSync(path.dirname(dest),{recursive:true});
 fs.writeFileSync(dest,JSON.stringify(result,null,2)+"\n");
 console.log(JSON.stringify({status:result.status,...result.summary,
  requested79to14:result.cases.map(c=>({ticker:c.ticker,caseId:c.caseId,
   reason:c.namedWindowDiagnostics.find(w=>w.entryLeadDays===79&&w.exitLeadDays===14)?.reason}))}));
 if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
  "### PDUFA T-90 to T-3 windows: unvalidated research, no winner\n\n"+
  JSON.stringify(result.summary,null,2)+"\n\nNo validated entry/exit return or RAAS score.\n");
}
if(require.main===module)try{main()}catch(e){
 console.error("RAAS_WINDOW_RESEARCH_FATAL_"+String(e.message).replace(/[^A-Z0-9_]/g,"_"));
 process.exitCode=1;
}
module.exports={NAMED_WINDOWS,allWindows,guardedObservations,evaluate,build};
