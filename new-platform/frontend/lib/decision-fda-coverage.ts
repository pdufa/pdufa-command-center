/** CRL coverage controls: missing public letters are never interpreted as FDA approval. */
export type FdaDecisionCoverage={status:"NOT_READY"|"REVIEW_REQUIRED";approvalRecords:number;crlRecords:number;unresolvedRecords:number;warnings:string[]};
export function assessFdaDecisionCoverage(approvalRecords:number,crlRecords:number,unresolvedRecords:number,sourceComplete=false):FdaDecisionCoverage{
 const counts=[approvalRecords,crlRecords,unresolvedRecords];
 const valid=counts.every(n=>Number.isSafeInteger(n)&&n>=0);
 const warnings:string[]=[];
 if(!valid)warnings.push("Invalid historical record counts");
 if(!sourceComplete)warnings.push("Public FDA CRL disclosures are incomplete; missing letters do not establish approval");
 if(unresolvedRecords>0)warnings.push("Unresolved review-cycle outcomes must not be classified as approvals or failures");
 if(crlRecords===0)warnings.push("No documented nonapproval cases: approval-only sample risks selection bias");
 if(approvalRecords+crlRecords===0)warnings.push("No classified historical decision records");
 return {status:valid&&sourceComplete&&unresolvedRecords===0&&crlRecords>0&&approvalRecords+crlRecords>0?"REVIEW_REQUIRED":"NOT_READY",approvalRecords,crlRecords,unresolvedRecords,warnings};
}
