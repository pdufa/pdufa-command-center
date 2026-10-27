/** Canonical record mapping for archived FDA decisions. Does not assert that supplied records are authentic. */
import type {HistoricalPdufaAnalogue} from "./decision-historical-analogues";
export type ArchivedFdaDecision={programId:string;decisionDate:string;decisionType:"APPROVAL"|"COMPLETE_RESPONSE_LETTER"|"WITHDRAWAL"|"OTHER";diseaseSubtype:string;indication:string;mechanism:string;primaryEndpoint:string;trialPhase:number;sourceUrl:string;reviewedBy:string;reviewedAt:string};
export type HistoricalIngestion={status:"NOT_READY"|"READY_FOR_REVIEW";records:HistoricalPdufaAnalogue[];issues:string[]};
export function mapArchivedFdaDecisions(rows:ArchivedFdaDecision[]):HistoricalIngestion{
 const issues:string[]=[];const records:HistoricalPdufaAnalogue[]=[];const seen=new Set<string>();
 for(const [i,r] of rows.entries()){
  const date=Date.parse(r.decisionDate),reviewed=Date.parse(r.reviewedAt);
  if(!/^PDUFA-\d{6,}$/.test(r.programId)||seen.has(r.programId)){issues.push("Row "+i+": invalid or duplicate program");continue;}
  seen.add(r.programId);
  if(!Number.isFinite(date)||!Number.isFinite(reviewed)||reviewed<date){issues.push("Row "+i+": invalid chronology");continue;}
  let sourceOk=false;try{const u=new URL(r.sourceUrl);sourceOk=u.protocol==="https:"&&Boolean(u.hostname);}catch{}
  if(!sourceOk||!r.reviewedBy.trim()){issues.push("Row "+i+": source or review metadata missing");continue;}
  const outcome=r.decisionType==="APPROVAL"?"APPROVED":r.decisionType==="COMPLETE_RESPONSE_LETTER"?"CRL":r.decisionType==="WITHDRAWAL"?"WITHDRAWN":null;
  if(!outcome){issues.push("Row "+i+": unsupported FDA outcome");continue;}
  if(![r.diseaseSubtype,r.indication,r.mechanism,r.primaryEndpoint].every(x=>x.trim())||!Number.isInteger(r.trialPhase)||r.trialPhase<3){issues.push("Row "+i+": insufficient trial attributes");continue;}
  records.push({programId:r.programId,decisionAt:r.decisionDate,diseaseSubtype:r.diseaseSubtype,indication:r.indication,mechanism:r.mechanism,primaryEndpoint:r.primaryEndpoint,trialPhase:r.trialPhase,outcome,sourceUrl:r.sourceUrl,independentlyReviewed:false});
 }
 return {status:issues.length?"NOT_READY":"READY_FOR_REVIEW",records,issues:[...issues,"Imported records require independent source verification before comparison eligibility"]};
}
