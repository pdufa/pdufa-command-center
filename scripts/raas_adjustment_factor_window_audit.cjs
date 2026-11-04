#!/usr/bin/env node
"use strict";
/**
 * Research-only full-window Alpaca SIP price-adjustment comparison.
 *
 * This compares the SAME vendor's "raw" and "all" close series over an
 * event's proposed T-79 to T-14 exchange-session window. Ratio changes are
 * possible corporate-action/adjustment INVESTIGATION LEADS only. A flat
 * ratio is not independent evidence that splits, dividends, spin-offs, cash
 * distributions, ticker changes or share counts were verified.
 *
 * Never use this output to approve a RAAS metric, trading case, validated
 * market cap, FDA outcome prediction, or retrospective optimum.
 */
const ymd=d=>typeof d==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(d)&&
 Number.isFinite(Date.parse(d+"T00:00:00Z"))&&
 new Date(d+"T00:00:00Z").toISOString().slice(0,10)===d;
const rounded=(x,n=4)=>Math.round(x*10**n)/10**n;
const EVENT_MIN=4,EVENT_MAX=90;
const SOURCE="ALPACA_SIP_1DAY_RAW_AND_ALL_SAME_VENDOR_RESEARCH";
function validBars(source,event,kind){
 if(source===undefined||source===null)return null;
 if(!Array.isArray(source)||source.length>600)throw Error("RAAS_RATIO_BARS_INVALID_"+kind);
 const seen=new Set(),sorted=[];
 for(const bar of source){
  if(!bar||!ymd(bar.date)||bar.date>event||
   !Number.isFinite(bar.close)||bar.close<=0||
   seen.has(bar.date))throw Error("RAAS_RATIO_BARS_INVALID_"+kind);
  seen.add(bar.date);sorted.push({date:bar.date,close:bar.close});
 }
 return sorted.filter(x=>x.date<event).sort((a,b)=>a.date.localeCompare(b.date));
}
function auditWindowFactors({
 leads,adjustedBarsByEvent,rawBarsByEvent,
 entryLeadTradingSessions=79,exitLeadTradingSessions=14,
 stepAlertPercent=0.5
}={}){
 if(!Array.isArray(leads)||leads.length===0||leads.length>1000||
  !(adjustedBarsByEvent instanceof Map)||!(rawBarsByEvent instanceof Map)||
  !Number.isInteger(entryLeadTradingSessions)||
  !Number.isInteger(exitLeadTradingSessions)||
  entryLeadTradingSessions<EVENT_MIN||entryLeadTradingSessions>EVENT_MAX||
  exitLeadTradingSessions<3||exitLeadTradingSessions>=entryLeadTradingSessions||
  !Number.isFinite(stepAlertPercent)||stepAlertPercent<=0||stepAlertPercent>10)
  throw Error("RAAS_RATIO_INPUT_INVALID");
 const seenCases=new Set(),seenEvents=new Set(),rows=[];
 for(const lead of leads){
  if(!lead||typeof lead.caseId!=="string"||!lead.caseId||
   !/^[A-Z][A-Z0-9.-]{0,11}$/.test(lead.ticker)||
   !ymd(lead.pdufaTargetDate)||
   lead.pdufaTargetDate<"2024-01-01"||lead.pdufaTargetDate>"2025-12-31"||
   seenCases.has(lead.caseId))
   throw Error("RAAS_RATIO_EVENT_INVALID");
  const key=lead.ticker+"|"+lead.pdufaTargetDate;
  if(seenEvents.has(key))throw Error("RAAS_RATIO_EVENT_DUPLICATE");
  seenCases.add(lead.caseId);seenEvents.add(key);
  const adjusted=validBars(adjustedBarsByEvent.get(key),lead.pdufaTargetDate,"ALL");
  const raw=validBars(rawBarsByEvent.get(key),lead.pdufaTargetDate,"RAW");
  const enough=adjusted!==null&&adjusted.length>=entryLeadTradingSessions;
  const entry=enough?adjusted[adjusted.length-entryLeadTradingSessions]:null;
  const exit=enough&&adjusted.length>=exitLeadTradingSessions?
   adjusted[adjusted.length-exitLeadTradingSessions]:null;
  const window=entry&&exit?adjusted.filter(x=>x.date>=entry.date&&x.date<=exit.date):[];
  const byRaw=new Map((raw||[]).map(x=>[x.date,x.close]));
  const paired=window.filter(x=>byRaw.has(x.date)).map(x=>({
   date:x.date,rawClose:byRaw.get(x.date),adjustedClose:x.close,
   factor:x.close/byRaw.get(x.date)
  }));
  const missingRaw=window.filter(x=>!byRaw.has(x.date)).map(x=>x.date);
  const extraRaw=entry&&exit?(raw||[])
   .filter(x=>x.date>=entry.date&&x.date<=exit.date&&
    !window.some(w=>w.date===x.date)).map(x=>x.date):[];
  const stepCandidates=[];
  let largestStep=0;
  for(let i=1;i<paired.length;i++){
   if(paired[i-1].date===paired[i].date)throw Error("RAAS_RATIO_BAR_DUPLICATE");
   // A missing raw session breaks factor continuity. Never treat the
   // two non-adjacent observations as evidence of a one-session event.
   const prevAdjustedIndex=window.findIndex(x=>x.date===paired[i-1].date);
   const nextAdjustedIndex=window.findIndex(x=>x.date===paired[i].date);
   if(nextAdjustedIndex!==prevAdjustedIndex+1)continue;
   const changePct=100*(paired[i].factor/paired[i-1].factor-1);
   largestStep=Math.max(largestStep,Math.abs(changePct));
   if(Math.abs(changePct)>=stepAlertPercent){
    stepCandidates.push({
     previousSession:paired[i-1].date,session:paired[i].date,
     changeInAdjustedToRawFactorPct:rounded(changePct),
     status:"POTENTIAL_ADJUSTMENT_FACTOR_STEP_UNATTRIBUTED"
    });
   }
  }
  const full=!!entry&&!!exit&&raw!==null&&
   missingRaw.length===0&&extraRaw.length===0&&
   paired.length===window.length;
  const first=full?paired[0]:null,last=full?paired.at(-1):null;
  rows.push({
   caseId:lead.caseId,ticker:lead.ticker,pdufaTargetDate:lead.pdufaTargetDate,
   entryLeadTradingSessions,exitLeadTradingSessions,
   proposedEntrySession:entry?.date??null,proposedExitSession:exit?.date??null,
   adjustedWindowSessions:window.length,
   sameDateRawAdjustedPairs:paired.length,
   missingRawSessions:missingRaw,rawOnlySessions:extraRaw,
   entryAdjustedToRawFactor:first?rounded(first.factor,8):null,
   exitAdjustedToRawFactor:last?rounded(last.factor,8):null,
   entryToExitFactorChangePct:first&&last?
    rounded(100*(last.factor/first.factor-1)):null,
   largestConsecutiveSessionFactorStepPct:full?rounded(largestStep):null,
   factorStepAlertThresholdPercent:stepAlertPercent,
   adjustmentFactorStepCandidates:stepCandidates,
   completeSameVendorWindow:full,
   researchStatus:!enough?"INSUFFICIENT_ADJUSTED_TRADING_SESSIONS":
    raw===null?"MISSING_RAW_PRICE_SERIES":
    !full?"RAW_ADJUSTED_SESSION_GAPS":
    stepCandidates.length?"FACTOR_CHANGE_CANDIDATES_REQUIRES_SOURCE_AUDIT":
    "NO_LARGE_FACTOR_STEP_OBSERVED_NOT_ACTION_VERIFIED",
   sameVendorOnly:true,independentAdjustedPriceVendorVerified:false,
   exchangeSessionAndTickerContinuityVerified:false,
   dividendSplitSpinOffAndADRReconciliationVerified:false,
   entryCapIndependentlyValidated:false,
   eligibleForValidatedRaasTradingCase:false,
   approvedRaasMetricGrades:0
  });
 }
 return {
  schemaVersion:1,
  scope:"RAAS_2024_2025_FULL_WINDOW_ADJUSTMENT_FACTOR_RESEARCH",
  status:"RESEARCH_ONLY_NOT_CORPORATE_ACTION_VERIFIED",
  source:SOURCE,
  caseCount:rows.length,
  casesWithCompleteSameVendorPriceWindow:rows.filter(x=>x.completeSameVendorWindow).length,
  pairedSessionsInSelectedWindows:rows.reduce((n,x)=>n+x.sameDateRawAdjustedPairs,0),
  missingRawSessionsInSelectedWindows:rows.reduce((n,x)=>n+x.missingRawSessions.length,0),
  casesWithFactorStepCandidates:rows.filter(x=>x.adjustmentFactorStepCandidates.length>0).length,
  totalFactorStepCandidates:rows.reduce((n,x)=>n+x.adjustmentFactorStepCandidates.length,0),
  independentlyVerifiedCorporateActionHistories:0,
  independentlyVerifiedAdjustedReturnWindows:0,
  independentlyVerifiedMarketCaps:0,
  validatedTradingCases:0,approvedRaasMetricGrades:0,
  rows,
  warnings:[
   "Raw and all-adjusted daily prices are from the SAME Alpaca SIP vendor; this cannot independently validate splits, dividends, ADRs or total returns.",
   "A stable raw-to-adjusted factor or no flagged step does NOT establish that no corporate action occurred; small changes, vendor methodology and events outside this window remain unexamined.",
   "Factor jumps are not identified corporate actions. Each requires dated issuer/exchange/vendor records and an independent adjusted-price cross-check.",
   "The T-79 to T-14 window is a research example. FDA actual-action censoring, full eligible 2024–2025 census, point-in-time market-cap qualification, issuer-disjoint holdout and calibrated RAAS scores remain unverified."
  ]
 };
}
module.exports={auditWindowFactors};
