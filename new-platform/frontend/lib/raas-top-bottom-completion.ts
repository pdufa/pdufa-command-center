/** Complete source-backed status ledger for the TWO classified RAAS sheets.
 * All 30 requirements are represented per exact NCT; an absent primary-source
 * review is a nullable missing grade, NEVER a zero, neutral rating, or a
 * fabricated FDA probability. The 11k+ POOL, 762 registry prep inventory,
 * and issuer-unverified queue are excluded.
 */
import type {ReadoutClassification,ReadoutRow} from "./phase3-public-readout";
import {exactClassifiedRaasComponentGrades} from "./raas-classified-component-grades";
import {RAAS_METRIC_CATALOG,type RaasStage} from "./raas-metric-specs";
import {RAAS_PROVISIONAL_RUBRICS} from "./raas-provisional-rubric-engine";

export type RaasClassifiedCompletionTask={
 nctId:string;ticker:string;stage:"TOP"|"BOTTOM";metricId:string;
 category:string;categoryWeightPct:number;metricName:string;
 status:"SOURCE_CHECKED_PROVISIONAL_ONLY"|"NO_SOURCE_REVIEWED_GRADE";
 numericProvisionalGrade:number|null;
 sourceCheckedAt:string;issuerDisclosureUrl:string;registrySourceUrl:string;
 reviewedPrimarySourceUrl:string|null;reviewedComparatorSourceUrl:string|null;
 reviewAssessedAt:string|null;primarySourceDated:string|null;
 requiredSourceEvidence:string;requiredIndependentBenchmark:string;
 criticalRisk:string;scoreRule:string;
 nextAction:string;independentValidationStatus:"NOT_COMPLETED";
 approvedOverallScore:null;calibratedFdaApprovalProbability:null;
};
type TrialSummary={
 nctId:string;ticker:string;stage:"TOP"|"BOTTOM";
 reviewed:number;missing:number;approvedOverallScore:null;
 sourceUrl:string;issuerEvidenceDate:string;
};
export type RaasTopBottomCompletion={
 summary:{
  scoredScope:"SOURCE_CLASSIFIED_TOP_BOTTOM_ONLY";
  researchSourceCensus:number;unclassifiedResearchRows:number;
  topTrials:number;bottomTrials:number;classifiedTrialRows:number;
  topMetricSlots:number;bottomMetricSlots:number;allMetricSlots:number;
  provisionalMetricGrades:number;missingMetricGrades:number;
  independentFullScores:0;calibratedFdaProbabilities:0;
  gradingSetupReady:true;allNumericGradesFinished:false;
 };
 trials:TrialSummary[];tasks:RaasClassifiedCompletionTask[];
 allCsv:string;missingOnlyCsv:string;
};
const columns=[
 "nctId","ticker","stage","metricId","category","categoryWeightPct",
 "metricName","status","numericProvisionalGrade",
 "issuerEvidenceDate","issuerEvidenceUrl","ClinicalTrialsGovUrl",
 "reviewedPrimarySourceUrl","reviewedComparatorSourceUrl","assessedAt",
 "primarySourceDated","requiredSourceEvidence","requiredIndependentBenchmark",
 "criticalRisk","scoreRule","nextAction",
 "independentValidationStatus","approvedOverallScore",
 "calibratedFdaApprovalProbability"
] as const;
const csvCell=(value:string|number|null)=>{
 const raw=value===null?"":String(value);
 const safe=/^[=+@\-\t\r]/.test(raw)?"'"+raw:raw;
 return /[",\r\n]/.test(safe)?'"'+safe.replace(/"/g,'""')+'"':safe;
};
const csvRow=(values:(string|number|null)[])=>values.map(csvCell).join(",");
function exportCsv(rows:readonly RaasClassifiedCompletionTask[]){
 const csv=[columns.join(",")];
 for(const r of rows){
  csv.push(csvRow([
   r.nctId,r.ticker,r.stage,r.metricId,r.category,r.categoryWeightPct,
   r.metricName,r.status,r.numericProvisionalGrade,
   r.sourceCheckedAt,r.issuerDisclosureUrl,r.registrySourceUrl,
   r.reviewedPrimarySourceUrl,r.reviewedComparatorSourceUrl,
   r.reviewAssessedAt,r.primarySourceDated,r.requiredSourceEvidence,
   r.requiredIndependentBenchmark,r.criticalRisk,r.scoreRule,r.nextAction,
   r.independentValidationStatus,r.approvedOverallScore,
   r.calibratedFdaApprovalProbability
  ]));
 }
 return csv.join("\r\n")+"\r\n";
}

export function buildRaasTopBottomCompletion(data:ReadoutClassification):
 RaasTopBottomCompletion{
 if(!data||!Array.isArray(data.pre)||!Array.isArray(data.post)||
  !Array.isArray(data.unverified)||
  !Number.isSafeInteger(data.total)||
  data.pre.length+data.post.length+data.unverified.length!==data.total)
  throw Error("RAAS_TOP_BOTTOM_COMPLETION_INVALID_CLASSIFICATION");
 const allItems=new Set<string>(),tasks:RaasClassifiedCompletionTask[]=[];
 const trials:TrialSummary[]=[];
 let topSlots=0,bottomSlots=0,reviewedCount=0;
 const rubricById=new Map(RAAS_PROVISIONAL_RUBRICS.map(r=>[r.metricId,r]));
 if(rubricById.size!==60)throw Error("RAAS_TOP_BOTTOM_RUBRIC_INCOMPLETE");
 const stages:[RaasStage,readonly ReadoutRow[]][]=[
  ["pre",data.pre],["post",data.post]
 ];
 for(const [stage,rows] of stages){
  const groups=RAAS_METRIC_CATALOG[stage];
  if(groups.length!==6||groups.some(g=>g.metrics.length!==5))
   throw Error("RAAS_TOP_BOTTOM_METRICS_NOT_30");
  for(const row of rows){
   if(allItems.has(row.nctId))throw Error("RAAS_TOP_BOTTOM_DUPLICATE_CLASSIFIED_NCT");
   allItems.add(row.nctId);
   const grade=exactClassifiedRaasComponentGrades(stage,row);
   const found=new Map(grade.provisionalGrades.map(x=>[x.id,x]));
   if(found.size!==30||grade.gradedMetrics+grade.missingMetrics!==30||
    grade.approvedOverallRaasScore!==null||
    grade.fdaPassCrlExtensionProbability!==null)
    throw Error("RAAS_TOP_BOTTOM_GRADEBOOK_COUNT_INVALID");
   const reviewed=grade.gradedMetrics;
   reviewedCount+=reviewed;
   trials.push({
    nctId:row.nctId,ticker:row.ticker,stage:grade.stage,
    reviewed,missing:30-reviewed,approvedOverallScore:null,
    sourceUrl:grade.sourceUrl,issuerEvidenceDate:grade.sourceAsOf
   });
   if(stage==="pre")topSlots+=30;
   else bottomSlots+=30;
   for(const g of groups)for(const m of g.metrics){
    const current=found.get(m.id);
    const rubric=rubricById.get(m.id);
    if(!current||!rubric||rubric.stage!==stage||
     rubric.approvedForComposite!==false)
     throw Error("RAAS_TOP_BOTTOM_EVIDENCE_METRIC_NOT_APPROVED_FOR_SOURCE_QUEUE");
    const hasGrade=current.grade!==null;
    const task:RaasClassifiedCompletionTask={
     nctId:row.nctId,ticker:row.ticker,stage:grade.stage,metricId:m.id,
     category:g.name,categoryWeightPct:g.weight,metricName:m.name,
     status:hasGrade?"SOURCE_CHECKED_PROVISIONAL_ONLY":"NO_SOURCE_REVIEWED_GRADE",
     numericProvisionalGrade:current.grade,
     sourceCheckedAt:grade.sourceAsOf,
     issuerDisclosureUrl:grade.sourceUrl,registrySourceUrl:row.sourceUrl,
     reviewedPrimarySourceUrl:current.sourceUrl,
     reviewedComparatorSourceUrl:current.benchmarkSourceUrl,
     reviewAssessedAt:current.assessedAt,primarySourceDated:current.sourceDate,
     requiredSourceEvidence:m.requiredEvidence,
     requiredIndependentBenchmark:rubric.benchmarkRequirement,
     criticalRisk:m.criticalRisk,scoreRule:m.scoreRule,
     nextAction:hasGrade?
      "Reverify exact primary-source finding, comparator and uncertainty with independent reviewer; provisional grade is not validated.":
      "Find exact-trial, same-therapy primary evidence; verify dated comparator, effect size, uncertainty, critical risks and independent reviewer before assigning a numeric metric grade.",
     independentValidationStatus:"NOT_COMPLETED",
     approvedOverallScore:null,calibratedFdaApprovalProbability:null
    };
    if(!hasGrade&&(task.reviewedPrimarySourceUrl!==null||
     task.reviewedComparatorSourceUrl!==null||
     task.reviewAssessedAt!==null||task.primarySourceDated!==null))
     throw Error("RAAS_TOP_BOTTOM_MISSING_SCORE_HAS_UNVERIFIED_REVIEW_DATA");
    tasks.push(task);
   }
  }
 }
 for(const unclassified of data.unverified){
  if(allItems.has(unclassified.nctId))
   throw Error("RAAS_TOP_BOTTOM_UNVERIFIED_LEAKED_INTO_CLASSIFIED");
 }
 const expected=topSlots+bottomSlots;
 const missing=tasks.filter(x=>x.numericProvisionalGrade===null);
 if(tasks.length!==expected||reviewedCount+missing.length!==expected||
  trials.length!==data.pre.length+data.post.length||
  tasks.some(t=>t.approvedOverallScore!==null||
   t.calibratedFdaApprovalProbability!==null))
  throw Error("RAAS_TOP_BOTTOM_COMPLETION_RECONCILIATION_FAILED");
 tasks.sort((a,b)=>
  a.stage.localeCompare(b.stage)||
  b.categoryWeightPct-a.categoryWeightPct||
  a.ticker.localeCompare(b.ticker)||
  a.nctId.localeCompare(b.nctId)||
  a.metricId.localeCompare(b.metricId));
 trials.sort((a,b)=>a.stage.localeCompare(b.stage)||
  b.missing-a.missing||a.ticker.localeCompare(b.ticker));
 return {
  summary:{
   scoredScope:"SOURCE_CLASSIFIED_TOP_BOTTOM_ONLY",
   researchSourceCensus:data.total,
   unclassifiedResearchRows:data.unverified.length,
   topTrials:data.pre.length,bottomTrials:data.post.length,
   classifiedTrialRows:trials.length,
   topMetricSlots:topSlots,bottomMetricSlots:bottomSlots,
   allMetricSlots:expected,
   provisionalMetricGrades:reviewedCount,
   missingMetricGrades:missing.length,
   independentFullScores:0,calibratedFdaProbabilities:0,
   gradingSetupReady:true,allNumericGradesFinished:false
  },
  trials,tasks,allCsv:exportCsv(tasks),missingOnlyCsv:exportCsv(missing)
 };
}
