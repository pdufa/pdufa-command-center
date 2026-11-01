/** Auditable, source-scoped competitive factor for the gold card beside A/P.
 * It is NOT a multi-assessment score, overall trial winner, FDA outcome, or trade call.
 * Never use evidence completeness, market cap, ticker, or shared disease as superiority.
 */
import {benefitForTrial,type BenefitFeed,type BenefitAdvantage} from "./benefit-assessments";
import {validateComparatorInventory,type ComparatorEvidence} from "./pipeline-benefit-assessments";
import {RANKED_BENEFIT_ASSESSMENTS} from "./pipeline-benefit-assessments";
import type {PipelineResearchRow} from "./pipeline-research-view";

export type EdgeTrial=Pick<PipelineResearchRow,"nctId"|"ticker"|"drug"|"indication"> & {
  competitorEvidence?:ComparatorEvidence[]|null;
  comparisonScope?:PipelineResearchRow["comparisonScope"];
};
export type CompetitiveEdge={
  status:"SOURCED_FACTOR"|"NOT_ESTABLISHED"|"NOT_COMPARABLE";
  label:string;
  reason:string;
  assessment:number|null;
  assessmentTitle:string|null;
  comparator:string|null;
  sourceUrl:string|null;
  sourceDate:string|null;
  method:string|null;
  /** Never imply these findings establish overall superiority. */
  overallWinner:false;
};
const same=(a:string|null|undefined,b:string|null|undefined)=>
  !!a?.trim()&&!!b?.trim()&&a.trim().toLowerCase()===b.trim().toLowerCase();
const missing=(reason:string,status:CompetitiveEdge["status"]="NOT_ESTABLISHED"):CompetitiveEdge=>({
  status,label:status==="NOT_COMPARABLE"?"Not comparable":"Not established",
  reason,assessment:null,assessmentTitle:null,comparator:null,
  sourceUrl:null,sourceDate:null,method:null,overallWinner:false
});
const title=(assessment:number)=>RANKED_BENEFIT_ASSESSMENTS.find(a=>a.rank===assessment)?.title||"Benefit assessment";
const sourced=(label:string,reason:string,assessment:number,comparator:string,
  sourceUrl:string,sourceDate:string,method:string):CompetitiveEdge=>({
  status:"SOURCED_FACTOR",label,reason,assessment,assessmentTitle:title(assessment),
  comparator,sourceUrl,sourceDate,method,overallWinner:false
});

/** Only source-reviewed, explicitly comparator-named advantage records can supply a factor.
 * An overallAdvantages rank is a *reviewed priority*, not a validated composite winner.
 */
export function competitiveEdge(
  trial:EdgeTrial,
  feed:BenefitFeed|null=null,
  peers:readonly EdgeTrial[]=[]
):CompetitiveEdge{
  const qualifiedPeers=peers.filter(p=>p.nctId!==trial.nctId);
  if(qualifiedPeers.length && (!trial.drug||!trial.indication||
    qualifiedPeers.some(p=>!same(trial.indication,p.indication))))
    return missing("Different or missing indications: outcomes cannot be ranked across unmatched diseases.",
      "NOT_COMPARABLE");
  if(!trial.drug?.trim()||!trial.indication?.trim()||!/^NCT\d{8}$/.test(trial.nctId))
    return missing("Drug, indication, and exact NCT identity must be verified before comparing.");
  const compareTo=(name:string,nct?:string)=>
    !qualifiedPeers.length||qualifiedPeers.some(p=>(!!nct&&p.nctId===nct&&same(p.drug,name))||
      same(p.drug,name));
  const reviewed=benefitForTrial(feed,{
    nctId:trial.nctId,ticker:trial.ticker,drug:trial.drug,indication:trial.indication
  });
  const advantages=reviewed?.advantages||[];
  const reviewedOverall=(reviewed?.overallAdvantages||[])
    .filter(a=>a.status==="VERIFIED"&&a.confidence==="HIGH"&&compareTo(a.comparator))
    .sort((a,b)=>a.rank-b.rank);
  // All 20 original categories are eligible; do not auto-rank across unrelated
  // domains. Prefer an explicitly REVIEWED cross-category priority when supplied.
  const directSource=trial.competitorEvidence
    ?validateComparatorInventory(trial,trial.competitorEvidence).accepted
      .find(c=>c.comparisonBasis==="DIRECT_HEAD_TO_HEAD"&&c.finding==="BETTER"
        &&c.verificationStatus==="VERIFIED"&&c.confidence==="HIGH"
        &&compareTo(c.therapy,c.kind==="PIPELINE"?c.regulatorOrTrialId:undefined)
        &&!!trial.comparisonScope&&trial.comparisonScope.status==="VERIFIED"
        &&same(trial.comparisonScope.lineOfTherapy,c.lineOfTherapy)
        &&same(trial.comparisonScope.patientPopulation,c.patientPopulation)
        &&same(trial.comparisonScope.endpoint,c.comparisonEvidence?.endpoint)
        &&trial.comparisonScope.followUpMonths===c.comparisonEvidence?.followUpMonths)
    :undefined;
  if(directSource){
    const c=directSource;
    return sourced("Reported head-to-head advantage",
      c.reason+" · "+c.outcome+" · "+c.effectSize,6,c.therapy,
      c.comparisonEvidence!.sourceUrl,c.comparisonEvidence!.verifiedAt,
      "Matched treatment line, population, endpoint and follow-up; source-verified direct comparison. This is a reported finding, not an overall 20-assessment winner.");
  }
  const chosen=reviewedOverall[0]||(
    // Assessment #6 is the explicit competition section. An otherwise verified
    // factor can be shown but not ranked as the "best" across all twenty.
    advantages.filter(a=>a.assessment===6&&a.status==="VERIFIED"
      &&a.confidence==="HIGH"&&compareTo(a.comparator))
      .sort((a,b)=>a.rank-b.rank)[0]
  );
  if(chosen){
    const explicitlyOverall=reviewedOverall.some(a=>a.id===chosen.id);
    return sourced(explicitlyOverall?"Top reviewed competitive factor":"Reviewed competitive factor",
      chosen.comparison,chosen.assessment,chosen.comparator,chosen.sourceUrl,
      chosen.sourceDate,chosen.method+
        (explicitlyOverall?" · Explicit reviewer priority across assessments.":" · Assessment-specific ranking only."));
  }
  return missing(qualifiedPeers.length?
    "No verified, comparator-specific advantage currently establishes one selected trial as stronger. Match the same indication, treatment line, patient population, endpoint and follow-up; review all 20 assessments, safety and uncertainty.":
    "No reviewed comparator-specific advantage is linked to this exact trial. Open assessment #6 and the 20 benefit categories to investigate.");
}
