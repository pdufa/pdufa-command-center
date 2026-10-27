/** Point-in-time price observations for historical research, never a live trading signal. */
export type HistoricalPrice={programId:string;observedAt:string;close:number;source:string;capturedAt:string};
export type HistoricalTradeWindow={programId:string;entryAt:string;exitAt:string;entryClose:number;exitClose:number;roundTripCostPct:number;netReturnPct:number};
export type PriceWindowResult={status:"NOT_READY"|"RESEARCH_ONLY";issues:string[];window:HistoricalTradeWindow|null};
const validUrl=(s:string)=>{try{return new URL(s).protocol==="https:";}catch{return false;}};
/** Uses only two explicitly timestamped observations; no nearest-date forward filling. */
export function evaluateHistoricalPriceWindow(entry:HistoricalPrice,exit:HistoricalPrice,costPct:number):PriceWindowResult{
 const issues:string[]=[];const e=Date.parse(entry.observedAt),x=Date.parse(exit.observedAt),ec=Date.parse(entry.capturedAt),xc=Date.parse(exit.capturedAt);
 if(!/^PDUFA-\d{6,}$/.test(entry.programId)||entry.programId!==exit.programId)issues.push("Mismatched program identity");
 if(![e,x,ec,xc].every(Number.isFinite)||e>=x||ec<e||xc<x)issues.push("Invalid observation or capture chronology");
 if(!validUrl(entry.source)||!validUrl(exit.source))issues.push("Source reference missing");
 if(!Number.isFinite(entry.close)||entry.close<=0||!Number.isFinite(exit.close)||exit.close<=0)issues.push("Invalid prices");
 if(!Number.isFinite(costPct)||costPct<0||costPct>=100)issues.push("Invalid trading costs");
 if(issues.length)return {status:"NOT_READY",issues,window:null};
 const netReturnPct=(exit.close/entry.close-1)*100-costPct;
 return {status:"RESEARCH_ONLY",issues:["Source URLs and timestamps require independent verification; adjusted prices and corporate actions not yet verified"],window:{programId:entry.programId,entryAt:entry.observedAt,exitAt:exit.observedAt,entryClose:entry.close,exitClose:exit.close,roundTripCostPct:costPct,netReturnPct}};
}
