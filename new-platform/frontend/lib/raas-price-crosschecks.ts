/** Historical daily-close cross-provider reconciliation.
 * A matching quote is evidence for the nominal close, NOT proof of adjusted
 * total return, security class, split/ADR factors, or predictive validity.
 */
import type {TopRetrospectiveFeed} from "./raas-top-retrospective-intake";
import type {RetrospectiveFeed} from "./raas-retrospective-intake";
export type PriceSide="ENTRY"|"EXIT";
export type Crosscheck={
 caseId:string;side:PriceSide;date:string;secondaryClose:number;currency:"USD";
 secondaryProvider:string;sourceUrl:string;
 quoteGranularity:"DAILY_SESSION_CLOSE"|"WEEKLY_FRIDAY_CLOSE";
 sourceQuoteBasis:"NOMINAL_DAILY_CLOSE_ADJUSTMENTS_UNCONFIRMED";
 sourceDisplayDate:string;sourceFirstPublishedAt?:string;note:string;
};
export type PriceCrosscheckFeed={
 schemaVersion:1;scope:"RAAS_HISTORICAL_SECOND_PROVIDER_CLOSE_CHECKS";
 sourceAsOf:string;note:string;observations:Crosscheck[];
};
export type PriceCheckResult={
 side:PriceSide;date:string;originalClose:number;
 secondaryClose:number|null;secondaryProvider:string|null;
 quoteGranularity:"DAILY_SESSION_CLOSE"|"WEEKLY_FRIDAY_CLOSE"|null;
 originalUrl:string;secondaryUrl:string|null;
 sourceFirstPublishedAt:string|null;postExitDisclosure:boolean;
 differenceUsd:number|null;differencePercent:number|null;
 status:"PROVIDER_PRICE_MATCH"|"PROVIDER_PRICE_MISMATCH"|"SECOND_SOURCE_MISSING";
};
export type WindowPriceAudit={
 caseId:string;ticker:string;stage:"pre"|"post";
 entry:PriceCheckResult;exit:PriceCheckResult;
 secondProviderPoints:0|1|2;bothClosesAgree:boolean;
 adjustmentStatus:"CORPORATE_ACTION_RECONCILIATION_PENDING";
 vendorPricesIndependentlyAudited:false;
 eligibleForValidatedRAAS:false;blockingIssues:string[];
};
const validDate=(s:string):boolean=>/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 Number.isFinite(Date.parse(s+"T00:00:00Z"))&&new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const url=(s:string):boolean=>/^https:\/\/[^\s/]+\/\S+/.test(s);
type CaseInput={id:string;ticker:string;stage:"pre"|"post";
 entry:{date:string;close:number;sourceUrl:string};exit:{date:string;close:number;sourceUrl:string}};
