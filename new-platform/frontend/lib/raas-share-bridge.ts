/** Research-only historical share-price to capitalization arithmetic.
 * NEVER certifies market data, fully diluted value, or predictive validity.
 * A SEC cover-page share count must have been public BEFORE the chosen
 * historical close; on the entry date, an exchange-hour timestamp is required.
 */
import type {TopRetrospectiveFeed} from "./raas-top-retrospective-intake";
import type {RetrospectiveFeed} from "./raas-retrospective-intake";
export type ShareBridgeRecord={
 caseId:string;ticker:string;stage:"pre"|"post";class:"COMMON"|"ADS";
 securityLabel:string;sharesOutstanding:number;sharesAsOf:string;
 sharesPublishedAt:string;sharesPublishedTimeEastern?:string;
 sharesSourceUrl:string;ordinarySharesPerQuotedSecurity:number;
 quoteCurrency:"USD";notes:string;
};
export type ShareBridgeFeed={
 schemaVersion:1;scope:"RAAS_HISTORICAL_SHARE_BRIDGE_RESEARCH";
 sourceAsOf:string;note:string;records:ShareBridgeRecord[];
};
export type CapBridge={
 caseId:string;ticker:string;stage:"pre"|"post";
 quotedSharesEquivalent:number;observedEntryPrice:number;
 reconstructedEquityCapUsdMillions:number;vendorCapUsdMillions:number;
 absoluteDifferenceUsdMillions:number;relativeDifferencePercent:number;
 shareSourceUrl:string;priceSourceUrl:string;vendorCapSourceUrl:string;
 shareCountAsOf:string;sharePublishedAt:string;
 status:"ARITHMETIC_MATCH_REQUIRES_PRICE_AUDIT"|"ARITHMETIC_MISMATCH";
 fullyDilutedReconciled:false;corporateActionsReconciled:false;entryPriceIndependentlyVerified:false;
 approvedRaasScore:false;
};
const validDate=(s:string):boolean=>/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 Number.isFinite(Date.parse(s+"T00:00:00Z"))&&new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const validUrl=(s:string):boolean=>/^https:\/\/[^\s/]+\/\S+/.test(s);
const integer=(n:unknown):n is number=>typeof n==="number"&&Number.isSafeInteger(n)&&n>0;
const ratio=(n:unknown):n is number=>integer(n)&&n<=100000;
const round=(n:number)=>Math.round(n*100)/100;
type CaseSnapshot={id:string;ticker:string;stage:"pre"|"post";entryDate:string;entryClose:number;
 priceUrl:string;vendorCap:number;capUrl:string};
