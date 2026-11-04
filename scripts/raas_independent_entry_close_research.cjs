#!/usr/bin/env node
"use strict";
/** Source-linked, research-only comparison of a historical raw Alpaca entry
 * close to independent third-party nominal closing-price leads.
 *
 * A second-source nominal match is not a split/dividend/spin-off adjustment
 * audit, an independently validated market capitalization or a RAAS return.
 */
const date=d=>typeof d==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(d)&&
 Number.isFinite(Date.parse(d+"T00:00:00Z"))&&
 new Date(d+"T00:00:00Z").toISOString().slice(0,10)===d;
function auditIndependentEntryCloses(cap,feed){
 if(!cap||cap.scope!=="RAAS_2024_2025_RAW_CLOSE_SEC_COVER_ENTRY_CAP_RESEARCH"||
  !Array.isArray(cap.rows)||!feed||feed.schemaVersion!==1||
  feed.scope!=="RAAS_2024_2025_SECOND_PROVIDER_ENTRY_NOMINAL_CLOSE_RESEARCH"||
  !date(feed.sourceAsOf)||!Array.isArray(feed.observations)||
  feed.observations.length>1000)
  throw Error("RAAS_SECOND_CLOSE_INPUT_INVALID");
 const cases=new Map(),seen=new Set(),observations=new Map();
 for(const c of cap.rows){
  if(!c||typeof c.caseId!=="string"||cases.has(c.caseId)||
   !/^[A-Z][A-Z0-9.-]{0,11}$/.test(c.ticker)||
   (c.proposedEntrySession!==null&&!date(c.proposedEntrySession)))
   throw Error("RAAS_SECOND_CLOSE_CASE_INVALID");
  cases.set(c.caseId,c);
 }
 for(const x of feed.observations){
  const c=cases.get(x?.caseId);
  if(!c||seen.has(x.caseId)||x.ticker!==c.ticker||
   (c.proposedEntrySession!==null&&x.session!==c.proposedEntrySession)||
   !date(x.session)||
   !Number.isFinite(x.nominalCloseUsd)||x.nominalCloseUsd<=0||
   x.priceAdjustmentBasis!=="NOMINAL_CLOSE_ADJUSTMENTS_UNCONFIRMED"||
   !["DAILY_SESSION_CLOSE","WEEKLY_FRIDAY_CLOSE"].includes(x.quoteGranularity)||
   x.quoteGranularity==="WEEKLY_FRIDAY_CLOSE"&&
    new Date(x.session+"T00:00:00Z").getUTCDay()!==5||
   !x.secondaryProvider?.trim()||
   /alpaca/i.test(x.secondaryProvider)||
   !/^https:\/\/[^\s/@:?#]+\/\S+$/.test(x.sourceUrl)||
   /(^|\.)alpaca\.markets$/i.test(new URL(x.sourceUrl).hostname)||
   !date(x.sourceInspectedDate)||x.sourceInspectedDate>feed.sourceAsOf||
   x.sourceInspectedDate<x.session||!x.note?.trim())
   throw Error("RAAS_SECOND_CLOSE_OBSERVATION_INVALID");
  seen.add(x.caseId);observations.set(x.caseId,x);
 }
 const rows=cap.rows.map(c=>{
  const v=observations.get(c.caseId);
  const raw=c.rawCloseAlpaca;
  const gap=raw!==null&&v&&c.proposedEntrySession===v.session?
   Math.round((v.nominalCloseUsd-raw)*10000)/10000:null;
  const matches=gap!==null&&Math.abs(gap)<=0.005;
  return {
   caseId:c.caseId,ticker:c.ticker,entrySession:c.proposedEntrySession,
   alpacaRawEntryClose:raw,independentNominalEntryClose:v?.nominalCloseUsd??null,
   independentProvider:v?.secondaryProvider??null,
   independentSourceUrl:v?.sourceUrl??null,
   independentPriceGranularity:v?.quoteGranularity??null,
   differenceUsd:gap,
   status:!v?"NO_SECOND_SOURCE_RECORDED":
    c.proposedEntrySession===null?"ALPACA_ENTRY_SESSION_UNAVAILABLE":
    raw===null?"ALPACA_RAW_PRICE_MISSING":
    matches?"INDEPENDENT_NOMINAL_CLOSE_MATCH_ADJUSTMENTS_UNAUDITED":
    "INDEPENDENT_NOMINAL_CLOSE_DISAGREEMENT",
   priceAdjustmentVerified:false,corporateActionVerified:false,
   entryMarketCapVerified:false,eligibleForValidatedRaasTradingCase:false,
   approvedRaasScore:null
  };
 });
 return {
  schemaVersion:1,scope:"RAAS_2024_2025_INDEPENDENT_ENTRY_PRICE_NOMINAL_AUDIT",
  status:"NOMINAL_PRICE_RESEARCH_ONLY",
  casesInspected:rows.length,secondSourcePriceLeads:feed.observations.length,
  matchingIndependentNominalCloses:rows.filter(x=>x.status===
   "INDEPENDENT_NOMINAL_CLOSE_MATCH_ADJUSTMENTS_UNAUDITED").length,
  mismatchedIndependentNominalCloses:rows.filter(x=>x.status===
   "INDEPENDENT_NOMINAL_CLOSE_DISAGREEMENT").length,
  missingIndependentNominalCloses:rows.filter(x=>x.status==="NO_SECOND_SOURCE_RECORDED").length,
  independentlyVerifiedAdjustedPricePairs:0,
  verifiedCorporateActionHistories:0,
  independentlyValidatedEntryMarketCaps:0,
  approvedRaasScores:0,rows,
  warnings:[
   "A nominal close from a separate historical-price website can corroborate a displayed price but does not certify adjusted total returns, source methodology, liquidity or achievable fill.",
   "The quoted external price is observed retrospectively, not an immutable entry-date RAAS prediction.",
   "An independent vendor's price, a dated SEC cover-share count and daily capitalization continuity are separate validation requirements; none of their approval gates is automatically satisfied by this nominal comparison."
  ]
 };
}
module.exports={auditIndependentEntryCloses};
