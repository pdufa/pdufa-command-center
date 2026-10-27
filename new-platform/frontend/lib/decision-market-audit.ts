/** Strict source manifest for historical stock prices; prevents unadjusted series from being used in backtests. */
export type HistoricalMarketRecord={programId:string;ticker:string;observedAt:string;capturedAt:string;adjustedClose:number;currency:string;priceSource:string;adjustmentMethod:"SPLIT_AND_DIVIDEND_ADJUSTED"|"SPLIT_ADJUSTED"|"RAW";corporateActionsReviewed:boolean;verifiedBy:string};
export type HistoricalMarketAudit={status:"NOT_READY"|"READY_FOR_RESEARCH";issues:string[]};
export function auditHistoricalMarketPair(entry:HistoricalMarketRecord,exit:HistoricalMarketRecord):HistoricalMarketAudit{
 const issues:string[]=[];
 const valid=(s:string)=>{try{const u=new URL(s);return u.protocol==="https:"&&Boolean(u.hostname);}catch{return false;}};
 if(!/^PDUFA-\d{6,}$/.test(entry.programId)||entry.programId!==exit.programId)issues.push("Program identity mismatch");
 if(!/^[A-Z][A-Z0-9.\-]{0,9}$/.test(entry.ticker)||entry.ticker!==exit.ticker)issues.push("Ticker identity mismatch");
 if(entry.currency!=="USD"||exit.currency!=="USD")issues.push("Currency conversion not supported");
 for(const [i,r] of [entry,exit].entries()){
  if(!Number.isFinite(r.adjustedClose)||r.adjustedClose<=0)issues.push("Invalid adjusted price at "+i);
  if(!valid(r.priceSource))issues.push("Missing HTTPS market source at "+i);
  if(r.adjustmentMethod!=="SPLIT_AND_DIVIDEND_ADJUSTED"||!r.corporateActionsReviewed||!r.verifiedBy.trim())issues.push("Corporate actions or independent review incomplete at "+i);
  const observed=Date.parse(r.observedAt),captured=Date.parse(r.capturedAt);
  if(!Number.isFinite(observed)||!Number.isFinite(captured)||captured<observed)issues.push("Invalid observation capture chronology at "+i);
 }
 if(Date.parse(entry.observedAt)>=Date.parse(exit.observedAt))issues.push("Exit must follow entry");
 return {status:issues.length?"NOT_READY":"READY_FOR_RESEARCH",issues};
}
