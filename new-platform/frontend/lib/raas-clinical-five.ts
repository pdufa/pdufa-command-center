/** RAAS clinical-five v2: only five patient/clinical-science factors are active.
 * The 30-metric feed remains historical; retired categories never contribute.
 * Missing grades stay null. FDA/PDUFA facts and calibration remain separate.
 */
import type {RaasStage} from "./raas-metric-specs";
import {RAAS_METRIC_CATALOG} from "./raas-metric-specs";
import {fullReviewedTrialCandidate,uniquelyReviewedUnverifiedProgram}
 from "./raas-reviewed-full-score";

export const ACTIVE_RAAS_VERSION="CLINICAL_FIVE_2026_11_05";
export type ClinicalKey="efficacy"|"clinicalBenefit"|"statistics"|"reproducibility"|"safety";
export type ClinicalFactor={
 key:ClinicalKey;id:string;name:string;requiredEvidence:string;
 scoreRule:string;criticalRisk:string;grade:number|null;
 finding:string|null;sourceUrl:string|null;benchmarkSourceUrl:string|null;
 sourceDate:string|null;assessedAt:string|null;
};
export type ClinicalFiveResult={
 stage:RaasStage;stageVerified:boolean;factors:ClinicalFactor[];
 graded:number;missing:number;researchScore:number|null;
};
const active:Record<RaasStage,readonly {key:ClinicalKey;name:string;id:string}[]>={
 pre:[
  {key:"efficacy",name:"Prior clinical efficacy",id:"pre-1-1"},
  {key:"clinicalBenefit",name:"Expected patient benefit and counterevidence",id:"pre-1-5"},
  {key:"statistics",name:"Trial design and statistical strength",id:"pre-1-2"},
  {key:"reproducibility",name:"Mechanism, dose and reproducibility",id:"pre-1-3"},
  {key:"safety",name:"Safety and tolerability",id:"pre-1-4"}
 ],
 post:[
  {key:"efficacy",name:"Actual Phase 3 efficacy",id:"post-1-1"},
  {key:"clinicalBenefit",name:"Clinical importance and patient benefit",id:"post-1-2"},
  {key:"statistics",name:"Statistical reliability",id:"post-1-3"},
  {key:"reproducibility",name:"Replication and durability",id:"post-1-4"},
  {key:"safety",name:"Safety and tolerability",id:"post-1-5"}
 ]
};
export function clinicalFiveDefinitions(stage:RaasStage){
 const spec=RAAS_METRIC_CATALOG[stage].flatMap(g=>g.metrics);
 return active[stage].map(x=>{
  const m=spec.find(z=>z.id===x.id);
  if(!m)throw Error("RAAS_ACTIVE_CLINICAL_SPEC_NOT_FOUND:"+x.id);
  return {...x,requiredEvidence:m.requiredEvidence,
   scoreRule:m.scoreRule,criticalRisk:m.criticalRisk};
 });
}
export function clinicalFiveForTrial(
 trial:{nctId:string;ticker:string;drug?:string;indication?:string},
 stage:RaasStage,stageVerified:boolean
):ClinicalFiveResult{
 const program=trial.drug?.trim()&&trial.indication?.trim()?trial:
  uniquelyReviewedUnverifiedProgram(trial,stage);
 const reviewed=program?fullReviewedTrialCandidate(program,stage,stageVerified):null;
 const byMetric=new Map((reviewed?.grades??[]).map(x=>[x.metricId,x]));
 const factors:ClinicalFactor[]=clinicalFiveDefinitions(stage).map(x=>{
  const grade=byMetric.get(x.id);
  return {key:x.key,id:x.id,name:x.name,requiredEvidence:x.requiredEvidence,
   scoreRule:x.scoreRule,criticalRisk:x.criticalRisk,
   grade:grade?.score??null,finding:grade?.finding??null,
   sourceUrl:grade?.sourceUrl??null,benchmarkSourceUrl:grade?.benchmarkSourceUrl??null,
   sourceDate:grade?.sourceDate??null,assessedAt:grade?.assessedAt??null};
 });
 const graded=factors.filter(x=>x.grade!==null).length;
 // Equal weights are a new explicit clinical-only model, not a legacy RAAS.
 const researchScore=stageVerified&&graded===5?
  Math.round(factors.reduce((n,x)=>n+(x.grade??0),0)/5*10)/10:null;
 return {stage,stageVerified,factors,graded,missing:5-graded,researchScore};
}
export function clinicalFiveForClassifiedRow(row:{
 nctId:string;ticker:string;evidence:{drug:string;indication:string;
  kind:"PRE_AS_OF_CHECK"|"POST_PUBLIC_READOUT"}|null
},stage:RaasStage){
 if(!row.evidence||row.evidence.kind!==(stage==="pre"?
  "PRE_AS_OF_CHECK":"POST_PUBLIC_READOUT"))
  throw Error("RAAS_CLINICAL_FIVE_STAGE_NOT_CLASSIFIED");
 return clinicalFiveForTrial({nctId:row.nctId,ticker:row.ticker,
  drug:row.evidence.drug,indication:row.evidence.indication},stage,true);
}
