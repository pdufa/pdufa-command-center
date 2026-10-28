/** Historical FDA outcome coverage audit. Never infer that missing CRLs mean approval. */
export type HistoricalCoverageInput={asOf:string;windowStart:string;windowEnd:string;eligibleApplications:number;reviewedDecisions:number;approved:number;crl:number;withdrawn:number;unresolved:number;sourceCoverageConfirmed:boolean;includesNonApprovals:boolean};
export type HistoricalCoverageAudit={status:"NOT_READY"|"READY_FOR_INDEPENDENT_REVIEW";coveragePct:number|null;issues:string[]};
export function auditHistoricalOutcomeCoverage(input:HistoricalCoverageInput):HistoricalCoverageAudit{
 const issues:string[]=[];const start=Date.parse(input.windowStart),end=Date.parse(input.windowEnd),cutoff=Date.parse(input.asOf);
 if(![start,end,cutoff].every(Number.isFinite)||start>=end||end>=cutoff)issues.push("Invalid historical observation window or lookahead");
 const nums=[input.eligibleApplications,input.reviewedDecisions,input.approved,input.crl,input.withdrawn,input.unresolved];
 if(nums.some(n=>!Number.isSafeInteger(n)||n<0))issues.push("Historical counts must be nonnegative integers");
 if(input.eligibleApplications===0||input.reviewedDecisions>input.eligibleApplications)issues.push("Historical denominator missing or inconsistent");
 if(input.approved+input.crl+input.withdrawn!==input.reviewedDecisions)issues.push("Reviewed outcomes do not reconcile");
 if(input.reviewedDecisions+input.unresolved!==input.eligibleApplications)issues.push("Unresolved applications not reconciled");
 if(!input.sourceCoverageConfirmed||!input.includesNonApprovals)issues.push("Nonapproval source coverage or denominator not independently established");
 if(input.unresolved>0)issues.push("Unresolved outcomes prevent complete historical rate");
 const coveragePct=input.eligibleApplications>0&&nums.every(n=>Number.isSafeInteger(n)&&n>=0)?100*input.reviewedDecisions/input.eligibleApplications:null;
 return {status:issues.length?"NOT_READY":"READY_FOR_INDEPENDENT_REVIEW",coveragePct,issues};
}
