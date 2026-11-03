/** SEC cover-share evidence known at the proposed T-79 regular session.
 * This is a point-in-time source-availability bridge, NOT a verification
 * of trading-day shares, float, USD market cap, adjusted bars or returns.
 * No FDA outcomes are imported into the pre-entry feature.
 */
import primarySource from "../data/raas-active-2024-2025-primary-source-leads.json";
import earlySource from "../data/raas-active-2024-2025-preentry-sec-share-leads.json";
import laterSource from "../data/raas-active-2024-2025-sec-cover-share-leads.json";
import {activePdufaGoalAsOfAudit,type GoalAsOfAudit} from "./raas-pdufa-goal-asof-metric-audit";

type SECRow={
 caseId:string;ticker:string;cik:string;venue:string;shareClass:string;
 securityCurrency:string;rawCloseCurrency:string;status:string;
 sharesOutstanding:number;sharesMeasurementDate:string;filedDate:string;
 firstConservativeEntryDate:string;sourceUrl:string;
 needsShareContinuityAudit:boolean;needsStockSplitAndDilutionAudit:boolean;
 needsIndependentPriceCrosscheck:boolean;
};
type SECFeed={schemaVersion:number;scope:string;sourceAsOf:string;records:SECRow[]};
type PrimaryFeed={schemaVersion:number;scope:string;sourceAsOf:string;
 records:{caseId:string;ticker:string;application:string;pdufaTargetDate:string}[]};
export type SECAsOfCase={
 caseId:string;ticker:string;application:string;
 proposedEntrySession:string;proposedExitSession:string;
 currentSECSourceUrl:string|null;currentSECShares:number|null;
 currentSECSharesMeasurementDate:string|null;currentSECFirstConservativeUse:string|null;
 currentSECDisclosureAgeDays:number|null;
 earlierCoverShares:number;laterCoverShares:number;shareSnapshotDifference:number;
 earlierSECUrl:string;laterSECUrl:string;
 laterCoverAvailableAtEntry:boolean;laterCoverWasNotYetPublicAtEntry:boolean;
 sourceAtEntryStatus:"Dated_SEC_cover_available_unverified"|"NO_SEC_cover_public_by_entry";
 underlyingSharesContinuousVerified:false;corporateActionsVerified:false;
 independentAdjustedEntryPriceVerified:false;independentAdjustedExitPriceVerified:false;
 entryMarketCapUsdMillions:null;entryMarketCap300Mto10BValidated:false;
 adjustedHistoricalReturnPct:null;validatedRaasScore:null;
};
export type SECAsOfReport={
 schemaVersion:1;scope:"RAAS_2024_2025_SEC_SHARES_ASOF_T79_SESSION_RESEARCH";
 status:"RESEARCH_SOURCE_AVAILABILITY_ONLY";
 sourceAsOf:string;caseCount:number;coverFactsPublicAtProposedEntry:number;
 coverFactsMissingAtProposedEntry:number;laterSnapshotsUnavailableAtEntry:number;
 independentlyValidatedEntryMarketCaps:0;independentlyVerifiedPricePairs:0;
 calibratedRaasScores:0;rows:SECAsOfCase[];warnings:string[];
};
const dateOK=(s:unknown):s is string=>typeof s==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 !Number.isNaN(Date.parse(s+"T00:00:00Z"))&&new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const diff=(a:string,b:string)=>(Date.parse(a+"T00:00:00Z")-Date.parse(b+"T00:00:00Z"))/86400000;
const secURL=(s:unknown)=>typeof s==="string"&&
 /^https:\/\/www\.sec\.gov\/Archives\/edgar\/data\/[0-9]+\/[A-Za-z0-9./_-]+$/.test(s);
