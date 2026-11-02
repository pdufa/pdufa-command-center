/** RAAS missing-grade worklist for one exact trial and analysis stage.
 * Survey research facts are evidence leads only, never approved RAAS grades.
 * The caller supplies missing IDs from the independently gated RAAS score engine;
 * neither a VERIFIED survey fact nor an empty mapping can promote an RAAS grade.
 */
import {RAAS_METRIC_CATALOG,type RaasStage} from "./raas-metric-specs";
import type {BenefitRecord} from "./benefit-assessments";

export type RaasMissingMetric={
 id:string;name:string;requiredEvidence:string;
 relatedVerified:number;relatedModeled:number;relatedUnrecorded:number;relatedTotal:number;
 status:"DEDICATED_SOURCE_REQUIRED"|"RELATED_RESEARCH_NOT_VERIFIED"|"PARTIAL_RESEARCH"|"RELATED_RESEARCH_RECORDED";
};
export type RaasMissingGroup={
 id:string;name:string;weight:number;approved:number;total:number;
 missing:readonly RaasMissingMetric[];
};
export type RaasMissingChecklist={
 total:number;approved:number;missing:number;
 categories:readonly RaasMissingGroup[];
};
export function raasMissingMetricChecklist(
 stage:RaasStage,record:BenefitRecord|null,missingIds:readonly string[]
):RaasMissingChecklist|null{
 const categories=RAAS_METRIC_CATALOG[stage];
 const metrics=categories.flatMap(group=>group.metrics);
 const ids=new Set(metrics.map(metric=>metric.id));
 const missing=new Set(missingIds);
 // Fail closed if the score engine and the catalog disagree. A stale set of
 // metric identifiers must not be silently called a complete score.
 if(categories.length!==6||metrics.length!==30||ids.size!==30||
    missing.size!==missingIds.length||missingIds.some(id=>!ids.has(id)))return null;
 return {
  total:30,approved:30-missing.size,missing:missing.size,
  categories:categories.map(group=>({
   id:group.id,name:group.name,weight:group.weight,total:group.metrics.length,
   approved:group.metrics.filter(metric=>!missing.has(metric.id)).length,
   missing:group.metrics.filter(metric=>missing.has(metric.id)).map(metric=>{
    const related=metric.relatedFieldIds;
    const verified=related.filter(id=>record?.facts[id]?.status==="VERIFIED").length;
    const modeled=related.filter(id=>record?.facts[id]?.status==="MODELED").length;
    const unrecorded=related.length-verified-modeled;
    const status: RaasMissingMetric["status"]=related.length===0?"DEDICATED_SOURCE_REQUIRED":
      verified===0?"RELATED_RESEARCH_NOT_VERIFIED":
      unrecorded+modeled>0?"PARTIAL_RESEARCH":"RELATED_RESEARCH_RECORDED";
    return {id:metric.id,name:metric.name,requiredEvidence:metric.requiredEvidence,
     relatedVerified:verified,relatedModeled:modeled,relatedUnrecorded:unrecorded,
     relatedTotal:related.length,status};
   })
  }))
 };
}
