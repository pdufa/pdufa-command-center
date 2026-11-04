#!/usr/bin/env node
"use strict";
/**
 * RAAS 2024–2025 historical entry-cap RESEARCH ONLY.
 * A raw Alpaca SIP close × a previously published SEC cover-share count is a
 * provisional arithmetic estimate, not a verified point-in-time market cap.
 * Adjusted and raw Alpaca bars are ONE vendor, not two independent sources.
 * No FDA outcome/approval, trading eligibility, score, or optimized window
 * can be inferred from this module.
 */
const date=s=>typeof s==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 Number.isFinite(Date.parse(s+"T00:00:00Z"))&&
 new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const secUrl=s=>typeof s==="string"&&
 /^https:\/\/www\.sec\.gov\/Archives\/edgar\/data\/[0-9]+\/[A-Za-z0-9./_-]+$/.test(s);
const int=n=>Number.isSafeInteger(n)&&n>0;
const asEntries=m=>m instanceof Map?m:new Map();
function asSECMap(feed,scope) {
 if(!feed||feed.scope!==scope||feed.schemaVersion!==1||!date(feed.sourceAsOf)||
  !Array.isArray(feed.records)||feed.records.length===0)
  throw Error("RAAS_RAW_CAP_SEC_FEED_INVALID");
 const out=new Map();
 for(const r of feed.records) {
  if(!r||typeof r.caseId!=="string"||out.has(r.caseId)||
   !/^[A-Z][A-Z0-9.-]{0,11}$/.test(r.ticker)||!/^[0-9]{10}$/.test(r.cik)||
   !int(r.sharesOutstanding)||!date(r.sharesMeasurementDate)||
   !date(r.filedDate)||!date(r.firstConservativeEntryDate)||
   !(r.sharesMeasurementDate<=r.filedDate&&r.filedDate<r.firstConservativeEntryDate)||
   !secUrl(r.sourceUrl)||r.status!=="COVER_SHARE_RESEARCH_ONLY"||
   r.needsShareContinuityAudit!==true||
   r.needsStockSplitAndDilutionAudit!==true||
   r.needsIndependentPriceCrosscheck!==true)
   throw Error("RAAS_RAW_CAP_SEC_RECORD_INVALID");
  out.set(r.caseId,r);
 }
 return out;
}
function validatedBarArray(bars,expectedBefore) {
 if(!Array.isArray(bars))return [];
 const sorted=[...bars].sort((a,b)=>a.date.localeCompare(b.date));
 const seen=new Set();
 for(const b of sorted){
  if(!b||!date(b.date)||b.date>expectedBefore||seen.has(b.date)||
   typeof b.close!=="number"||!Number.isFinite(b.close)||b.close<=0)
   throw Error("RAAS_RAW_CAP_BAR_INVALID");
  seen.add(b.date);
 }
 return sorted;
}
function auditRawEntryMarketCapResearch({
 leads,earlier,later,additionalEarliest=null,adjustedBarsByEvent,rawBarsByEvent,
 entryLeadTradingSessions=79
}) {
 if(!Array.isArray(leads)||leads.length===0||
  !Number.isInteger(entryLeadTradingSessions)||
  entryLeadTradingSessions<4||entryLeadTradingSessions>90)
  throw Error("RAAS_RAW_CAP_INPUT_INVALID");
 const a=asSECMap(earlier,"RAAS_MANUALLY_LOCATED_PRE_ENTRY_SEC_SHARES_RESEARCH");
 const b=asSECMap(later,"RAAS_MANUALLY_LOCATED_SEC_HISTORIC_COMMON_SHARE_RESEARCH");
 const additional=additionalEarliest?asSECMap(additionalEarliest,
  "RAAS_ADDITIONAL_EARLIEST_PRE_ENTRY_SEC_COVER_RESEARCH"):new Map();
 if((additionalEarliest&&additionalEarliest.sourceAsOf!==earlier.sourceAsOf)||
  [...additional.keys()].some(k=>!a.has(k))||
  earlier.sourceAsOf!==later.sourceAsOf||
  leads.length!==a.size||leads.length!==b.size)
  throw Error("RAAS_RAW_CAP_SOURCE_COVERAGE_INVALID");
 const adjusted=asEntries(adjustedBarsByEvent),raw=asEntries(rawBarsByEvent);
 const seen=new Set(),rows=[];
 for(const lead of leads) {
  if(!lead||typeof lead.caseId!=="string"||seen.has(lead.caseId)||
   !/^[A-Z][A-Z0-9.-]{0,11}$/.test(lead.ticker)||
   !date(lead.pdufaTargetDate)||lead.pdufaTargetDate<"2024-01-01"||
   lead.pdufaTargetDate>"2025-12-31"||
   !date(lead.targetAnnouncementDate)||!date(lead.phase3ReadoutDate))
   throw Error("RAAS_RAW_CAP_GOAL_INVALID");
  seen.add(lead.caseId);
  const s0=additional.get(lead.caseId),
   s1=a.get(lead.caseId),s2=b.get(lead.caseId);
  if(!s1||!s2||s1.ticker!==lead.ticker||s2.ticker!==lead.ticker||
   s1.cik!==s2.cik||s1.shareClass!==s2.shareClass||
   s1.sharesMeasurementDate>=s2.sharesMeasurementDate||
   s1.firstConservativeEntryDate>=s2.firstConservativeEntryDate||
   (s0&&(s0.ticker!==lead.ticker||s0.cik!==s1.cik||
    s0.shareClass!==s1.shareClass||
    s0.sharesMeasurementDate>=s1.sharesMeasurementDate||
    s0.filedDate>=s1.filedDate||
    s0.firstConservativeEntryDate>=s1.firstConservativeEntryDate)))
   throw Error("RAAS_RAW_CAP_CASE_IDENTITY_OR_SEQUENCE_INVALID");
  const key=lead.ticker+"|"+lead.pdufaTargetDate;
  const adj=validatedBarArray(adjusted.get(key),lead.pdufaTargetDate);
  const unchecked=validatedBarArray(raw.get(key),lead.pdufaTargetDate);
  const prior=adj.filter(x=>x.date<lead.pdufaTargetDate);
  const entry=prior.length>=entryLeadTradingSessions?
   prior[prior.length-entryLeadTradingSessions]:null;
  const rawAtEntry=entry?unchecked.find(x=>x.date===entry.date):null;
  const sources=[s0,s1,s2].filter(s=>s&&entry&&s.firstConservativeEntryDate<=entry.date);
  const selected=sources.length?sources[sources.length-1]:null;
  let reason="PROVISIONAL_CAP_ONLY_NOT_A_VALIDATED_MARKET_CAP";
  if(!entry)reason="MISSING_ADJUSTED_T79_SESSION";
  else if(!rawAtEntry)reason="MISSING_RAW_PRICE_FOR_SAME_T79_SESSION";
  else if(lead.targetAnnouncementDate>=entry.date)
   reason="PDUFA_TARGET_NOT_PUBLIC_BEFORE_ENTRY";
  else if(lead.phase3ReadoutDate>=entry.date)
   reason="PHASE3_NOT_PUBLIC_BEFORE_ENTRY";
  else if(!selected)reason="NO_SEC_COVER_PUBLIC_BY_ENTRY";
  const validPair=!!entry&&!!rawAtEntry;
  const cap=validPair&&selected&&reason==="PROVISIONAL_CAP_ONLY_NOT_A_VALIDATED_MARKET_CAP"
   ?Math.round(rawAtEntry.close*selected.sharesOutstanding/10000)/100:null;
  rows.push({
   caseId:lead.caseId,ticker:lead.ticker,pdufaTargetDate:lead.pdufaTargetDate,
   entryLeadTradingSessions,proposedEntrySession:entry?.date??null,
   adjustedCloseAlpacaAll:entry?.close??null,
   rawCloseAlpaca:rawAtEntry?.close??null,
   rawToAdjustedCloseRatio:validPair?
    Math.round(entry.close/rawAtEntry.close*1000000)/1000000:null,
   secSharesOutstanding:selected?.sharesOutstanding??null,
   secSharesMeasurementDate:selected?.sharesMeasurementDate??null,
   secFirstConservativeUse:selected?.firstConservativeEntryDate??null,
   secSourceUrl:selected?.sourceUrl??null,
   provisionalRawPriceTimesDatedSecCoverCapUsdMillions:cap,
   studyMarketCapFloorUsdMillions:300,studyMarketCapCeilingUsdMillions:10000,
   marketCap300MTo10BIndependentlyVerified:false,
   independentAdjustedPriceVendorVerified:false,
   secShareContinuityVerified:false,
   corporateActionReconciliationVerified:false,
   eligibleForValidatedRaasTradingCase:false,
   approvedRaasScore:null,
   sourceType:"ALPACA_SIP_RAW_AND_ALL_PLUS_DATED_SEC_COVER_RESEARCH_ONLY",
   status:reason
  });
 }
 return {
  schemaVersion:1,scope:"RAAS_2024_2025_RAW_CLOSE_SEC_COVER_ENTRY_CAP_RESEARCH",
  status:"RESEARCH_ONLY_NO_VALIDATED_MARKET_CAPS_OR_RETURNS",
  caseCount:rows.length,
  sameSessionRawAdjustedPricePairs:rows.filter(x=>x.rawCloseAlpaca!==null).length,
  provisionalCapEstimates:rows.filter(x=>x.provisionalRawPriceTimesDatedSecCoverCapUsdMillions!==null).length,
  independentlyValidatedEntryMarketCaps:0,
  independentlyReconciledAdjustedPricePairs:0,
  validatedTradingCases:0,approvedRaasScores:0,
  rows,
  warnings:[
   "A raw close and SEC cover-share count establish only a provisional arithmetic cap, not a validated entry-day capitalization or fully diluted ownership.",
   "Alpaca raw and all-adjusted prices originate from the same vendor; independent adjusted-price vendor parity and split/dividend/spin-off adjustment audits remain missing.",
   "A cover share count may be stale by the entry session and does not establish issuance, warrants, ADS conversion or corporate-action continuity.",
   "Only SEC filings conservatively available by each proposed trading entry may contribute shares; future filings cannot be backdated.",
   "The 2024–2025 full FDA event census, $300M–$10B qualification, issuer-disjoint training/holdout and RAAS score approvals are still blocked."
  ]
 };
}
module.exports={auditRawEntryMarketCapResearch};
