import {auditHistoricalMarketPair,type HistoricalMarketRecord} from "./decision-market-audit";
import {evaluateHistoricalPriceWindow,type PriceWindowResult} from "./decision-historical-prices";
/** A market return cannot be computed until both observations pass the adjusted-price audit. */
export function evaluateAuditedMarketWindow(entry:HistoricalMarketRecord,exit:HistoricalMarketRecord,costPct:number):PriceWindowResult{
 const audit=auditHistoricalMarketPair(entry,exit);
 if(audit.status!=="READY_FOR_RESEARCH")return {status:"NOT_READY",issues:audit.issues,window:null};
 const mapped=(r:HistoricalMarketRecord)=>({programId:r.programId,observedAt:r.observedAt,capturedAt:r.capturedAt,close:r.adjustedClose,source:r.priceSource});
 const result=evaluateHistoricalPriceWindow(mapped(entry),mapped(exit),costPct);
 if(result.status!=="RESEARCH_ONLY")return result;
 return {...result,issues:[...result.issues,"Metadata does not independently prove adjusted-price integrity or reviewer identity"]};
}
