/** Historical analogues are mandatory evidence for FDA decision research, not a standalone approval predictor. */
export type HistoricalPdufaAnalogue={programId:string;decisionAt:string;diseaseSubtype:string;indication:string;mechanism:string;primaryEndpoint:string;trialPhase:number;outcome:"APPROVED"|"CRL"|"WITHDRAWN";sourceUrl:string;independentlyReviewed:boolean};
export type AnalogueTarget={programId:string;asOf:string;diseaseSubtype:string;indication:string;mechanism:string;primaryEndpoint:string};
export type AnalogueReview={status:"NOT_READY"|"HISTORICAL_COMPARISON_READY_FOR_REVIEW";matched:HistoricalPdufaAnalogue[];issues:string[]};
export function compareHistoricalPdufa(target:AnalogueTarget,history:HistoricalPdufaAnalogue[],minimum=3):AnalogueReview{
 const issues:string[]=[];const asOf=Date.parse(target.asOf);const seen=new Set<string>();
 if(!/^PDUFA-\d{6,}$/.test(target.programId)||!Number.isFinite(asOf))issues.push("Invalid target identity or decision cutoff");
 const same=(a:string,b:string)=>a.trim().toLowerCase()===b.trim().toLowerCase()&&Boolean(a.trim());
 const matched=history.filter(r=>{
  const decision=Date.parse(r.decisionAt);
  if(!/^PDUFA-\d{6,}$/.test(r.programId)||seen.has(r.programId)){issues.push("Invalid or duplicate historical program");return false;}
  seen.add(r.programId);
  if(!Number.isFinite(decision)||decision>=asOf||r.programId===target.programId)return false;
  if(!r.independentlyReviewed||!r.sourceUrl.startsWith("https://"))return false;
  return r.trialPhase>=3&&same(r.diseaseSubtype,target.diseaseSubtype)&&same(r.indication,target.indication)&&same(r.mechanism,target.mechanism)&&same(r.primaryEndpoint,target.primaryEndpoint);
 });
 if(!Number.isSafeInteger(minimum)||minimum<3||matched.length<minimum)issues.push("Insufficient independently reviewed, pre-cutoff close analogues");
 return {status:issues.length?"NOT_READY":"HISTORICAL_COMPARISON_READY_FOR_REVIEW",matched,issues};
}
