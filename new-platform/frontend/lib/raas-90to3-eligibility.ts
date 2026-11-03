/** Audits the user's 90–3-day, $300M–$10B historical research filter.
 * Source-aligned samples are NOT validated investment trades or a 10-year
 * strategy backtest. TOP uses the retrospectively known public readout date;
 * BOTTOM uses the target PDUFA date publicly known before entry.
 */
import type {TopRetrospectiveFeed} from "./raas-top-retrospective-intake";
import type {RetrospectiveFeed} from "./raas-retrospective-intake";
import type {ShareBridgeFeed} from "./raas-share-bridge";
import type {PriceCrosscheckFeed} from "./raas-price-crosschecks";
import {bridgeForCase} from "./raas-share-bridge";
import {priceAuditForCase} from "./raas-price-crosschecks";
import type {HistoricalReturnDescriptiveReport} from "./raas-historical-return-distribution";
export type RaasWindowFilterRow={
 caseId:string;ticker:string;stage:"pre"|"post";
 entryDaysBeforeEvent:number;exitDaysBeforeEvent:number;grossReturnPercent:number;
 historicalReference:"ACTUAL_READOUT_RETROSPECTIVE"|"PDUFA_TARGET_KNOWN_AT_ENTRY";
 vendorCapUsdMillions:number;secReconstructedCapUsdMillions:number|null;
 capWithin300mTo10b:boolean;secBridgeAgreesWithin2Pct:boolean;
 hasBothIndependentNominalCloses:boolean;
 eligibleCalendarWindow:boolean;
 eligibleForSourceFollowUp:boolean;
 eligibleForValidatedRaas:false;
 blockers:string[];
};
export type RaasWindowFilterReport={
 scope:"RETROSPECTIVE_90_TO_3_DAYS_300M_TO_10B_RESEARCH_ONLY";
 calendarWindowCount:number;
 issuerCapInRangeCount:number;
 matchingCapBridgeCount:number;
 eligibleForSourceFollowUpCount:number;
 eligibleForValidatedRaas:0;
 topCalendarCount:number;bottomCalendarCount:number;
 rows:RaasWindowFilterRow[];
};
export function auditRaasNinetyToThree(
 study:HistoricalReturnDescriptiveReport,top:TopRetrospectiveFeed,
 bottom:RetrospectiveFeed,shares:ShareBridgeFeed,prices:PriceCrosscheckFeed
):RaasWindowFilterReport{
 const historical=[...top.records,...bottom.records];
 const byId=new Map(historical.map(x=>[x.id,x] as const));
 if(historical.length!==study.windows.length||byId.size!==historical.length)
  throw Error("RAAS_WINDOW_FILTER_ROSTER_INVALID");
 const rows=study.windows.map(w=>{
  const record=byId.get(w.id);
  if(!record||record.stage!==w.stage||record.ticker!==w.ticker)
   throw Error("RAAS_WINDOW_FILTER_IDENTITY_INVALID");
  const marketCap=record.marketCapAtEntry.usdMillions;
  const capWithin300mTo10b=marketCap>=300&&marketCap<=10000;
  const actualReference=w.stage==="pre"?
   "ACTUAL_READOUT_RETROSPECTIVE" as const:"PDUFA_TARGET_KNOWN_AT_ENTRY" as const;
  const eligibleCalendarWindow=w.daysEntryToScheduledEvent>=3&&
   w.daysEntryToScheduledEvent<=90&&w.daysExitToScheduledEvent>=3&&
   w.daysExitToScheduledEvent<w.daysEntryToScheduledEvent&&
   (w.daysExitToActualOutcome===null||w.daysExitToActualOutcome>0);
  const sec=bridgeForCase(shares,top,bottom,w.id);
  const price=priceAuditForCase(prices,top,bottom,w.id);
  const secBridgeAgreesWithin2Pct=sec?.status==="ARITHMETIC_MATCH_REQUIRES_PRICE_AUDIT";
  const hasBothIndependentNominalCloses=price?.bothClosesAgree??false;
  const eligibleForSourceFollowUp=eligibleCalendarWindow&&capWithin300mTo10b&&
   secBridgeAgreesWithin2Pct&&hasBothIndependentNominalCloses;
  const blockers=[
   ...(!eligibleCalendarWindow?["Selected entry/exit not both in the retrospective 90-to-3 calendar-day window"]:[]),
   ...(!capWithin300mTo10b?["Vendor historical issuer cap outside $300M–$10B"]:[]),
   ...(!sec?["No pre-entry SEC share count bridge"]:!secBridgeAgreesWithin2Pct?
    ["SEC share count × vendor close conflicts with recorded cap by more than 2%"]:[]),
   ...(!hasBothIndependentNominalCloses?["Independent exact-date nominal closing-price check incomplete"]:[]),
   ...(w.stage==="pre"?["Actual public Phase 3 readout date is known only retrospectively; historical sponsor guidance cannot be treated as that exact date"]:[]),
   "Corporate action-adjusted total returns and execution costs not verified",
   "No original timestamped RAAS prediction or out-of-sample approved calibration"
  ];
  return {caseId:w.id,ticker:w.ticker,stage:w.stage,
   entryDaysBeforeEvent:w.daysEntryToScheduledEvent,
   exitDaysBeforeEvent:w.daysExitToScheduledEvent,
   grossReturnPercent:w.grossReturnPercent,
   historicalReference:actualReference,vendorCapUsdMillions:marketCap,
   secReconstructedCapUsdMillions:sec?.reconstructedEquityCapUsdMillions??null,
   capWithin300mTo10b,secBridgeAgreesWithin2Pct,
   hasBothIndependentNominalCloses,eligibleCalendarWindow,
   eligibleForSourceFollowUp,eligibleForValidatedRaas:false as const,blockers};
 });
 return {scope:"RETROSPECTIVE_90_TO_3_DAYS_300M_TO_10B_RESEARCH_ONLY",
  calendarWindowCount:rows.filter(x=>x.eligibleCalendarWindow).length,
  issuerCapInRangeCount:rows.filter(x=>x.capWithin300mTo10b).length,
  matchingCapBridgeCount:rows.filter(x=>x.secBridgeAgreesWithin2Pct).length,
  eligibleForSourceFollowUpCount:rows.filter(x=>x.eligibleForSourceFollowUp).length,
  eligibleForValidatedRaas:0,topCalendarCount:rows.filter(x=>x.stage==="pre"&&x.eligibleCalendarWindow).length,
  bottomCalendarCount:rows.filter(x=>x.stage==="post"&&x.eligibleCalendarWindow).length,
  rows};
}
