#!/usr/bin/env node
"use strict";

// Permanent retirement: no historical artifact writer may execute as a command.
if (require.main === module) { process.stderr.write("RAAS_PERMANENTLY_RETIRED: this archived command cannot run or modify historical records.\n"); process.exit(78); }

/**
 * Research-only walk-forward and multiple-comparisons diagnostic for the
 * FULL T-90..T-3 study. 2024 defines selection; 2025 can only be evaluated
 * after selection. The pooled 9-stock leader is hindsight, NOT validation.
 * No approval, return forecast, trading score or optimized strategy.
 */
const fs=require("node:fs"),path=require("node:path");
const SCOPE="RAAS_ACTIVE_2024_2025_FULL_T90_T3_RESEARCH_GRID_ONLY";
const OUT="RAAS_2024_2025_WALKFORWARD_SELECTION_BIAS_AUDIT";
const PAIRS=3828,EVENTS=9,EVALS=42108;
const fmt=n=>Math.round((n+Number.EPSILON)*100)/100;
const fail=s=>{throw Error("RAAS_WALKFORWARD_"+s)};
function stats(a){
 const v=a.map(x=>x.provisionalGrossReturnPct).filter(Number.isFinite);
 if(v.length!==a.length)fail("UNVERIFIED_ROW_AS_RETURN");
 if(!v.length)return {cases:0,meanGrossPct:null,meanNetAfterAssumed1ptPct:null,
  medianGrossPct:null,winRatePct:null,wins:0,worstGrossPct:null,caseReturns:[]};
 const sorted=[...v].sort((a,b)=>a-b);
 const n=sorted.length,med=n%2?sorted[(n-1)/2]:(sorted[n/2-1]+sorted[n/2])/2;
 const mean=v.reduce((a,b)=>a+b,0)/n,wins=v.filter(x=>x>0).length;
 return {cases:n,meanGrossPct:fmt(mean),meanNetAfterAssumed1ptPct:fmt(mean-1),
  medianGrossPct:fmt(med),winRatePct:fmt(wins/n*100),wins,
  worstGrossPct:fmt(sorted[0]),
  caseReturns:a.map(x=>({ticker:x.ticker,caseId:x.caseId,
   provisionalGrossReturnPct:x.provisionalGrossReturnPct,
   entrySession:x.entrySession,exitSession:x.exitSession}))};
}
const key=(e,x)=>e+"|"+x;
function rankRows(rows){
 if(!Array.isArray(rows)||rows.length<1)fail("NO_FINAL_CASE_ROWS");
 const grouped=new Map(),seen=new Set();
 for(const x of rows){
  if(!x||!Number.isInteger(x.entryLeadDays)||!Number.isInteger(x.exitLeadDays)||
   x.entryLeadDays<4||x.entryLeadDays>90||x.exitLeadDays<3||
   x.exitLeadDays>=x.entryLeadDays||
   typeof x.caseId!=="string"||!x.caseId||
   typeof x.ticker!=="string"||
   ![2024,2025].includes(x.cohortYear)||
   x.verifiedTrade!==false||x.approvedRAASScore!==null)
   fail("CASE_ROW_SCOPE_OR_APPROVAL_INVALID");
  const id=x.caseId+"|"+key(x.entryLeadDays,x.exitLeadDays);
  if(seen.has(id))fail("DUPLICATE_CASE_AND_WINDOW");
  seen.add(id);
  const valid=x.reason==="PROVISIONAL_UNVERIFIED_ELIGIBILITY";
  if(valid?(
    !Number.isFinite(x.provisionalGrossReturnPct)||
    !Number.isFinite(x.provisionalNetReturnPct)||
    !Number.isFinite(x.provisionalCapUsdMillions)||
    x.provisionalCapUsdMillions<299.99||x.provisionalCapUsdMillions>10000.01||
    Math.abs(x.provisionalNetReturnPct-(x.provisionalGrossReturnPct-1))>0.03||
    typeof x.entrySession!=="string"||typeof x.exitSession!=="string"||
    x.entrySession>=x.exitSession||typeof x.shareSourceAtEntry!=="string"
   ):(x.provisionalGrossReturnPct!==null||x.provisionalNetReturnPct!==null))
   fail("CASE_RETURN_OR_CAP_INVALID");
  const k=key(x.entryLeadDays,x.exitLeadDays);
  if(!grouped.has(k))grouped.set(k,{entryLeadDays:x.entryLeadDays,
   exitLeadDays:x.exitLeadDays,train:[],holdout:[],trainAll:0,holdoutAll:0});
  const group=grouped.get(k);
  if(x.cohortYear===2024){
   group.trainAll++;
   if(valid)group.train.push(x);
  }else{
   group.holdoutAll++;
   if(valid)group.holdout.push(x);
  }
 }
 const candidates=[...grouped.values()].filter(x=>x.trainAll===5&&x.holdoutAll===4);
 for(const a of candidates){
  if(a.trainAll!==5||a.holdoutAll!==4)fail("CASE_COHORT_COUNT_INCOMPLETE");
 }
 const eligibleTrain=candidates.filter(x=>x.train.length===5);
 const eligibleAllNine=eligibleTrain.filter(x=>x.holdout.length===4);
 // Invariant: 2025 data is NEVER a selection key for the train-only winner.
 const trainingRanking=eligibleTrain.slice().sort((a,b)=>{
  const ma=stats(a.train).meanGrossPct,mb=stats(b.train).meanGrossPct;
  return mb-ma||b.entryLeadDays-a.entryLeadDays||a.exitLeadDays-b.exitLeadDays;
 });
 const pooledRanking=eligibleAllNine.slice().sort((a,b)=>{
  const ma=stats([...a.train,...a.holdout]).meanGrossPct,
   mb=stats([...b.train,...b.holdout]).meanGrossPct;
  return mb-ma||b.entryLeadDays-a.entryLeadDays||a.exitLeadDays-b.exitLeadDays;
 });
 const pair=(g,label,selectionMethod)=>{
  if(!g)return null;
  return {label,selectionMethod,entryLeadDays:g.entryLeadDays,
   exitLeadDays:g.exitLeadDays,train2024:stats(g.train),
   holdout2025:stats(g.holdout),all2024To2025:stats([...g.train,...g.holdout]),
   approved:false};
 };
 const wanted=(e,x)=>candidates.find(c=>c.entryLeadDays===e&&c.exitLeadDays===x);
 return {
  candidateTrainOnly:pair(trainingRanking[0],
    "Top 2024-only mean (2025 descriptive evaluation)",
    "SELECTED_FROM_2024_TRAIN_ONLY"),
  candidatePooledLookahead:pair(pooledRanking[0],
    "Top pooled mean (LOOKAHEAD: disallowed as evidence of predictive performance)",
    "SELECTED_FROM_2024_AND_2025_NOT_INDEPENDENT"),
  preObservedWindows:[
   [76,63],[76,52],[75,63],[79,14]
  ].map(([e,x])=>pair(wanted(e,x),
   "Post-hoc observed candidate T-"+e+" to T-"+x,
   "AFTER_LOOKING_AT_2024_AND_2025_NOT_AN_INDEPENDENT_HOLDOUT")),
  trainFullCoveragePairs:eligibleTrain.length,
  allNineFullCoveragePairs:eligibleAllNine.length,
  trainingRank76to63:trainingRanking.findIndex(x=>x.entryLeadDays===76&&x.exitLeadDays===63)+1,
  fullGridPairsPresent:grouped.size
 };
}
function build(report){
 if(!report||report.scope!==SCOPE||
  report.status!=="PROVISIONAL_SELECTED_CASE_PRICE_GRID_NOT_VALIDATED"||
  report.uniqueEntryExitPairsPerGoalVersion!==PAIRS||
  report.totalGoalCaseWindowEvaluations!==EVALS||
  report.goalVersionCaseSets!==11||report.allSourceCases!==EVENTS||
  report.validatedMarketCapCases!==0||report.validatedTradingCases!==0||
  report.approvedRAASMetrics!==0||report.approvedBestEntryExitWindow!==null||
  report.comparisonWindowSelected!==null||
  report.independentlyPriceVerified!==false||
  report.completeTwoYearFDACensus!==false||
  report.cohortSplitRule!=="FINAL_PUBLIC_PDUFA_GOAL_YEAR_REGARDLESS_OF_ORIGINAL_GOAL_VERSION"||
  !Array.isArray(report.caseWindows)||report.caseWindows.length!==EVALS||
  !Number.isInteger(report.researchWindowCount))
  fail("INPUT_PROVENANCE_OR_VALIDATION_GATE_INVALID");
 const final=report.caseWindows.filter(x=>x.targetVersion==="FINAL_AS_PUBLISHED");
 if(final.length!==PAIRS*EVENTS)fail("FINAL_GOAL_CASE_WINDOWS_INCOMPLETE");
 const totals=new Map(),distinct2024=new Set(),distinct2025=new Set();
 let countProvisional=0;
 for(const row of report.caseWindows){
  if(row.verifiedTrade!==false||row.approvedRAASScore!==null)
   fail("CLAIMED_APPROVAL_INVALID");
  if(row.provisionalGrossReturnPct!==null)countProvisional++;
 }
 if(countProvisional!==report.researchWindowCount)
  fail("PROVISIONAL_ROW_COUNT_MISMATCH");
 for(const r of final){
  const existing=totals.get(r.caseId);
  if(existing&&(existing.ticker!==r.ticker||existing.cohortYear!==r.cohortYear))
   fail("COHORT_IDENTITY_CHANGED");
  totals.set(r.caseId,{ticker:r.ticker,cohortYear:r.cohortYear});
  (r.cohortYear===2024?distinct2024:distinct2025).add(r.ticker);
 }
 if(totals.size!==EVENTS||distinct2024.size!==5||distinct2025.size!==4||
  new Set([...distinct2024,...distinct2025]).size!==9)
  fail("RESEARCH_ISSUER_HOLDOUT_NOT_DISJOINT");
 const result=rankRows(final);
 if(result.fullGridPairsPresent!==PAIRS||result.candidateTrainOnly===null)
  fail("NO_FULL_T90_TO_T3_WINDOW_SELECTION");
 return {
  schemaVersion:1,scope:OUT,status:"RESEARCH_ONLY_NO_APPROVED_TRADING_WINDOW",
  source:"RAAS 2024-2025 live Alpaca and SEC original-source grid artifact",
  observed2024Cases:5,observed2025Cases:4,
  caseWindowsEvaluated:report.totalGoalCaseWindowEvaluations,
  provisionalCaseWindows:report.researchWindowCount,
  fullTwoYearFDACensus:false,independentVendorPriceParity:false,
  validatedTrades:0,verifiedHistoricalCapCases:0,
  approvedBestEntryExit:null,validatedRaasMetrics:0,
  ...result,
  cautions:[
   "2024-only selection is a chronology check, not statistical validation: only five outcome-selected training issuers.",
   "2025 is a separate four-issuer descriptive evaluation, but the study's nine-event source-lead selection is not an FDA census.",
   "The pooled T-76/T-63 best window was discovered using BOTH years. Its 2025 mean cannot be treated as an independent test.",
   "Testing thousands of windows inflates chance results; adjacent calendar offsets can map to the same trade sessions.",
   "Approximate net subtracts one percentage point; liquidity, live execution, daily SEC share-continuity, splits/ADR corporate actions and external adjusted-price parity are NOT validated.",
   "Do not promote any window into Pipeline filters, RAAS grades, or automatic trading."
  ]
 };
}
function csv(x){
 const a=[x.candidateTrainOnly,x.candidatePooledLookahead,...x.preObservedWindows]
   .filter(Boolean);
 const cols=["label","selectionMethod","entryLeadDays","exitLeadDays",
 "trainCases","trainMeanGrossPct","trainWins","holdoutCases","holdoutMeanGrossPct",
 "holdoutWins","pooledMeanGrossPct","approved"];
 const v=(t)=>t===null||t===undefined?"":typeof t==="number"?String(t):
   '"'+String(t).replaceAll('"','""')+'"';
 return cols.join(",")+"\n"+a.map(r=>{
  const data=[r.label,r.selectionMethod,r.entryLeadDays,r.exitLeadDays,
  r.train2024.cases,r.train2024.meanGrossPct,r.train2024.wins,
  r.holdout2025.cases,r.holdout2025.meanGrossPct,r.holdout2025.wins,
  r.all2024To2025.meanGrossPct,r.approved];
  return data.map(v).join(",");
 }).join("\n")+"\n";
}
function main(){
 try{
  const dir=path.resolve(__dirname,"..");
  const input=process.env.RAAS_T90_T3_GRID_JSON||
   path.join(dir,"raas-2024-2025-full-t90-t3-grid.json");
  const report=build(JSON.parse(fs.readFileSync(input,"utf8")));
  const json=process.env.RAAS_WALKFORWARD_JSON||
   path.join(dir,"raas-2024-2025-walkforward-selection-bias.json");
  const outCsv=process.env.RAAS_WALKFORWARD_CSV||
   path.join(dir,"raas-2024-2025-walkforward-selection-bias.csv");
  for(const file of [json,outCsv])fs.mkdirSync(path.dirname(file),{recursive:true});
  fs.writeFileSync(json,JSON.stringify(report,null,2)+"\n");
  fs.writeFileSync(outCsv,csv(report));
  const summary={status:report.status,trainFullCoveragePairs:report.trainFullCoveragePairs,
   allNineFullCoveragePairs:report.allNineFullCoveragePairs,
   trainOnlyPair:[report.candidateTrainOnly.entryLeadDays,
    report.candidateTrainOnly.exitLeadDays],
   trainMeanPct:report.candidateTrainOnly.train2024.meanGrossPct,
   holdoutMeanPct:report.candidateTrainOnly.holdout2025.meanGrossPct,
   pooledLookaheadPair:[report.candidatePooledLookahead.entryLeadDays,
    report.candidatePooledLookahead.exitLeadDays],
   verifiedTrades:0,approvedBestEntryExit:null};
  console.log(JSON.stringify(summary));
  if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
   "\n### Walk-forward selection-bias audit (research only)\n\n"+
   JSON.stringify(summary,null,2)+"\n\nNo independently approved window.\n");
 }catch(e){
  console.error("RAAS_WALKFORWARD_FATAL_"+String(e.message||e).replace(/[^A-Z0-9_]/g,"_"));
  process.exitCode=1;
 }
}
if(require.main===module)main();
module.exports={stats,rankRows,build,csv};
