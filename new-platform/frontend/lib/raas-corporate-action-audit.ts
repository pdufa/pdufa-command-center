/** Corporate-action research for historical price windows, not an exchange-action feed.
 * An empty list and a pre-window event do NOT certify the absence of
 * in-window events, split adjustment factors, distributions, or delistings.
 */
import type {TopRetrospectiveFeed} from "./raas-top-retrospective-intake";
import type {RetrospectiveFeed} from "./raas-retrospective-intake";
export type CorporateEvent={
 id:string;date:string;type:"SHARE_DISTRIBUTION"|"REVERSE_SPLIT"|"SPINOFF"|"CASH_MERGER";
 factorNumerator?:number;factorDenominator?:number;cashPerQuotedSecurityUsd?:number;
 sourceUrl:string;notes:string;
};
export type CorporateActionRecord={
 ticker:string;securityClass:"NASDAQ_COMMON"|"NASDAQ_ADS";adsOrdinaryShares?:number;
 events:CorporateEvent[];researchStatus:"PARTIAL_CORPORATE_ACTION_HISTORY";
};
export type CorporateActionFeed={
 schemaVersion:1;scope:"RAAS_HISTORICAL_CORPORATE_ACTION_RESEARCH";
 sourceAsOf:string;note:string;records:CorporateActionRecord[];
};
export type WindowEvent={event:CorporateEvent;placement:"BEFORE_WINDOW"|"DURING_WINDOW"|"AFTER_WINDOW"};
export type CorporateActionWindow={
 caseId:string;ticker:string;stage:"pre"|"post";
 securityClass:string|null;adsOrdinaryShares:number|null;
 listedEvents:WindowEvent[];eventsDuringWindow:number;
 knownBefore:number;knownAfter:number;
 researchStatus:"PARTIAL_HISTORY"|"NO_ACTION_SOURCE_IMPORTED";
 adjustedTotalReturnVerified:false;
 actionHistoryComplete:false;approvedRAAS:false;
 blockers:string[];
};
const date=(s:string):boolean=>/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 Number.isFinite(Date.parse(s+"T00:00:00Z"))&&new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const url=(s:string):boolean=>/^https:\/\/[^\s/]+\/\S+/.test(s);
const positive=(v:unknown):v is number=>typeof v==="number"&&Number.isFinite(v)&&v>0;
type EventWindow={id:string;ticker:string;stage:"pre"|"post";entry:string;exit:string};
const windows=(t:TopRetrospectiveFeed,b:RetrospectiveFeed):EventWindow[]=>[
 ...t.records.map(r=>({id:r.id,ticker:r.ticker,stage:"pre" as const,entry:r.entry.date,exit:r.exit.date})),
 ...b.records.map(r=>({id:r.id,ticker:r.ticker,stage:"post" as const,entry:r.entry.date,exit:r.exit.date}))
];
export function parseCorporateActions(input:unknown):CorporateActionFeed{
 if(!input||typeof input!=="object")throw Error("RAAS_ACTION_FEED_INVALID");
 const f=input as CorporateActionFeed;
 if(f.schemaVersion!==1||f.scope!=="RAAS_HISTORICAL_CORPORATE_ACTION_RESEARCH"||
 !date(f.sourceAsOf)||!Array.isArray(f.records)||f.records.length>1000)
 throw Error("RAAS_ACTION_FEED_INVALID");
 const companies=new Set<string>(),ids=new Set<string>();
 for(const r of f.records){
  if(!r||!r.ticker?.trim()||companies.has(r.ticker.toUpperCase())||
   !["NASDAQ_COMMON","NASDAQ_ADS"].includes(r.securityClass)||
   (r.securityClass==="NASDAQ_ADS"&&(!Number.isInteger(r.adsOrdinaryShares)||!(r.adsOrdinaryShares!>1)))||
   (r.securityClass==="NASDAQ_COMMON"&&r.adsOrdinaryShares!==undefined)||
   !Array.isArray(r.events)||!r.events.length||
   r.researchStatus!=="PARTIAL_CORPORATE_ACTION_HISTORY")
    throw Error("RAAS_ACTION_RECORD_INVALID");
  companies.add(r.ticker.toUpperCase());
  for(const e of r.events){
   if(!e?.id||ids.has(e.id)||!date(e.date)||e.date>f.sourceAsOf||
      !url(e.sourceUrl)||!e.notes?.trim()||
      !["SHARE_DISTRIBUTION","REVERSE_SPLIT","SPINOFF","CASH_MERGER"].includes(e.type))
      throw Error("RAAS_ACTION_EVENT_INVALID");
   ids.add(e.id);
   if((e.type==="REVERSE_SPLIT"||e.type==="SHARE_DISTRIBUTION")&&
      (!positive(e.factorNumerator)||!positive(e.factorDenominator)))
     throw Error("RAAS_ACTION_FACTOR_MISSING");
   if(e.type==="CASH_MERGER"&&!positive(e.cashPerQuotedSecurityUsd))
     throw Error("RAAS_ACTION_MERGER_CASH_INVALID");
  }
 }
 return f;
}
export function corporateActionsForCase(feed:CorporateActionFeed,t:TopRetrospectiveFeed,
 b:RetrospectiveFeed,id:string):CorporateActionWindow|null{
 const w=windows(t,b).find(x=>x.id===id);if(!w)return null;
 const r=feed.records.find(x=>x.ticker.toUpperCase()===w.ticker.toUpperCase());
 const listedEvents:WindowEvent[]=(r?.events??[]).map(event=>({
  event,placement:event.date<w.entry?"BEFORE_WINDOW" as const:
   event.date>w.exit?"AFTER_WINDOW" as const:"DURING_WINDOW" as const
 }));
 const before=listedEvents.filter(x=>x.placement==="BEFORE_WINDOW").length;
 const after=listedEvents.filter(x=>x.placement==="AFTER_WINDOW").length;
 const during=listedEvents.filter(x=>x.placement==="DURING_WINDOW").length;
 return {caseId:id,ticker:w.ticker,stage:w.stage,
  securityClass:r?.securityClass??null,adsOrdinaryShares:r?.adsOrdinaryShares??null,
  listedEvents,eventsDuringWindow:during.length,knownBefore:before,knownAfter:after,
  researchStatus:r?"PARTIAL_HISTORY":"NO_ACTION_SOURCE_IMPORTED",
  actionHistoryComplete:false,adjustedTotalReturnVerified:false,approvedRAAS:false,
  blockers:[
   ...(r?[]:["No issuer/exchange corporate-action source recorded for this ticker"]),
   ...(during.length?["A listed event falls during the observed price window"]:[]),
   "Complete dated exchange/transfer-agent split, dividend and distribution record missing",
   "Nominal vendor closes have no independently audited historical adjustment factors",
   "No executable price, full dilution or original pre-entry RAAS prediction verified"
  ]};
}
export function corporateActionSummary(feed:CorporateActionFeed,t:TopRetrospectiveFeed,b:RetrospectiveFeed){
 const rows=windows(t,b).map(w=>corporateActionsForCase(feed,t,b,w.id)!);
 return {cases:rows.length,withPartialActionHistory:rows.filter(r=>r.researchStatus==="PARTIAL_HISTORY").length,
  withoutActionHistory:rows.filter(r=>r.researchStatus==="NO_ACTION_SOURCE_IMPORTED").length,
  listedDuringWindow:rows.filter(r=>r.eventsDuringWindow>0).length,
  verifiedAdjustedReturns:0,approvedRAASPredictions:0};
}
