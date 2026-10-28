import type {FdaApplicationEvidence,FdaSubmissionEvidence} from "./decision-openfda-normalizer";
import {auditHistoricalSourceChronology,type HistoricalSourceRecord} from "./decision-historical-source-chronology";
/** Audit historical FDA review cycles without treating approval after a CRL as an original approval. */
export type FdaReviewCycle={applicationNumber:string;indication:string;decisionDate:string;decision:"APPROVED"|"CRL"|"WITHDRAWN";sourceUrl:string;reviewed:boolean};
export type CycleAudit={status:"NOT_READY"|"READY_FOR_REVIEW";cycles:FdaReviewCycle[];issues:string[]};
export function auditFdaReviewCycles(cycles:FdaReviewCycle[],cutoff:string):CycleAudit{
 const issues:string[]=[];const until=Date.parse(cutoff);const seen=new Set<string>();
 if(!Number.isFinite(until))issues.push("Invalid historical prediction cutoff");
 if(!cycles.length)issues.push("No historical review cycles");
 for(const [i,c] of cycles.entries()){
  const date=Date.parse(c.decisionDate),key=[c.applicationNumber.toUpperCase(),c.indication.trim().toLowerCase(),c.decisionDate].join("|");
  if(!/^(NDA|BLA)\d{6}$/i.test(c.applicationNumber)||!c.indication.trim())issues.push("Row "+i+": application or indication missing");
  if(!Number.isFinite(date)||date>=until)issues.push("Row "+i+": decision not before prediction cutoff");
  if(seen.has(key))issues.push("Row "+i+": duplicate application-indication-decision cycle");
  seen.add(key);
  let sourceOk=false;try{const u=new URL(c.sourceUrl);sourceOk=u.protocol==="https:"&&/(^|\.)fda\.gov$/.test(u.hostname)&&!u.username&&!u.password;}catch{}
  if(!sourceOk||c.reviewed!==true)issues.push("Row "+i+": original FDA source requires independent review");
  if(!["APPROVED","CRL","WITHDRAWN"].includes(c.decision))issues.push("Row "+i+": unsupported outcome");
 }
 return {status:issues.length?"NOT_READY":"READY_FOR_REVIEW",cycles,issues};
}

/** A manual classification must identify the exact submission and its original letter. */
export type ClassifiedFdaReviewCycle=FdaReviewCycle&{
 submissionType:string;submissionNumber:string;sourceChronology:HistoricalSourceRecord;
};
export type FdaReviewCycleLedgerEntry={
 applicationNumber:string;submissionType:string;submissionNumber:string;submissionStatus:string;
 statusDate:string|null;decision:FdaReviewCycle["decision"]|null;sourceUrl:string|null;
 missingData:string[];
};
export type FdaReviewCycleLedger={status:"NOT_READY"|"READY_FOR_REVIEW";entries:FdaReviewCycleLedgerEntry[];issues:string[];warnings:string[]};
/** Join public submission metadata to manual, cutoff-safe review evidence. The ledger cannot
 * establish that public data contains every CRL, withdrawal, indication, or review cycle. */
export function buildFdaReviewCycleLedger(application:FdaApplicationEvidence,classifications:ClassifiedFdaReviewCycle[],cutoff:string):FdaReviewCycleLedger{
 const issues:string[]=[];
 const until=Date.parse(cutoff);
 if(!Number.isFinite(until))issues.push("Invalid ledger observation cutoff");
 if(!application.submissions.length)issues.push("FDA submission history missing");
 const key=(row:{submissionType:string;submissionNumber:string})=>row.submissionType.toUpperCase()+"|"+row.submissionNumber;
 const seen=new Set<string>();
 const entries=application.submissions.map((submission:FdaSubmissionEvidence)=>{
  const missingData:string[]=[];
  const submissionKey=key(submission);
  if(!submission.submissionType||!submission.submissionNumber)missingData.push("Exact submission identity missing");
  if(submission.applicationNumber.toUpperCase()!==application.applicationNumber.toUpperCase())missingData.push("Submission/application identity mismatch");
  if(seen.has(submissionKey))missingData.push("Duplicate submission identity");
  seen.add(submissionKey);
  if(!submission.statusDate)missingData.push("Submission status date missing");
  else{
   const iso=submission.statusDate.slice(0,4)+"-"+submission.statusDate.slice(4,6)+"-"+submission.statusDate.slice(6,8);
   const parsed=Date.parse(iso);
   if(!/^\d{8}$/.test(submission.statusDate)||!Number.isFinite(parsed)||new Date(parsed).toISOString().slice(0,10)!==iso)missingData.push("Invalid submission status date");
   else if(parsed>=until)missingData.push("Submission metadata not before observation cutoff");
  }
  const matches=classifications.filter(row=>key(row)===submissionKey&&row.applicationNumber.toUpperCase()===application.applicationNumber.toUpperCase());
  let decision:FdaReviewCycle["decision"]|null=null,sourceUrl:string|null=null;
  if(matches.length!==1)missingData.push(matches.length?"Conflicting manual review-cycle classifications":"Manual indication/outcome classification missing");
  else{
   const row=matches[0];
   if(submission.statusDate&&row.decisionDate.slice(0,10).replace(/-/g,"")!==submission.statusDate)missingData.push("Submission status date differs from classified decision date");
   const cycleAudit=auditFdaReviewCycles([row],cutoff);
   missingData.push(...cycleAudit.issues);
   const chronology=auditHistoricalSourceChronology(row.sourceChronology);
   missingData.push(...chronology.issues);
   if(row.sourceChronology.sourceUrl!==row.sourceUrl||Date.parse(row.sourceChronology.decisionAt)!==Date.parse(row.decisionDate)||Date.parse(row.sourceChronology.predictionCutoff)!==until)missingData.push("Source chronology does not match classified review cycle and cutoff");
   if(!submission.documents.some(document=>document.url===row.sourceUrl))missingData.push("Original decision letter not linked to this submission");
   if(!missingData.length){decision=row.decision;sourceUrl=row.sourceUrl;}
  }
  issues.push(...missingData.map(issue=>submissionKey+": "+issue));
  return {applicationNumber:application.applicationNumber,submissionType:submission.submissionType,submissionNumber:submission.submissionNumber,submissionStatus:submission.status,statusDate:submission.statusDate,decision,sourceUrl,missingData};
 });
 for(const row of classifications){
  if(row.applicationNumber.toUpperCase()!==application.applicationNumber.toUpperCase()||!seen.has(key(row)))issues.push("Classified review cycle has no matching application/submission metadata");
 }
 return {status:issues.length?"NOT_READY":"READY_FOR_REVIEW",entries,issues,warnings:["Public approval-focused metadata may omit CRLs, withdrawals, and earlier review cycles; this ledger does not establish a complete historical denominator.","Manual review flags and source URLs require independent verification; submission status alone never classifies an outcome."]};
}
