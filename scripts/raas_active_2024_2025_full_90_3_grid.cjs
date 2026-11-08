#!/usr/bin/env node
"use strict";

// Permanent retirement: no historical artifact writer may execute as a command.
if (require.main === module) { process.stderr.write("RAAS_PERMANENTLY_RETIRED: this archived command cannot run or modify historical records.\n"); process.exit(78); }

/** Full T-90 through T-3 2024/25 entry/exit search, research-only.
 * Every e>x, e<=90, x>=3 is evaluated. No T-79/T-14 benchmark or winner.
 * Uses historical Alpaca RAW closes only for provisional SEC-cover cap,
 * and adjusted 'all' SIP closes separately for provisional price returns.
 * A named PDUFA goal can be used only after its original/revised announcement.
 * FDA actions are used only to censor returns, not as entry features.
 * Never promote nine outcome-selected cases to validated predictions.
 */
const fs=require("node:fs"),path=require("node:path");
const {allWindows}=require("./raas_historical_provisional_window_grid.cjs");
const {validatePreentry}=require("./raas_historical_preentry_share_window_research.cjs");
const root=path.resolve(__dirname,"..");
const SCOPE="RAAS_ACTIVE_2024_2025_FULL_T90_T3_RESEARCH_GRID_ONLY";
const R_SCOPE="RAAS_ACTIVE_2024_2025_ORIGINAL_SOURCE_LEADS_AND_ALPACA_CAP_RESEARCH";
const valid=s=>typeof s==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 !Number.isNaN(Date.parse(s+"T00:00:00Z"))&&new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const day=(s,n)=>new Date(Date.parse(s+"T00:00:00Z")+n*86400000).toISOString().slice(0,10);
const delta=(a,b)=>(Date.parse(a+"T00:00:00Z")-Date.parse(b+"T00:00:00Z"))/86400000;
const round=n=>Math.round((n+Number.EPSILON)*100)/100;
const median=v=>{const a=v.slice().sort((x,y)=>x-y),n=a.length;return n%2?a[(n-1)/2]:(a[n/2-1]+a[n/2])/2};
const fail=s=>{throw Error("RAAS_T90_T3_"+s)};
function verifySources(primary,earlier,later){
 if(primary?.scope!=="RAAS_HISTORICAL_PRIMARY_PDUFA_EVENT_EVIDENCE_RESEARCH"||
  !Array.isArray(primary.records)||primary.records.length!==9||
  earlier?.records?.length!==9||later?.records?.length!==9)fail("PRIMARY_SOURCE_INVALID");
 const shareMap=validatePreentry({primary,shares:later,preentry:earlier});
 if(shareMap.size!==9)fail("SEC_SHARES_INCOMPLETE");
 if(new Set(primary.records.map(x=>x.caseId)).size!==9)fail("DUPLICATE_CASE");
 for(const x of primary.records){
  if(!x||!valid(x.pdufaTargetDate)||!valid(x.actualFDAActionDate)||
   !valid(x.phase3ReadoutDate)||!valid(x.targetAnnouncementDate)||
   !["APPROVED","CRL"].includes(x.actualFDAOutcome)||
   !shareMap.has(x.caseId))fail("FDA_SOURCE_INVALID");
  if(x.originallyAnnouncedPdufaTargetDate!==undefined &&
    (!valid(x.originallyAnnouncedPdufaTargetDate)||
     !valid(x.originalTargetAnnouncementDate)||
     x.originalTargetAnnouncementDate>=x.targetAnnouncementDate||
     x.pdufaTargetDate<=x.originallyAnnouncedPdufaTargetDate||
     x.formalGoalExtensionIndependentlyVerified!==true))fail("REVISION_CHAIN_INVALID");
 }
 return shareMap;
}
function goalVersions(e){
 const v=[{version:"FINAL_AS_PUBLISHED",goal:e.pdufaTargetDate,
  announced:e.targetAnnouncementDate,sourceUrl:e.targetAnnouncementSourceUrl,
  revisesAt:null}];
 if(e.originallyAnnouncedPdufaTargetDate){
  v.unshift({version:"ORIGINAL_AS_PUBLISHED",
   goal:e.originallyAnnouncedPdufaTargetDate,
   announced:e.originalTargetAnnouncementDate,
   sourceUrl:e.originalTargetAnnouncementSourceUrl||null,
   revisesAt:e.targetAnnouncementDate});
 }
 return v;
}
function checkedBars(raw,e,last){
 if(!raw||raw.caseId!==e.caseId||raw.ticker!==e.ticker||
  raw.pdufaTargetDate!==e.pdufaTargetDate||
  raw.actualFDAActionDate!==e.actualFDAActionDate||
  raw.source!=="ALPACA_SIP_RAW_CLOSE_X_SEC_COVER_SHARES"||
  raw.priceReturnSource!=="ALPACA_SIP_ADJUSTMENT_ALL_SEPARATE"||
  raw.eventTradeCasesValidated!==0||raw.approvedRaasRatings!==0||
  !Array.isArray(raw.observations))fail("PRICE_CASE_IDENTITY_INVALID");
 let prev="";
 for(const o of raw.observations){
  if(!valid(o.session)||o.session<=prev||
   !Number.isFinite(o.rawClose)||o.rawClose<=0||
   !Number.isFinite(o.adjustedClose)||o.adjustedClose<=0||
   o.sourceUrl!==last.sourceUrl||
   o.beforeActualFDAAction!==(o.session<e.actualFDAActionDate))fail("BAR_PROVENANCE_INVALID");
  prev=o.session;
 }
 return raw.observations;
}
function assess(e,g,w,bars,shareRows){
 const pe=day(g.goal,-w.entryLeadDays),px=day(g.goal,-w.exitLeadDays);
 const base={caseId:e.caseId,ticker:e.ticker,targetYear:+g.goal.slice(0,4),
  cohortYear:+e.pdufaTargetDate.slice(0,4),
  targetVersion:g.version,entryLeadDays:w.entryLeadDays,exitLeadDays:w.exitLeadDays,
  plannedEntry:pe,plannedExit:px,entrySession:null,exitSession:null,
  provisionalCapUsdMillions:null,provisionalGrossReturnPct:null,
  provisionalNetReturnPct:null,shareSourceAtEntry:null,
  verifiedTrade:false,approvedRAASScore:null};
 if(!g.sourceUrl)return {...base,reason:"INDEPENDENT_ORIGINAL_GOAL_SOURCE_URL_NOT_RECORDED"};
 if(g.announced>pe)return {...base,reason:"GOAL_DATE_NOT_PUBLIC_BY_PLANNED_ENTRY"};
 if(e.phase3ReadoutDate>pe)return {...base,reason:"PHASE3_READOUT_NOT_PUBLIC_BY_PLANNED_ENTRY"};
 if(g.revisesAt&&g.revisesAt<=px)return {...base,reason:"ORIGINAL_GOAL_REVISED_BEFORE_PLANNED_EXIT"};
 if(!bars||bars.length===0)return {...base,reason:"MISSING_ALPACA_RAW_AND_ADJUSTED_BARS"};
 const entry=bars.find(b=>b.session>=pe&&b.session<=day(pe,4));
 const exit=[...bars].reverse().find(b=>b.session<=px&&b.session>=day(px,-4));
 const dates={entrySession:entry?.session??null,exitSession:exit?.session??null};
 if(!entry||!exit)return {...base,...dates,reason:"MISSING_ENTRY_OR_EXIT_SESSION"};
 if(entry.session>=exit.session)return {...base,...dates,reason:"NO_ORDERED_TRADING_SESSIONS"};
 if(entry.session<g.announced||entry.session<e.phase3ReadoutDate)
  return {...base,...dates,reason:"EVIDENCE_NOT_PUBLIC_AT_EXECUTION_SESSION"};
 if(g.revisesAt&&g.revisesAt<=exit.session)
  return {...base,...dates,reason:"ORIGINAL_GOAL_REVISED_BEFORE_EXIT"};
 if(exit.session>=e.actualFDAActionDate)
  return {...base,...dates,reason:"FDA_ACTION_BEFORE_PLANNED_EXIT_CENSORS_WINDOW"};
 const usable=shareRows.filter(s=>s.firstConservativeEntryDate<=entry.session)
  .sort((x,y)=>y.firstConservativeEntryDate.localeCompare(x.firstConservativeEntryDate));
 const share=usable[0];
 if(!share)return {...base,...dates,reason:"NO_PUBLIC_SEC_COVER_SHARES_AT_ENTRY"};
 const cap=entry.rawClose*share.sharesOutstanding/1000000;
 const fact={shareSourceAtEntry:share.sourceUrl};
 if(!Number.isFinite(cap)||cap<300||cap>10000)
  return {...base,...dates,...fact,reason:"PROVISIONAL_CAP_OUTSIDE_300M_TO_10B"};
 const gross=round((exit.adjustedClose/entry.adjustedClose-1)*100);
 return {...base,...dates,...fact,reason:"PROVISIONAL_UNVERIFIED_ELIGIBILITY",
  provisionalCapUsdMillions:round(cap),provisionalGrossReturnPct:gross,
  provisionalNetReturnPct:round(gross-1)};
}
function build({primary,earlier,later,research=null}){
 verifySources(primary,earlier,later);
 const pairs=allWindows();
 if(pairs.length!==3828||pairs[0].entryLeadDays!==90||
  pairs[0].exitLeadDays!==3||
  pairs.at(-1).entryLeadDays!==4||pairs.at(-1).exitLeadDays!==3||
  new Set(pairs.map(p=>p.entryLeadDays+"|"+p.exitLeadDays)).size!==3828)
  fail("FULL_WINDOW_ENUMERATION_CHANGED");
 const goals=primary.records.flatMap(e=>goalVersions(e).map(g=>({e,g})));
 const base={schemaVersion:1,scope:SCOPE,years:[2024,2025],
  configuredEntryCalendarDays:[90,4],configuredExitCalendarDays:[3,89],
  earliestAllowedEntryLeadDays:90,lastAllowedExitLeadDays:3,
  restrictions:"entry lead > exit lead; 300m-10b provisional as-of cap; published goal/readout",
  uniqueEntryExitPairsPerGoalVersion:pairs.length,
  goalVersionCaseSets:goals.length,
  totalGoalCaseWindowEvaluations:pairs.length*goals.length,
  allSourceCases:primary.records.length,comparisonWindowSelected:null,
  validatedMarketCapCases:0,validatedTradingCases:0,approvedRAASMetrics:0,
  approvedBestEntryExitWindow:null,completeTwoYearFDACensus:false,
  cohortSplitRule:"FINAL_PUBLIC_PDUFA_GOAL_YEAR_REGARDLESS_OF_ORIGINAL_GOAL_VERSION",
  independentlyPriceVerified:false,
  warnings:[
   "T-79/T-14 is an ordinary window among 3828, not a preferred benchmark.",
   "Nine retrospectively selected 2024/2025 events are not a complete two-year FDA PDUFA census.",
   "2024 comparisons are exploratory training only; 2025 is separated as descriptive holdout, not validated out-of-sample.",
   "2024/2025 cohorts follow the final target year, not a superseded original goal year; a 2025 case must never leak into 2024 training.",
   "Only historical source-available PDUFA goals, Phase 3 disclosure and SEC share counts can enter provisional eligibility; later dates are blocked.",
   "Retrospective FDA actions censor untraded exits, never enter a forecast feature.",
   "Raw Alpaca SIP prices for provisional market cap are not the adjusted=all SIP returns; independent vendor/corporate actions/unadjusted daily share-continuity audits remain missing.",
   "No optimized window or numeric RAAS rating may be published from this sample."
  ]};
 if(!research||research.status==="BLOCKED_MISSING_ALPACA_CREDENTIALS")
  return {...base,status:"BLOCKED_NO_ALPACA_BARS",caseWindows:[],
   windowSummaries:[],researchWindowCount:0,reasonTotals:{MISSING_ALPACA_RAW_AND_ADJUSTED_BARS:base.totalGoalCaseWindowEvaluations}};
 if(research.scope!==R_SCOPE||
  research.status!=="2024_2025_SOURCE_LEADS_UNVALIDATED_PRICE_RESEARCH"||
  research.validatedTradingCases!==0||research.approvedRaasMetrics!==0||
  research.fullYearCensusesAudited!==0||research.selectedOptimalWindow!==null||
  research.allResearchOnly!==true||!Array.isArray(research.priceDataRawAndAdjusted)||
  research.priceDataRawAndAdjusted.length!==primary.records.length)
  fail("RESEARCH_ARTIFACT_INVALID");
 const priceMap=new Map(research.priceDataRawAndAdjusted.map(x=>[x.caseId,x]));
 if(priceMap.size!==primary.records.length)fail("DUPLICATE_PRICE_CASE");
 const earlyMap=new Map(earlier.records.map(x=>[x.caseId,x]));
 const lateMap=new Map(later.records.map(x=>[x.caseId,x]));
 const bars=new Map(primary.records.map(e=>[e.caseId,
  checkedBars(priceMap.get(e.caseId),e,lateMap.get(e.caseId))]));
 const caseWindows=[],grouped=new Map(),reasons={};
 for(const {e,g} of goals)for(const w of pairs){
  const s=assess(e,g,w,bars.get(e.caseId),[earlyMap.get(e.caseId),lateMap.get(e.caseId)]);
  caseWindows.push(s);
  reasons[s.reason]=(reasons[s.reason]||0)+1;
  const key=g.version+"|"+w.entryLeadDays+"|"+w.exitLeadDays;
  if(!grouped.has(key))grouped.set(key,{targetVersion:g.version,
   entryLeadDays:w.entryLeadDays,exitLeadDays:w.exitLeadDays,
   casesConsidered:0,casesWithProvisionalReturns:0,training2024:[],
   holdout2025:[],distinctIssuers:new Set()});
  const a=grouped.get(key);a.casesConsidered++;
  if(s.provisionalGrossReturnPct!==null){
   a.casesWithProvisionalReturns++;a.distinctIssuers.add(e.ticker);
   a[s.cohortYear===2024?"training2024":"holdout2025"].push(s.provisionalGrossReturnPct);
  }
 }
 function summary(v){
  if(!v.length)return {n:0,meanGrossPct:null,medianGrossPct:null,
   winRatePct:null,worstGrossPct:null};
  return {n:v.length,
   meanGrossPct:round(v.reduce((a,b)=>a+b,0)/v.length),
   medianGrossPct:round(median(v)),
   winRatePct:round(100*v.filter(n=>n>0).length/v.length),
   worstGrossPct:Math.min(...v)};
 }
 const windowSummaries=[...grouped.values()].map(a=>({
  targetVersion:a.targetVersion,entryLeadDays:a.entryLeadDays,
  exitLeadDays:a.exitLeadDays,casesConsidered:a.casesConsidered,
  provisionalReturnCases:a.casesWithProvisionalReturns,
  distinctResearchIssuers:a.distinctIssuers.size,
  training2024:summary(a.training2024),holdout2025:summary(a.holdout2025),
  eligibilityVerified:false,independentPriceVerified:false,approvedWinner:false
 }));
 return {...base,status:"PROVISIONAL_SELECTED_CASE_PRICE_GRID_NOT_VALIDATED",
  caseWindows,windowSummaries,
  researchWindowCount:caseWindows.filter(x=>x.provisionalGrossReturnPct!==null).length,
  reasonTotals:reasons};
}
const stringifyCSV=(report)=>{
 if(report?.scope!==SCOPE||report.approvedBestEntryExitWindow!==null||
  report.approvedRAASMetrics!==0||report.validatedTradingCases!==0)
  fail("CSV_REPORT_INVALID");
 const cols=["ticker","cohortYear","targetYear","targetVersion","entryLeadDays","exitLeadDays",
  "plannedEntry","plannedExit","entrySession","exitSession",
  "shareSourceAtEntry","provisionalCapUsdMillions","provisionalGrossReturnPct",
  "provisionalNetReturnPct","reason","verifiedTrade","approvedRAASScore"];
 const val=(x)=>x===null||x===undefined?"":typeof x==="number"?String(x):
  '"'+(/^[\s\u0000-\u001f]*[=+\-@]/u.test(String(x))?"'":"")+
  String(x).replaceAll('"','""')+'"';
 return cols.join(",")+"\n"+report.caseWindows.map(row=>cols.map(k=>val(row[k])).join(",")).join("\n")+"\n";
};
function main(){
 try{
  const load=(env,f)=>JSON.parse(fs.readFileSync(process.env[env]||path.join(root,f),"utf8"));
  const result=build({
   primary:load("RAAS_T90_T3_PRIMARY","new-platform/frontend/data/raas-active-2024-2025-primary-source-leads.json"),
   earlier:load("RAAS_T90_T3_EARLIER","new-platform/frontend/data/raas-active-2024-2025-preentry-sec-share-leads.json"),
   later:load("RAAS_T90_T3_LATER","new-platform/frontend/data/raas-active-2024-2025-sec-cover-share-leads.json"),
   research:process.env.RAAS_ACTIVE_SOURCE_RESEARCH_OUTPUT?load("RAAS_ACTIVE_SOURCE_RESEARCH_OUTPUT",""):null
  });
  const json=process.env.RAAS_T90_T3_GRID_JSON||path.join(root,"raas-2024-2025-full-t90-t3-grid.json");
  const csv=process.env.RAAS_T90_T3_GRID_CSV||path.join(root,"raas-2024-2025-full-t90-t3-grid.csv");
  for(const p of [json,csv])fs.mkdirSync(path.dirname(p),{recursive:true});
  fs.writeFileSync(json,JSON.stringify(result)+"\n");
  fs.writeFileSync(csv,stringifyCSV(result));
  const summary={status:result.status,sourceCases:result.allSourceCases,
   goalVersionCaseSets:result.goalVersionCaseSets,
   pairsPerGoalVersion:result.uniqueEntryExitPairsPerGoalVersion,
   caseWindowChecks:result.totalGoalCaseWindowEvaluations,
   provisionalObservedWindowReturns:result.researchWindowCount,
   verifiedTrades:0,approvedBestWindow:null};
  console.log(JSON.stringify(summary));
  if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
   "### RAAS FULL T-90 to T-3 window comparison, research only\n\n"+
   JSON.stringify(summary,null,2)+"\n\nNo validated optimal entry/exit or RAAS grades.\n");
  if(result.status==="BLOCKED_NO_ALPACA_BARS")process.exitCode=1;
 }catch(e){console.error("RAAS_T90_T3_FATAL_"+String(e.message||e)
  .replace(/[^A-Z0-9_]/g,"_").slice(0,160));process.exitCode=1;}
}
if(require.main===module)main();
module.exports={goalVersions,assess,build,stringifyCSV};