const int=(v:unknown)=>typeof v==="number"&&Number.isSafeInteger(v)&&v>0;
function rowsByCase(feed:SECFeed,scope:string):Map<string,SECRow>{
 if(feed?.schemaVersion!==1||feed.scope!==scope||!dateOK(feed.sourceAsOf)||
  !Array.isArray(feed.records)||feed.records.length<1||feed.records.length>1000)
  throw Error("RAAS_SEC_ASOF_FEED_INVALID");
 const out=new Map<string,SECRow>();
 for(const row of feed.records){
  if(!row||typeof row.caseId!=="string"||out.has(row.caseId)||
   !/^[A-Z][A-Z0-9.-]{0,11}$/.test(row.ticker)||!/^[0-9]{10}$/.test(row.cik)||
   row.venue!=="NASDAQ"||row.securityCurrency!=="USD"||row.rawCloseCurrency!=="USD"||
   row.status!=="COVER_SHARE_RESEARCH_ONLY"||!int(row.sharesOutstanding)||
   !dateOK(row.sharesMeasurementDate)||!dateOK(row.filedDate)||
   !dateOK(row.firstConservativeEntryDate)||
   row.sharesMeasurementDate>row.filedDate||row.filedDate>=row.firstConservativeEntryDate||
   row.firstConservativeEntryDate>feed.sourceAsOf||!secURL(row.sourceUrl)||
   row.needsShareContinuityAudit!==true||row.needsStockSplitAndDilutionAudit!==true||
   row.needsIndependentPriceCrosscheck!==true||!row.shareClass?.trim())
    throw Error("RAAS_SEC_ASOF_SOURCE_ROW_INVALID");
  out.set(row.caseId,row);
 }
 return out;
}
export function auditSECAsOfEntryShares(
 primary:PrimaryFeed,earlier:SECFeed,later:SECFeed,goal:GoalAsOfAudit
):SECAsOfReport{
 if(primary?.scope!=="RAAS_HISTORICAL_PRIMARY_PDUFA_EVENT_EVIDENCE_RESEARCH"||
  primary.schemaVersion!==1||!dateOK(primary.sourceAsOf)||
  !Array.isArray(primary.records)||goal?.scope!=="RAAS_2024_2025_PDUFA_GOAL_VERSION_ASOF_INPUT_AUDIT"||
  goal.status!=="RESEARCH_ONLY_NO_APPROVED_METRIC_SCORES"||
  goal.approvedOverallRaasScores!==0||goal.validatedHistoricalTradingCases!==0||
  !Array.isArray(goal.cases)||goal.sourceCases!==primary.records.length||
  primary.sourceAsOf!==goal.sourceAsOf||
  primary.sourceAsOf!==earlier.sourceAsOf||primary.sourceAsOf!==later.sourceAsOf)
  throw Error("RAAS_SEC_ASOF_SCOPE_OR_CALIBRATION_INVALID");
 const a=rowsByCase(earlier,"RAAS_MANUALLY_LOCATED_PRE_ENTRY_SEC_SHARES_RESEARCH"),
  b=rowsByCase(later,"RAAS_MANUALLY_LOCATED_SEC_HISTORIC_COMMON_SHARE_RESEARCH");
 if(a.size!==primary.records.length||b.size!==primary.records.length||
  new Set(primary.records.map(p=>p.caseId)).size!==primary.records.length||
  new Set(goal.cases.map(p=>p.caseId)).size!==goal.cases.length)
  throw Error("RAAS_SEC_ASOF_INCOMPLETE_SOURCE_COVERAGE");
 const byGoal=new Map(goal.cases.map(x=>[x.caseId,x]));
 const results:SECAsOfCase[]=[];
 for(const p of primary.records){
  const first=a.get(p.caseId),last=b.get(p.caseId),g=byGoal.get(p.caseId);
  if(!first||!last||!g||p.ticker!==first.ticker||p.ticker!==last.ticker||
   p.ticker!==g.ticker||p.application!==g.application||
   first.cik!==last.cik||first.shareClass!==last.shareClass||
   first.sourceUrl===last.sourceUrl||
   first.sharesMeasurementDate>=last.sharesMeasurementDate||
   first.filedDate>=last.filedDate||
   first.firstConservativeEntryDate>=last.firstConservativeEntryDate||
   p.pdufaTargetDate!==g.eventTargetDate||
   !g.finalTargetKnownAtFinalT79Entry)
   throw Error("RAAS_SEC_ASOF_CASE_CHRONOLOGY_OR_IDENTITY_INVALID");
  const entry=g.current.indicativeEntrySessionDate,exit=g.current.indicativeExitSessionDate;
  if(!dateOK(entry)||!dateOK(exit)||entry>=exit||
   entry<g.current.calendarEntryDate||exit>g.current.calendarExitDate||
   g.current.targetWasPublishedByCalendarEntry!==true)
   throw Error("RAAS_SEC_ASOF_BAD_TRADING_SESSION_CONTEXT");
  const accessible=[first,last].filter(s=>s.firstConservativeEntryDate<=entry);
  const selected=accessible.length?accessible[accessible.length-1]:null;
  results.push({
   caseId:p.caseId,ticker:p.ticker,application:p.application,
   proposedEntrySession:entry,proposedExitSession:exit,
   currentSECSourceUrl:selected?.sourceUrl??null,
   currentSECShares:selected?.sharesOutstanding??null,
   currentSECSharesMeasurementDate:selected?.sharesMeasurementDate??null,
   currentSECFirstConservativeUse:selected?.firstConservativeEntryDate??null,
   currentSECDisclosureAgeDays:selected?diff(entry,selected.sharesMeasurementDate):null,
   earlierCoverShares:first.sharesOutstanding,laterCoverShares:last.sharesOutstanding,
   shareSnapshotDifference:last.sharesOutstanding-first.sharesOutstanding,
   earlierSECUrl:first.sourceUrl,laterSECUrl:last.sourceUrl,
   laterCoverAvailableAtEntry:last.firstConservativeEntryDate<=entry,
   laterCoverWasNotYetPublicAtEntry:last.firstConservativeEntryDate>entry,
   sourceAtEntryStatus:selected?"Dated_SEC_cover_available_unverified":"NO_SEC_cover_public_by_entry",
   underlyingSharesContinuousVerified:false,corporateActionsVerified:false,
   independentAdjustedEntryPriceVerified:false,independentAdjustedExitPriceVerified:false,
   entryMarketCapUsdMillions:null,entryMarketCap300Mto10BValidated:false,
   adjustedHistoricalReturnPct:null,validatedRaasScore:null
  });
 }
 const present=results.filter(x=>x.currentSECShares!==null).length;
 return {schemaVersion:1,scope:"RAAS_2024_2025_SEC_SHARES_ASOF_T79_SESSION_RESEARCH",
  status:"RESEARCH_SOURCE_AVAILABILITY_ONLY",sourceAsOf:primary.sourceAsOf,
  caseCount:results.length,coverFactsPublicAtProposedEntry:present,
  coverFactsMissingAtProposedEntry:results.length-present,
  laterSnapshotsUnavailableAtEntry:results.filter(x=>x.laterCoverWasNotYetPublicAtEntry).length,
  independentlyValidatedEntryMarketCaps:0,independentlyVerifiedPricePairs:0,
  calibratedRaasScores:0,rows:results,
  warnings:[
   "SEC cover shares are historical publication snapshots; they do not establish exact same-day outstanding shares, fully diluted ownership or market capitalization.",
   "Only a filing with a conservative first-usable date not later than the proposed entry is eligible; later SEC cover snapshots must never backfill entry features.",
   "Entry and exit sessions are exchange-calendar proposals, not independently verified traded bars or adjusted prices.",
   "The second adjusted-price vendor, split and dilution adjustments, full FDA census and out-of-sample validation are missing. No RAAS score is approved."
  ]};
}
export const activeSECAsOfEntryShares=()=>auditSECAsOfEntryShares(
 primarySource as unknown as PrimaryFeed,
 earlySource as unknown as SECFeed,
 laterSource as unknown as SECFeed,
 activePdufaGoalAsOfAudit()
);
