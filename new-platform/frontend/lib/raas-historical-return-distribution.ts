/** Descriptive historical RAAS research sample with arithmetic and sensitivity.
 * Not a market-timing backtest: windows were selected *after* outcomes, prices
 * have unverified corporate-action adjustment, no archived predictions exist.
 */
import type {TopRetrospectiveFeed} from "./raas-top-retrospective-intake";
import type {RetrospectiveFeed} from "./raas-retrospective-intake";
import type {PriceCrosscheckFeed} from "./raas-price-crosschecks";
import {priceAuditForCase} from "./raas-price-crosschecks";
type Stage="pre"|"post";
export type HistoricalWindowAnalysis={
 id:string;ticker:string;stage:Stage;entryDate:string;exitDate:string;
 eventDate:string;holdingCalendarDays:number;daysEntryToScheduledEvent:number;
 daysExitToScheduledEvent:number;daysExitToActualOutcome:number|null;
 grossReturnPercent:number;
 secondSourceEntryMatched:boolean;secondSourceExitMatched:boolean;
 adjustedTotalReturnVerified:false;historicalPredictionRecorded:false;
};
export type HistoricalStageDistribution={
 stage:Stage;count:number;uniqueIssuers:number;winCount:number;
 positiveAfterOnePercentCostCount:number;meanGrossPercent:number;medianGrossPercent:number;
 meanAfterOnePercentCost:number;medianAfterOnePercentCost:number;
 minimumGrossPercent:number;maximumGrossPercent:number;
 leaveOneOutMeanRange:{min:number;max:number}|null;
 bothClosesSecondSourceMatched:number;
};
export type HistoricalReturnDescriptiveReport={
 windows:HistoricalWindowAnalysis[];
 top:HistoricalStageDistribution;bottom:HistoricalStageDistribution;
 totalUniqueIssuers:number;yearRange:string;
 nominalSecondSourcePointsMatched:number;nominalPricePoints:number;
 adjustedTotalReturnVerified:0;originalRaasPredictions:0;eligibleCalibrations:0;
 costAssumptionRoundTripPercent:1;
 caveats:string[];
};
const day=(s:string)=>Date.parse(s+"T00:00:00Z");
const differenceDays=(a:string,b:string)=>Math.round((day(b)-day(a))/86400000);
const round=(x:number)=>Math.round((x+Number.EPSILON)*100)/100;
const median=(s:number[])=>{
 if(!s.length)return 0;
 const x=[...s].sort((a,b)=>a-b),n=x.length;
 return n%2?x[Math.floor(n/2)]:(x[n/2-1]+x[n/2])/2;
};
function describe(rows:HistoricalWindowAnalysis[],stage:Stage):HistoricalStageDistribution{
 const a=rows.filter(r=>r.stage===stage);
 if(!a.length)throw Error("RAAS_DISTRIBUTION_NO_SAMPLES");
 const v=a.map(x=>x.grossReturnPercent);
 const meansExcluded=v.length>1?v.map((_,i)=>v.reduce((sum,x,j)=>sum+(i===j?0:x),0)/(v.length-1)):[];
 return {stage,count:a.length,uniqueIssuers:new Set(a.map(x=>x.ticker)).size,
  winCount:v.filter(x=>x>0).length,
  positiveAfterOnePercentCostCount:v.filter(x=>x>1).length,
  meanGrossPercent:round(v.reduce((s,x)=>s+x,0)/v.length),
  medianGrossPercent:round(median(v)),
  meanAfterOnePercentCost:round(v.reduce((s,x)=>s+x,0)/v.length-1),
  medianAfterOnePercentCost:round(median(v)-1),
  minimumGrossPercent:round(Math.min(...v)),maximumGrossPercent:round(Math.max(...v)),
  leaveOneOutMeanRange:meansExcluded.length?
   {min:round(Math.min(...meansExcluded)),max:round(Math.max(...meansExcluded))}:null,
  bothClosesSecondSourceMatched:a.filter(x=>x.secondSourceEntryMatched&&x.secondSourceExitMatched).length
 };
}
export function analyzeRaasHistoricalReturns(
 top:TopRetrospectiveFeed,post:RetrospectiveFeed,checks:PriceCrosscheckFeed
):HistoricalReturnDescriptiveReport{
 const rows=[
  ...top.records.map(r=>({id:r.id,ticker:r.ticker,stage:"pre" as const,
   entry:r.entry,exit:r.exit,eventDate:r.publicReadoutDate,actualDate:null as string|null})),
  ...post.records.map(r=>({id:r.id,ticker:r.ticker,stage:"post" as const,
   entry:r.entry,exit:r.exit,eventDate:r.pdufaDate,actualDate:r.realizedFDAAction.date}))
 ];
 const seen=new Set<string>();
 const windows:HistoricalWindowAnalysis[]=rows.map(r=>{
  if(seen.has(r.id)||r.entry.date>=r.exit.date||r.exit.date>=r.eventDate||
   !(r.entry.close>0&&r.exit.close>0))
   throw Error("RAAS_DISTRIBUTION_WINDOW_INVALID");
  seen.add(r.id);
  const audit=priceAuditForCase(checks,top,post,r.id);
  if(!audit)throw Error("RAAS_DISTRIBUTION_PRICE_AUDIT_MISSING");
  return {id:r.id,ticker:r.ticker,stage:r.stage,
   entryDate:r.entry.date,exitDate:r.exit.date,eventDate:r.eventDate,
   holdingCalendarDays:differenceDays(r.entry.date,r.exit.date),
   daysEntryToScheduledEvent:differenceDays(r.entry.date,r.eventDate),
   daysExitToScheduledEvent:differenceDays(r.exit.date,r.eventDate),
   daysExitToActualOutcome:r.actualDate?differenceDays(r.exit.date,r.actualDate):null,
   grossReturnPercent:round((r.exit.close/r.entry.close-1)*100),
   secondSourceEntryMatched:audit.entry.status==="PROVIDER_PRICE_MATCH",
   secondSourceExitMatched:audit.exit.status==="PROVIDER_PRICE_MATCH",
   adjustedTotalReturnVerified:false,historicalPredictionRecorded:false};
 });
 const years=windows.flatMap(r=>[r.entryDate.slice(0,4),r.exitDate.slice(0,4)]).sort();
 return {windows,top:describe(windows,"pre"),bottom:describe(windows,"post"),
  totalUniqueIssuers:new Set(windows.map(x=>x.ticker)).size,
  yearRange:years[0]+"–"+years[years.length-1],
  nominalSecondSourcePointsMatched:windows.reduce((s,x)=>s+
   Number(x.secondSourceEntryMatched)+Number(x.secondSourceExitMatched),0),
  nominalPricePoints:windows.length*2,adjustedTotalReturnVerified:0,
  originalRaasPredictions:0,eligibleCalibrations:0,
  costAssumptionRoundTripPercent:1,
  caveats:[
   "All entry and exit windows were selected retrospectively; there are no archived RAAS ratings or actual trades.",
   "The 1% round-trip trading cost is a sensitivity assumption, not observed broker execution, spread or slippage.",
   "Price sources report nominal closes. Stock splits, dividends, ADR/security classes and corporate actions are not independently reconciled.",
   "No mean or median here estimates the best 90-to-3-day window, a ten-year return, FDA approval probability or predictive RAAS accuracy.",
   "The same issuer may appear in TOP and BOTTOM in different years; cross-stage records are not independent issuers."
  ]};
}
