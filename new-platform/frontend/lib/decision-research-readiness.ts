/** Independent SCIENCE and OUTCOME readiness gate. Scores alone are not evidence of validation. */
export type ResearchReadiness={programId:string;trialId:string;asOf:string;status:"COMPLETE"|"PARTIAL"|"MISSING";sourceStatus:"VERIFIED"|"UNVERIFIED"|"CONFLICT";reviewedLevels:number;requiredLevels:number;criticalFindingsResolved:boolean;calibrationStatus?:"VALIDATED"|"UNVALIDATED"};
export type CombinedReadiness={status:"NOT_READY"|"EVIDENCE_READY_FOR_REVIEW";issues:string[]};
const dateOk=(s:string,now:Date)=>{const t=Date.parse(s);return Number.isFinite(t)&&t<=now.getTime()+300000&&now.getTime()-t<=86400000;};
/** This is only a readiness signal; never a trade recommendation. */
export function assessScienceOutcomeReadiness(science:ResearchReadiness|null,outcome:ResearchReadiness|null,now=new Date()):CombinedReadiness{
 const issues:string[]=[];
 for(const [name,record] of [["SCIENCE",science],["OUTCOME",outcome]] as const){
  if(!record){issues.push(name+": record missing");continue;}
  if(!/^PDUFA-\d{6,}$/.test(record.programId)||!/^NCT\d{8}$/.test(record.trialId))issues.push(name+": invalid identity");
  if(record.status!=="COMPLETE"||record.sourceStatus!=="VERIFIED")issues.push(name+": assessment or source incomplete");
  if(!Number.isSafeInteger(record.reviewedLevels)||!Number.isSafeInteger(record.requiredLevels)||record.requiredLevels!==20||record.reviewedLevels!==20)issues.push(name+": 20-level review incomplete");
  if(record.criticalFindingsResolved!==true)issues.push(name+": critical findings unresolved");
  if(!dateOk(record.asOf,now))issues.push(name+": stale evidence");
 }
 if(science&&outcome&&(science.programId!==outcome.programId||science.trialId!==outcome.trialId))issues.push("SCIENCE/OUTCOME identities disagree");
 if(outcome?.calibrationStatus!=="VALIDATED")issues.push("OUTCOME calibration not validated");
 return {status:issues.length?"NOT_READY":"EVIDENCE_READY_FOR_REVIEW",issues};
}
