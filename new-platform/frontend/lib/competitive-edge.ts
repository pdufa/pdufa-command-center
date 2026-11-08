/** Direct comparator evidence only. Original 20-survey ranking is retired. */
import type {PipelineResearchRow} from "./pipeline-research-view";
import {validateComparatorInventory,type ComparatorEvidence} from "./clinical-comparators";
export type EdgeTrial=Pick<PipelineResearchRow,"nctId"|"ticker"|"drug"|"indication"> & {
  competitorEvidence?:ComparatorEvidence[]|null;
  comparisonScope?:PipelineResearchRow["comparisonScope"];
};
export type CompetitiveEdge={
  status:"SOURCED_FACTOR"|"NOT_ESTABLISHED"|"NOT_COMPARABLE";
  label:string;reason:string;assessment:null;assessmentTitle:null;comparator:string|null;
  sourceUrl:string|null;sourceDate:string|null;method:string|null;overallWinner:false;
};
const same=(a:string|null|undefined,b:string|null|undefined)=>
  !!a?.trim()&&!!b?.trim()&&a.trim().toLowerCase()===b.trim().toLowerCase();
const missing=(reason:string,status:CompetitiveEdge["status"]="NOT_ESTABLISHED"):CompetitiveEdge=>({
  status,label:status==="NOT_COMPARABLE"?"Not comparable":"Not established",
  reason,assessment:null,assessmentTitle:null,comparator:null,sourceUrl:null,
  sourceDate:null,method:null,overallWinner:false
});
export function competitiveEdge(trial:EdgeTrial,_retiredFeed:unknown=null,peers:readonly EdgeTrial[]=[]):CompetitiveEdge{
  const others=peers.filter(p=>p.nctId!==trial.nctId);
  if(!trial.drug?.trim()||!trial.indication?.trim()||!/^NCT\d{8}$/.test(trial.nctId))
    return missing("Exact trial, drug and indication identity must be established.");
  if(others.some(p=>!same(p.indication,trial.indication)))
    return missing("Comparators have different indications.","NOT_COMPARABLE");
  const confirmed=trial.competitorEvidence
    ?validateComparatorInventory(trial,trial.competitorEvidence).accepted.find(c=>
      c.comparisonBasis==="DIRECT_HEAD_TO_HEAD"&&c.finding==="BETTER"&&
      c.verificationStatus==="VERIFIED"&&c.confidence==="HIGH"&&
      !!trial.comparisonScope&&trial.comparisonScope.status==="VERIFIED"&&
      same(trial.comparisonScope.lineOfTherapy,c.lineOfTherapy)&&
      same(trial.comparisonScope.patientPopulation,c.patientPopulation)&&
      same(trial.comparisonScope.endpoint,c.comparisonEvidence?.endpoint)&&
      trial.comparisonScope.followUpMonths===c.comparisonEvidence?.followUpMonths)
    :undefined;
  if(!confirmed)return missing("No directly comparable, source-verified clinical advantage established.");
  return {status:"SOURCED_FACTOR",label:"Reported head-to-head advantage",
    reason:confirmed.reason+" · "+confirmed.outcome+" · "+confirmed.effectSize,
    assessment:null,assessmentTitle:null,comparator:confirmed.therapy,
    sourceUrl:confirmed.comparisonEvidence!.sourceUrl,
    sourceDate:confirmed.comparisonEvidence!.verifiedAt,
    method:"Same treatment line, population, endpoint and follow-up; reported finding, not an FDA decision.",
    overallWinner:false};
}