const caseSnapshots=(top:TopRetrospectiveFeed,bottom:RetrospectiveFeed):CaseSnapshot[]=>[
 ...top.records.map(r=>({id:r.id,ticker:r.ticker,stage:"pre" as const,entryDate:r.entry.date,entryClose:r.entry.close,
  priceUrl:r.entry.sourceUrl,vendorCap:r.marketCapAtEntry.usdMillions,capUrl:r.marketCapAtEntry.sourceUrl})),
 ...bottom.records.map(r=>({id:r.id,ticker:r.ticker,stage:"post" as const,entryDate:r.entry.date,entryClose:r.entry.close,
  priceUrl:r.entry.sourceUrl,vendorCap:r.marketCapAtEntry.usdMillions,capUrl:r.marketCapAtEntry.sourceUrl}))
];
export function parseShareBridge(input:unknown,top:TopRetrospectiveFeed,bottom:RetrospectiveFeed):ShareBridgeFeed{
 if(!input||typeof input!=="object")throw Error("RAAS_SHARE_BRIDGE_INVALID");
 const feed=input as ShareBridgeFeed;
 if(feed.schemaVersion!==1||feed.scope!=="RAAS_HISTORICAL_SHARE_BRIDGE_RESEARCH"||
 !validDate(feed.sourceAsOf)||!Array.isArray(feed.records)||feed.records.length>10000)
  throw Error("RAAS_SHARE_BRIDGE_INVALID");
 const cases=new Map(caseSnapshots(top,bottom).map(c=>[c.id,c] as const));
 const seen=new Set<string>();
 for(const row of feed.records){
  const c=cases.get(row?.caseId);
  if(!c||seen.has(row.caseId)||!row.notes?.trim()||!row.securityLabel?.trim()||
   row.ticker?.trim().toUpperCase()!==c.ticker.trim().toUpperCase()||
   row.stage!==c.stage||!integer(row.sharesOutstanding)||!ratio(row.ordinarySharesPerQuotedSecurity)||
   (row.class!=="COMMON"&&row.class!=="ADS")||
   (row.class==="COMMON"&&row.ordinarySharesPerQuotedSecurity!==1)||
   (row.class==="ADS"&&row.ordinarySharesPerQuotedSecurity<=1)||
   row.quoteCurrency!=="USD"||!validDate(row.sharesAsOf)||!validDate(row.sharesPublishedAt)||
   row.sharesAsOf>row.sharesPublishedAt||row.sharesPublishedAt>feed.sourceAsOf||
   row.sharesPublishedAt>c.entryDate||!validUrl(row.sharesSourceUrl))
   throw Error("RAAS_SHARE_BRIDGE_RECORD_INVALID");
  // Same-entry-day filings can only enter a close-to-close example if SEC acceptance
  // is timestamped no later than the 4:00 PM Eastern normal-session close.
  if(row.sharesPublishedAt===c.entryDate){
   if(!row.sharesPublishedTimeEastern||
     !/^(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d$/.test(row.sharesPublishedTimeEastern)||
     row.sharesPublishedTimeEastern>"16:00:00")
    throw Error("RAAS_SHARE_BRIDGE_SAME_DAY_TIMING_INVALID");
  }else if(row.sharesPublishedTimeEastern&&
   !/^(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d$/.test(row.sharesPublishedTimeEastern))
    throw Error("RAAS_SHARE_BRIDGE_TIME_INVALID");
  seen.add(row.caseId);
 }
 return feed;
}
/** Checks only SEC share-count * vendor price ~= vendor equity cap.
 * One matched multiplication does NOT make the source price authoritative.
 */
export function bridgeForCase(feed:ShareBridgeFeed,top:TopRetrospectiveFeed,
 bottom:RetrospectiveFeed,caseId:string):CapBridge|null{
 const record=feed.records.find(r=>r.caseId===caseId);
 const hist=caseSnapshots(top,bottom).find(c=>c.id===caseId);
 if(!record||!hist)return null;
 const quoteUnits=record.sharesOutstanding/record.ordinarySharesPerQuotedSecurity;
 const cap=quoteUnits*hist.entryClose/1e6;
 const diff=cap-hist.vendorCap;
 const diffPct=diff/hist.vendorCap*100;
 return {caseId,ticker:record.ticker,stage:record.stage,quotedSharesEquivalent:quoteUnits,
  observedEntryPrice:hist.entryClose,reconstructedEquityCapUsdMillions:round(cap),
  vendorCapUsdMillions:hist.vendorCap,absoluteDifferenceUsdMillions:round(diff),
  relativeDifferencePercent:round(diffPct),
  shareSourceUrl:record.sharesSourceUrl,priceSourceUrl:hist.priceUrl,vendorCapSourceUrl:hist.capUrl,
  shareCountAsOf:record.sharesAsOf,sharePublishedAt:record.sharesPublishedAt,
  status:Math.abs(diffPct)<=2?"ARITHMETIC_MATCH_REQUIRES_PRICE_AUDIT":"ARITHMETIC_MISMATCH",
  fullyDilutedReconciled:false,corporateActionsReconciled:false,
  entryPriceIndependentlyVerified:false,approvedRaasScore:false};
}
export function bridgeSummary(feed:ShareBridgeFeed,top:TopRetrospectiveFeed,bottom:RetrospectiveFeed){
 const cases=caseSnapshots(top,bottom);
 const bridges=cases.map(c=>bridgeForCase(feed,top,bottom,c.id));
 return {caseCount:cases.length,withSecShareCount:bridges.filter(Boolean).length,
  arithmeticMatches:bridges.filter(b=>b?.status==="ARITHMETIC_MATCH_REQUIRES_PRICE_AUDIT").length,
  missingShares:bridges.filter(b=>b===null).length,
  fullyVerifiedPriceCases:0,qualifiedRaasForecasts:0};
}