const cases=(top:TopRetrospectiveFeed,bottom:RetrospectiveFeed):CaseInput[]=>[
 ...top.records.map(r=>({id:r.id,ticker:r.ticker,stage:"pre" as const,entry:r.entry,exit:r.exit})),
 ...bottom.records.map(r=>({id:r.id,ticker:r.ticker,stage:"post" as const,entry:r.entry,exit:r.exit}))
];
export function parsePriceCrosschecks(input:unknown,top:TopRetrospectiveFeed,bottom:RetrospectiveFeed):PriceCrosscheckFeed{
 if(!input||typeof input!=="object")throw Error("RAAS_PRICE_CHECK_FEED_INVALID");
 const feed=input as PriceCrosscheckFeed;
 if(feed.schemaVersion!==1||feed.scope!=="RAAS_HISTORICAL_SECOND_PROVIDER_CLOSE_CHECKS"||
   !validDate(feed.sourceAsOf)||!Array.isArray(feed.observations)||
   feed.observations.length>20000)throw Error("RAAS_PRICE_CHECK_FEED_INVALID");
 const byId=new Map(cases(top,bottom).map(r=>[r.id,r] as const));
 const seen=new Set<string>();
 for(const r of feed.observations){
  const c=byId.get(r?.caseId);
  if(!c||!["ENTRY","EXIT"].includes(r.side)||!validDate(r.date)||
    !Number.isFinite(r.secondaryClose)||r.secondaryClose<=0||
    !r.secondaryProvider?.trim()||!url(r.sourceUrl)||!r.note?.trim()||
    !validDate(r.sourceDisplayDate)||r.sourceDisplayDate>feed.sourceAsOf||
    (r.sourceFirstPublishedAt!==undefined&&(!validDate(r.sourceFirstPublishedAt)||r.sourceFirstPublishedAt>feed.sourceAsOf))||
    !["DAILY_SESSION_CLOSE","WEEKLY_FRIDAY_CLOSE"].includes(r.quoteGranularity)||
    r.currency!=="USD"||
    r.sourceQuoteBasis!=="NOMINAL_DAILY_CLOSE_ADJUSTMENTS_UNCONFIRMED")
    throw Error("RAAS_PRICE_CHECK_OBSERVATION_INVALID");
  const baseline=r.side==="ENTRY"?c.entry:c.exit;
  if(r.date!==baseline.date||r.sourceUrl===baseline.sourceUrl)
   throw Error("RAAS_PRICE_CHECK_NOT_INDEPENDENT_DATE_OR_SOURCE");
  if(r.quoteGranularity==="WEEKLY_FRIDAY_CLOSE"&&new Date(r.date+"T00:00:00Z").getUTCDay()!==5)
   throw Error("RAAS_PRICE_CHECK_WEEKLY_NOT_FRIDAY");

  const k=r.caseId+"|"+r.side+"|"+r.secondaryProvider.toLowerCase().trim();
  if(seen.has(k))throw Error("RAAS_PRICE_CHECK_DUPLICATE");
  seen.add(k);
 }
 return feed;
}
export function priceAuditForCase(feed:PriceCrosscheckFeed,top:TopRetrospectiveFeed,
 bottom:RetrospectiveFeed,id:string):WindowPriceAudit|null{
 const original=cases(top,bottom).find(r=>r.id===id);
 if(!original)return null;
 const get=(side:PriceSide):PriceCheckResult=>{
  const baseline=side==="ENTRY"?original.entry:original.exit;
  const secondaries=feed.observations.filter(x=>x.caseId===id&&x.side===side);
  if(!secondaries.length)return {side,date:baseline.date,originalClose:baseline.close,
   secondaryClose:null,secondaryProvider:null,quoteGranularity:null,originalUrl:baseline.sourceUrl,
   secondaryUrl:null,sourceFirstPublishedAt:null,postExitDisclosure:false,
   differenceUsd:null,differencePercent:null,status:"SECOND_SOURCE_MISSING"};
  // Different secondary providers with conflicting prices do not silently
  // validate an existing vendor number.
  const primary=secondaries[0],difference=primary.secondaryClose-baseline.close;
  const inconsistent=secondaries.some(x=>Math.abs(x.secondaryClose-primary.secondaryClose)>.005);
  const delta=Math.abs(difference);
  const matches=delta<=.005&&!inconsistent;
  return {side,date:baseline.date,originalClose:baseline.close,
   secondaryClose:primary.secondaryClose,secondaryProvider:primary.secondaryProvider,
   quoteGranularity:primary.quoteGranularity,
   originalUrl:baseline.sourceUrl,secondaryUrl:primary.sourceUrl,
   sourceFirstPublishedAt:primary.sourceFirstPublishedAt??null,
   postExitDisclosure:primary.sourceFirstPublishedAt!==undefined&&primary.sourceFirstPublishedAt>original.exit.date,
   differenceUsd:Math.round(difference*10000)/10000,
   differencePercent:Math.round(difference/baseline.close*10000)/100,
   status:matches?"PROVIDER_PRICE_MATCH":"PROVIDER_PRICE_MISMATCH"};
 };
 const entry=get("ENTRY"),exit=get("EXIT");
 const count=(entry.status!=="SECOND_SOURCE_MISSING"?1:0)+(exit.status!=="SECOND_SOURCE_MISSING"?1:0);
 const blockers=[
  ...(entry.status==="SECOND_SOURCE_MISSING"?["Entry-date second provider not checked"]:[]),
  ...(exit.status==="SECOND_SOURCE_MISSING"?["Exit-date second provider not checked"]:[]),
  ...(entry.status==="PROVIDER_PRICE_MISMATCH"||exit.status==="PROVIDER_PRICE_MISMATCH"?["Cross-provider closing-price mismatch requires investigation"]:[]),
  "Corporate actions, dividends, ADR/security class and adjustment factors unverified",
  "Realistic execution and round-trip slippage not observed",
  "No contemporaneous recorded historical RAAS prediction"
 ];
 return {caseId:id,ticker:original.ticker,stage:original.stage,entry,exit,
  secondProviderPoints:count as 0|1|2,
  bothClosesAgree:entry.status==="PROVIDER_PRICE_MATCH"&&exit.status==="PROVIDER_PRICE_MATCH",
  adjustmentStatus:"CORPORATE_ACTION_RECONCILIATION_PENDING",
  vendorPricesIndependentlyAudited:false,eligibleForValidatedRAAS:false,blockingIssues:blockers};
}
export function priceAuditSummary(feed:PriceCrosscheckFeed,top:TopRetrospectiveFeed,bottom:RetrospectiveFeed){
 const results=cases(top,bottom).map(c=>priceAuditForCase(feed,top,bottom,c.id)!);
 return {caseCount:results.length,quotedPoints:results.length*2,
  secondaryPointsRecorded:results.reduce((s,r)=>s+r.secondProviderPoints,0),
  matchedPoints:results.flatMap(r=>[r.entry,r.exit]).filter(x=>x.status==="PROVIDER_PRICE_MATCH").length,
  mismatchedPoints:results.flatMap(r=>[r.entry,r.exit]).filter(x=>x.status==="PROVIDER_PRICE_MISMATCH").length,
  bothClosesMatchedCases:results.filter(x=>x.bothClosesAgree).length,
  adjustedTotalReturnsVerified:0,qualifiedHistoricalPredictions:0};
}
