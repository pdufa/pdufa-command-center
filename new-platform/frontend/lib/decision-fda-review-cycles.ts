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
  let sourceOk=false;try{const u=new URL(c.sourceUrl);sourceOk=u.protocol==="https:"&&/(^|\.)fda\.gov$/.test(u.hostname);}catch{}
  if(!sourceOk||!c.reviewed)issues.push("Row "+i+": original FDA source requires independent review");
  if(!["APPROVED","CRL","WITHDRAWN"].includes(c.decision))issues.push("Row "+i+": unsupported outcome");
 }
 return {status:issues.length?"NOT_READY":"READY_FOR_REVIEW",cycles,issues};
}
