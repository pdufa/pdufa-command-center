/** Only published, issuer-source-classified TOP/BOTTOM trial rows may
 * display saved, exact-program numerical metric research grades.
 *
 * No pooling across NCTs, drug/indication, stages or the 11k+ source POOL.
 * No grade is invented for an absent primary+comparator review; N/A != 0.
 * Individual provisional component points are never a validated 30/30
 * composite, FDA outcome probability, or trading recommendation.
 */
import type {ReadoutRow} from "./phase3-public-readout";
import {RAAS_METRIC_CATALOG,type RaasStage} from "./raas-metric-specs";
import {fullReviewedTrialCandidate} from "./raas-reviewed-full-score";

export type ClassifiedRaasComponentMetric={
 id:string;name:string;category:string;
 grade:number|null;finding:string|null;
 assessedAt:string|null;sourceDate:string|null;
 sourceUrl:string|null;benchmarkSourceUrl:string|null;
 reviewClass:"INDEPENDENT_REVIEW"|"AI_SOURCE_CROSSCHECKED"|null;
};
export type ClassifiedRaasComponents={
 stage:"TOP"|"BOTTOM";nctId:string;ticker:string;
 sourceUrl:string;sourceAsOf:string;
 totalMetrics:30;gradedMetrics:number;missingMetrics:number;
 provisionalGrades:ClassifiedRaasComponentMetric[];
 approvedOverallRaasScore:null;
 fdaPassCrlExtensionProbability:null;
 independentFullRaasValidation:false;
};
const validDate=(x:string)=>/^\d{4}-\d{2}-\d{2}$/.test(x)&&
 !Number.isNaN(Date.parse(x+"T00:00:00Z"))&&
 new Date(x+"T00:00:00Z").toISOString().slice(0,10)===x;

export function exactClassifiedRaasComponentGrades(
 stage:RaasStage,row:ReadoutRow
):ClassifiedRaasComponents{
 if(stage!=="pre"&&stage!=="post")
  throw Error("RAAS_ONLY_SOURCE_CLASSIFIED_TOP_BOTTOM");
 const e=row?.evidence;
 const expected=stage==="pre"?"PRE_AS_OF_CHECK":"POST_PUBLIC_READOUT";
 if(!e||e.kind!==expected||e.nctId!==row.nctId||
  e.ticker!==row.ticker||!/^NCT\d{8}$/.test(row.nctId)||
  !row.ticker?.trim()||!validDate(e.evidenceDate)||
  !e.evidenceUrl?.startsWith("https://")||
  !e.drug?.trim()||!e.indication?.trim()||
  row.sourceUrl!=="https://clinicaltrials.gov/study/"+row.nctId)
  throw Error("RAAS_CLASSIFIED_COMPONENT_EXACT_ISSUER_SOURCE_REQUIRED");
 const categories=RAAS_METRIC_CATALOG[stage];
 if(categories.length!==6||categories.some(c=>c.metrics.length!==5))
  throw Error("RAAS_CLASSIFIED_COMPONENT_CATALOG_30_REQUIRED");
 const reviewed=fullReviewedTrialCandidate({
  nctId:row.nctId,ticker:row.ticker,
  drug:e.drug,indication:e.indication
 },stage,false);
 if(reviewed.fullResearchScore!==null||
  reviewed.approvedOverallScore!==null)
  throw Error("RAAS_CLASSIFIED_COMPONENT_NEVER_FULL_OR_APPROVED");
 const byId=new Map(reviewed.grades.map(g=>[g.metricId,g]));
 if(byId.size!==reviewed.reviewedCount)
  throw Error("RAAS_CLASSIFIED_COMPONENT_DUPLICATE_GRADE");
 const metrics=categories.flatMap(c=>c.metrics.map(m=>{
  const item=byId.get(m.id);
  return {
   id:m.id,name:m.name,category:c.name,
   grade:item?.score??null,
   finding:item?.finding??null,
   assessedAt:item?.assessedAt??null,
   sourceDate:item?.sourceDate??null,
   sourceUrl:item?.sourceUrl??null,
   benchmarkSourceUrl:item?.benchmarkSourceUrl??null,
   reviewClass:item?.reviewClass??null
  };
 }));
 if(metrics.length!==30||metrics.filter(x=>x.grade!==null).length!==reviewed.reviewedCount||
  metrics.some(x=>x.grade===null&&(
   x.finding!==null||x.assessedAt!==null||x.sourceDate!==null||
   x.sourceUrl!==null||x.benchmarkSourceUrl!==null||x.reviewClass!==null)))
  throw Error("RAAS_CLASSIFIED_COMPONENT_GRADE_COVERAGE_INVALID");
 return {
  stage:stage==="pre"?"TOP":"BOTTOM",nctId:row.nctId,ticker:row.ticker,
  sourceUrl:e.evidenceUrl,sourceAsOf:e.evidenceDate,
  totalMetrics:30,gradedMetrics:reviewed.reviewedCount,
  missingMetrics:30-reviewed.reviewedCount,
  provisionalGrades:metrics,
  approvedOverallRaasScore:null,
  fdaPassCrlExtensionProbability:null,
  independentFullRaasValidation:false
 };
}
