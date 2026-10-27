/** Evidence manifest for a historical prediction. URLs and asserted flags alone never verify a record. */
export type HistoricalEvidenceRow={programId:string;predictedAt:string;decisionAt:string;predictionSource:string;decisionSource:string;predictionCapturedAt:string;decisionObservedAt:string;probability:number;approved:boolean;reviewStatus:"INDEPENDENTLY_VERIFIED"|"PENDING"|"CONFLICT"};
export type HistoricalEvidenceAudit={status:"NOT_READY"|"READY_FOR_INDEPENDENT_REVIEW";issues:string[];accepted:number};
const https=(s:string)=>{try{const u=new URL(s);return u.protocol==="https:"&&Boolean(u.hostname);}catch{return false;}};
/** Prevent outcome leakage, duplicate programs and self-declared source completeness. */
export function auditHistoricalEvidence(rows:HistoricalEvidenceRow[],minimum=30):HistoricalEvidenceAudit{
 const issues:string[]=[];const seen=new Set<string>();let accepted=0;
 for(const [i,r] of rows.entries()){
  const p=Date.parse(r.predictedAt),d=Date.parse(r.decisionAt),capture=Date.parse(r.predictionCapturedAt),observed=Date.parse(r.decisionObservedAt);
  if(!/^PDUFA-\d{6,}$/.test(r.programId)||seen.has(r.programId))issues.push("Row "+i+": invalid or duplicate identity");
  seen.add(r.programId);
  if(![p,d,capture,observed].every(Number.isFinite)||p>=d||capture>d||capture<p||observed<d)issues.push("Row "+i+": invalid chronology or possible future leakage");
  if(!https(r.predictionSource)||!https(r.decisionSource))issues.push("Row "+i+": HTTPS source missing");
  if(!Number.isFinite(r.probability)||r.probability<0||r.probability>1||typeof r.approved!=="boolean")issues.push("Row "+i+": invalid probability or outcome");
  if(r.reviewStatus!=="INDEPENDENTLY_VERIFIED")issues.push("Row "+i+": independent review incomplete");
  else accepted++;
 }
 if(!Number.isSafeInteger(minimum)||minimum<30||rows.length<minimum)issues.push("Insufficient historical sample");
 return {status:issues.length?"NOT_READY":"READY_FOR_INDEPENDENT_REVIEW",issues,accepted};
}
