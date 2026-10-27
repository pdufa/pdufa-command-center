/** Cross-source evidence reconciliation: FDA submission status cannot silently override CRL evidence. */
import type {FdaApplicationEvidence} from "./decision-openfda-normalizer";
import type {CrlEvidenceReview} from "./decision-crl-evidence";
export type ReconciledFdaEvidence={status:"NOT_READY"|"READY_FOR_MANUAL_RECONCILIATION";applicationNumber:string;crlReviewCycles:number;submissionCount:number;issues:string[]};
export function reconcileFdaEvidence(application:FdaApplicationEvidence|null,crls:CrlEvidenceReview[]):ReconciledFdaEvidence{
 const issues:string[]=[];
 if(!application)issues.push("Drugs@FDA application record missing");
 const applicationNumber=application?.applicationNumber||"";
 if(!/^(NDA|BLA)\d{6}$/i.test(applicationNumber))issues.push("Exact NDA/BLA identity required");
 if(!application?.submissions.length)issues.push("No application submission history available");
 if(!crls.length)issues.push("CRL source coverage not established; absence of a CRL is not proof of approval");
 for(const crl of crls){
  if(crl.applicationNumber.toUpperCase()!==applicationNumber.toUpperCase())issues.push("FDA/CRL application identity mismatch");
  if(crl.status!=="READY_FOR_INDEPENDENT_REVIEW"||crl.decision!=="NONAPPROVAL_THIS_REVIEW_CYCLE")issues.push("CRL evidence requires independent review");
 }
 issues.push("Indication, submission sequence, decision date, and original letters require manual reconciliation");
 return {status:issues.some(x=>!x.startsWith("Indication,"))?"NOT_READY":"READY_FOR_MANUAL_RECONCILIATION",applicationNumber,crlReviewCycles:crls.length,submissionCount:application?.submissions.length||0,issues};
}
