import {compareHistoricalPdufa,type AnalogueTarget,type HistoricalPdufaAnalogue} from "./decision-historical-analogues";
/** Display-only historical comparison summary. No inferred approval odds or trade recommendation. */
export type HistoricalComparisonDisplay={status:"NOT_READY"|"REVIEW_REQUIRED";totalComparables:number;approved:number;crl:number;withdrawn:number;approvalRatePct:number|null;items:{programId:string;decisionAt:string;outcome:string;sourceUrl:string}[];warnings:string[]};
export function buildHistoricalComparisonDisplay(target:AnalogueTarget,history:HistoricalPdufaAnalogue[]):HistoricalComparisonDisplay{
 const r=compareHistoricalPdufa(target,history);
 const approved=r.matched.filter(x=>x.outcome==="APPROVED").length;
 const crl=r.matched.filter(x=>x.outcome==="CRL").length;
 const withdrawn=r.matched.filter(x=>x.outcome==="WITHDRAWN").length;
 const warnings=[...r.issues,"Historical frequency is descriptive, not a calibrated probability for the current application.","Declared source review flags require independent verification."];
 return {status:r.status==="NOT_READY"?"NOT_READY":"REVIEW_REQUIRED",totalComparables:r.matched.length,approved,crl,withdrawn,approvalRatePct:r.matched.length?100*approved/r.matched.length:null,items:r.matched.map(x=>({programId:x.programId,decisionAt:x.decisionAt,outcome:x.outcome,sourceUrl:x.sourceUrl})),warnings};
}
