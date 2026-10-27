/** Normalize public Drugs@FDA submission metadata without inferring a PDUFA outcome. */
export type OpenFdaSubmission={submission_type?:string;submission_number?:string;submission_status?:string;submission_status_date?:string;submission_class_code_description?:string;application_docs?:{application_docs_url?:string;applications_doc_title?:string}[]};
export type OpenFdaApplication={application_number?:string;sponsor_name?:string;submissions?:OpenFdaSubmission[]};
export type FdaSubmissionEvidence={applicationNumber:string;submissionType:string;submissionNumber:string;status:string;statusDate:string|null;documents:{title:string;url:string}[];requiresManualOutcomeClassification:true};
export type FdaApplicationEvidence={applicationNumber:string;sponsor:string;submissions:FdaSubmissionEvidence[];warnings:string[]};
/** All submissions are retained: an APPROVAL status alone cannot establish the exact indication or PDUFA outcome. */
export function normalizeDrugsFdaApplication(input:OpenFdaApplication):FdaApplicationEvidence{
 const applicationNumber=(input.application_number||"").trim();
 if(!/^(NDA|BLA|ANDA)\d{6}$/i.test(applicationNumber))throw new Error("Missing or invalid FDA application number");
 const warnings=["FDA application submissions are not equivalent to indication-specific PDUFA decisions.","CRLs and withdrawn applications may be absent or incomplete in public approval-focused datasets.","Confirm original FDA letters, submission chronology, indication, and trial evidence before classifying outcomes."];
 const submissions=(input.submissions||[]).map(s=>{
  const date=s.submission_status_date||"";
  const validDate=/^\d{8}$/.test(date)&&Number.isFinite(Date.parse(date.slice(0,4)+"-"+date.slice(4,6)+"-"+date.slice(6,8)));
  const documents=(s.application_docs||[]).filter(d=>{try{const u=new URL(d.application_docs_url||"");return u.protocol==="https:"&&Boolean(u.hostname);}catch{return false;}}).map(d=>({title:d.applications_doc_title||"FDA document",url:d.application_docs_url!}));
  return {applicationNumber,submissionType:s.submission_type||"",submissionNumber:s.submission_number||"",status:s.submission_status||"UNKNOWN",statusDate:validDate?date:null,documents,requiresManualOutcomeClassification:true as const};
 });
 return {applicationNumber,sponsor:input.sponsor_name||"",submissions,warnings};
}
