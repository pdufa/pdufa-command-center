/** Reject source metadata that claims a document was knowable before publication. */
export type HistoricalSourceRecord={sourceUrl:string;publishedAt:string;observedAt:string;decisionAt:string;predictionCutoff:string;independentlyReviewed:boolean};
export type HistoricalSourceAudit={status:"NOT_READY"|"READY_FOR_INDEPENDENT_REVIEW";issues:string[]};
export function auditHistoricalSourceChronology(row:HistoricalSourceRecord):HistoricalSourceAudit{
 const issues:string[]=[];const published=Date.parse(row.publishedAt),observed=Date.parse(row.observedAt),decision=Date.parse(row.decisionAt),cutoff=Date.parse(row.predictionCutoff);
 if(![published,observed,decision,cutoff].every(Number.isFinite))issues.push("All source and decision timestamps are required");
 else {if(decision>=cutoff)issues.push("Historical decision occurred after prediction cutoff");if(published<decision)issues.push("Source publication precedes recorded decision");if(observed<published)issues.push("Source observed before publication");if(observed>=cutoff||published>=cutoff)issues.push("Source was not available at prediction cutoff");}
 let urlOk=false;try{const u=new URL(row.sourceUrl);urlOk=u.protocol==="https:"&&Boolean(u.hostname)&&!u.username&&!u.password;}catch{}
 if(!urlOk)issues.push("HTTPS source URL required");
 if(row.independentlyReviewed!==true)issues.push("Independent source review required");
 return {status:issues.length?"NOT_READY":"READY_FOR_INDEPENDENT_REVIEW",issues};
}
