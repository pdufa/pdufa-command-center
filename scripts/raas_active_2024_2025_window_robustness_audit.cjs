#!/usr/bin/env node
"use strict";
/**
 * Eight-or-more-case, issuer-disjoint 2024/2025 T-79 -> T-14 robustness AUDIT.
 * Descriptive sensitivity only. Never optimize a date from this selected sample.
 * The 2025 holdout is never pooled into 2024 training for parameter selection.
 */
const fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"..");
const INPUT="RAAS_ACTIVE_2024_2025_T79_TO_T14_RESEARCH_AUDIT";
const OUT="RAAS_ACTIVE_2024_2025_T79_TO_T14_ROBUSTNESS_ONLY";
const round=n=>Math.round((n+Number.EPSILON)*100)/100;
const median=x=>{const a=x.slice().sort((u,v)=>u-v),n=a.length;
 return n%2?a[(n-1)/2]:(a[n/2-1]+a[n/2])/2;};
const mean=x=>round(x.reduce((a,b)=>a+b,0)/x.length);
function build(audit){
 if(!audit||audit.scope!==INPUT||
  audit.status!=="UNVALIDATED_PROVISIONAL_RETURN_DIAGNOSTIC_ONLY"||
  audit.independentlyValidatedTradingCases!==0||audit.approvedRaasMetrics!==0||
  audit.completedFDAFullCensusYears!==0||audit.approvedOptimalWindow!==null||
  audit.window?.entryLeadCalendarDays!==79||audit.window?.exitLeadCalendarDays!==14||
  !Array.isArray(audit.rows)||audit.rows.length<3||
  audit.rows.length!==audit.sourceCaseCount||
  audit.requiredIndependentTrainIssuers!==30||
  audit.requiredIndependentHoldoutIssuers!==30)
  throw Error("RAAS_SENSITIVITY_UNTRUSTED_SOURCE");
 const seen=new Set(),tickerYear=new Map(),eligible=[];
 let blocked=0;
 for(const r of audit.rows){
  if(!r||typeof r.caseId!=="string"||!r.caseId||
   typeof r.ticker!=="string"||!/^[A-Z][A-Z0-9.-]{0,11}$/.test(r.ticker)||
   seen.has(r.caseId)||![2024,2025].includes(r.year)||
   !["APPROVED","CRL"].includes(r.actualFdaOutcomeRetrospective)||
   r.validatedTradingCase!==false||r.approvedRaasMetric!==false||
   r.independentlyVerifiedPrice!==false||r.completeFDAEventCensus!==false||
   typeof r.entryDate!=="string"||typeof r.exitDate!=="string"||
   r.entryDate>=r.exitDate||r.exitDate>=r.actualFdaActionDate||
   r.entryDate<r.goalFirstPublicDate||
   !["UNVALIDATED_ALPACA_PRICE_RESEARCH","BLOCKED_RESEARCH_WINDOW"].includes(r.status))
   throw Error("RAAS_SENSITIVITY_CASE_OR_CHRONOLOGY_INVALID");
  seen.add(r.caseId);
  if(tickerYear.has(r.ticker))
   throw Error("RAAS_SENSITIVITY_ISSUER_NOT_INDEPENDENT");
  tickerYear.set(r.ticker,r.year);
  if(r.status==="BLOCKED_RESEARCH_WINDOW"){
   if(r.grossReturnPct!==null||r.hypotheticalNetReturnPct!==null||
    r.entryCapResearchMillions!==null)throw Error("RAAS_SENSITIVITY_BLOCKED_RETURNS_NOT_NULL");
   blocked++;continue;
  }
  if(typeof r.grossReturnPct!=="number"||!Number.isFinite(r.grossReturnPct)||
   r.grossReturnPct< -100||
   typeof r.hypotheticalNetReturnPct!=="number"||
   !Number.isFinite(r.hypotheticalNetReturnPct)||
   Math.abs(r.hypotheticalNetReturnPct-(r.grossReturnPct-1))>0.03||
   typeof r.entryCapResearchMillions!=="number"||
   !Number.isFinite(r.entryCapResearchMillions)||
   r.entryCapResearchMillions<300||r.entryCapResearchMillions>10000)
   throw Error("RAAS_SENSITIVITY_PROVISIONAL_PRICE_INVALID");
  eligible.push(r);
 }
 if(eligible.length<3||blocked!==audit.blockedCases)
  throw Error("RAAS_SENSITIVITY_INSUFFICIENT_OBSERVATIONS");
 const gross=eligible.map(r=>r.grossReturnPct),allMean=mean(gross);
 const groups=(filter)=>{const a=eligible.filter(filter).map(r=>r.grossReturnPct);
  return {cases:a.length,meanGrossPct:a.length?mean(a):null,
   medianGrossPct:a.length?round(median(a)):null,
   positive:a.filter(v=>v>0).length,negative:a.filter(v=>v<0).length};};
 const loo=eligible.map(r=>{
  const remaining=eligible.filter(o=>o.caseId!==r.caseId).map(o=>o.grossReturnPct);
  const otherMean=mean(remaining);
  return {tickerOmitted:r.ticker,omittedYear:r.year,
   outcomeKnownOnlyAfterFDA:r.actualFdaOutcomeRetrospective,
   omittedGrossPct:r.grossReturnPct,remainingCases:remaining.length,
   remainingMeanGrossPct:otherMean,
   changeFromAllMeanPctPoints:round(otherMean-allMean)};
 }).sort((a,b)=>Math.abs(b.changeFromAllMeanPctPoints)-Math.abs(a.changeFromAllMeanPctPoints)||
  a.tickerOmitted.localeCompare(b.tickerOmitted));
 const x=gross.slice().sort((a,b)=>a-b),trimmed=x.slice(1,-1);
 const year2024=groups(r=>r.year===2024),year2025=groups(r=>r.year===2025);
 if(year2024.cases===0||year2025.cases===0)
  throw Error("RAAS_SENSITIVITY_TRAIN_HOLDOUT_NOT_SEPARATE");
 const worst=loo[0];
 return {schemaVersion:1,scope:OUT,status:"UNVALIDATED_SELECTED_SAMPLE_FRAGILITY_DIAGNOSTIC",
  sourceCaseCount:audit.sourceCaseCount,usableCases:eligible.length,blockedCases:blocked,
  all:{...groups(()=>true),hypotheticalNetMeanPct:round(allMean-1)},
  byYear:{2024:{role:"TRAIN_DESCRIPTIVE_ONLY",...year2024},
   2025:{role:"ISSUER_DISJOINT_HOLDOUT_DESCRIPTIVE_ONLY",...year2025}},
  byRetrospectiveOutcome:{APPROVED:groups(r=>r.actualFdaOutcomeRetrospective==="APPROVED"),
   CRL:groups(r=>r.actualFdaOutcomeRetrospective==="CRL")},
  leaveOneIssuerOut:loo,
  maxAbsoluteOneIssuerEffectPctPoints:Math.abs(worst.changeFromAllMeanPctPoints),
  mostInfluentialIssuerTicker:worst.tickerOmitted,
  trimmedOneEachGrossMeanPct:round(mean(trimmed)),
  fullYearCensusesAudited:0,independentlyValidatedTrades:0,
  approvedRaasMetrics:0,approvedOptimalWindow:null,
  calibrationPermitted:false,prospectiveFDAOutcomeKnownAtEntry:false,
  warnings:[
   "Leave-one-issuer-out and trimmed means measure fragility, not a tested entry/exit strategy.",
   "Returns are from an issuer/outcome-selected, incomplete FDA event cohort, not an unbiased target-year census.",
   "Retrospective APPROVED/CRL labels are diagnostic only; impossible to use at entry without lookahead.",
   "2024 train and issuer-disjoint 2025 holdout remain separate and too small (30/30 minimum).",
   "Gross historical Alpaca price research still lacks independent price, split, share-continuity and trading-cost validation.",
   "Do not select T-79/T-14 or any other trading window based on these statistics."
  ]};
}
function csv(result){
 if(result?.scope!==OUT)throw Error("RAAS_SENSITIVITY_CSV_INVALID");
 const header=["tickerOmitted","omittedYear","outcomeKnownOnlyAfterFDA",
  "omittedGrossPct","remainingCases","remainingMeanGrossPct","changeFromAllMeanPctPoints"];
 const nums=new Set(["omittedYear","omittedGrossPct","remainingCases",
  "remainingMeanGrossPct","changeFromAllMeanPctPoints"]);
 const cell=(k,v)=>{
  if(nums.has(k)){if(typeof v!=="number"||!Number.isFinite(v))
   throw Error("RAAS_SENSITIVITY_NUMERIC_EXPORT_INVALID");return String(v);}
  const t=String(v??""),safe=/^[\s\u0000-\u001f]*[=+\-@]/.test(t)?"'"+t:t;
  return '"'+safe.replaceAll('"','""')+'"';
 };
 return header.join(",")+"\n"+result.leaveOneIssuerOut.map(r=>
  header.map(k=>cell(k,r[k])).join(",")).join("\n")+"\n";
}
function main(){
 try{
  const input=process.env.RAAS_T79_14_AUDIT_JSON||path.join(root,"raas-2024-2025-t79-14-audit.json");
  const out=process.env.RAAS_T79_14_ROBUSTNESS_JSON||path.join(root,"raas-2024-2025-t79-14-robustness.json");
  const csvPath=process.env.RAAS_T79_14_ROBUSTNESS_CSV||path.join(root,"raas-2024-2025-t79-14-leave-one-out.csv");
  const result=build(JSON.parse(fs.readFileSync(input,"utf8")));
  for(const p of [out,csvPath])fs.mkdirSync(path.dirname(p),{recursive:true});
  fs.writeFileSync(out,JSON.stringify(result,null,2)+"\n");
  fs.writeFileSync(csvPath,csv(result));
  const summary={status:result.status,sourceCases:result.sourceCaseCount,
   allMean:result.all.meanGrossPct,trimmedMean:result.trimmedOneEachGrossMeanPct,
   largestOneIssuerShift:result.maxAbsoluteOneIssuerEffectPctPoints,
   mostInfluentialIssuer:result.mostInfluentialIssuerTicker,
   train:result.byYear[2024],holdout:result.byYear[2025],
   validatedTrades:0,approvedRaasMetrics:0};
  console.log(JSON.stringify(summary));
  if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
   "### T-79 / T-14 sample-selection sensitivity (NOT BACKTEST VALIDATION)\n\n"+
   JSON.stringify(summary,null,2)+"\n\nNo optimal window, prospective RAAS score, or trade approval.\n");
 }catch(e){console.error("RAAS_SENSITIVITY_FATAL_"+String(e.message||e).replace(/[^A-Z0-9_]/g,"_"));process.exitCode=1;}
}
if(require.main===module)main();
module.exports={build,csv};
