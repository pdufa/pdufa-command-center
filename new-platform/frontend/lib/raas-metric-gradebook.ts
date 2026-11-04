/** Exact-trial, stage-specific 30-metric RAAS gradebook.
 * Separates a numeric experimental grade from a source lead or a measurement.
 * No incomplete input becomes a 0 or 50, and no component becomes an overall score.
 */
import {RAAS_METRIC_CATALOG,type RaasStage} from "./raas-metric-specs";
import {parseRaasPilotFeed,observedCalculation} from "./raas-score-engine";
import {parseProspectiveSourceBaselines} from "./raas-prospective-source-baselines";
import {provisionalScoresForTrial} from "./raas-provisional-trial-scores";
import type {ProvisionalMetricGrade} from "./raas-threshold-profiles";
import {registryMetricLeads,type RegistryTrialEvidence} from "./raas-registry-evidence";
import {rawRaasRegistryDesignDiagnostic,
 type RawDesignDiagnostic} from "./raas-raw-registry-design";
import {fullReviewedTrialCandidate,type ReviewedTrialCandidate} from "./raas-reviewed-full-score";
import {RAAS_PROVISIONAL_RUBRICS,provisionalStageCoverage,
 type RaasProvisionalRubric} from "./raas-provisional-rubric-engine";
import pilotData from "../data/raas-pilot-observations.json";
import prospectiveData from "../data/raas-prospective-source-baselines.json";

const pilot=parseRaasPilotFeed(pilotData);
const prospective=parseProspectiveSourceBaselines(prospectiveData);
const same=(a:string,b:string)=>a.trim().toLowerCase()===b.trim().toLowerCase();
export type MetricEvidenceLead={
 id:string;kind:string;sourceDate:string;sourceUrl:string;description:string;
 measurement:{label:string;value:number;unit:string}|null;
};
export type MetricScoreStatus="EXPERIMENTAL_GRADE"|"REVIEWED_PROVISIONAL_GRADE"|"SOURCE_LEADS_ONLY"|"EVIDENCE_MISSING";
export type MetricGradebookRow={
 id:string;name:string;requiredEvidence:string;scoreRule:string;criticalRisk:string;
 status:MetricScoreStatus;grade:ProvisionalMetricGrade|null;
 rubric:RaasProvisionalRubric;
 evidence:MetricEvidenceLead[];
};
export type MetricGradebookCategory={
 id:string;name:string;weight:number;
 graded:number;withEvidence:number;missingEvidence:number;
 rows:MetricGradebookRow[];
};
export type RaasTrialGradebook={
 nctId:string;ticker:string;stage:RaasStage;total:30;graded:number;
 mappedOnly:number;withoutEvidence:number;approvedOverallScore:null;
 provisionalDiagnostic:ReturnType<typeof provisionalStageCoverage>;
 registrySourceLeadCount:number;registryNumericObservationCount:number;
 rawDesignDiagnostic:RawDesignDiagnostic|null;
 reviewedCandidate:ReviewedTrialCandidate;
 categories:MetricGradebookCategory[];
};
/** Full issuer/trial/therapy identity; the same ticker is never sufficient. */
function unique<T extends {nctId:string;ticker:string;drug:string;indication:string;stage:RaasStage}>(
 records:readonly T[],trial:{nctId:string;ticker:string;drug?:string;indication?:string},stage:RaasStage
):T|null{
 const hits=records.filter(r=>r.nctId===trial.nctId&&same(r.ticker,trial.ticker)&&r.stage===stage&&
  (!trial.drug?.trim()||same(r.drug,trial.drug))&&
  (!trial.indication?.trim()||same(r.indication,trial.indication)));
 return hits.length===1?hits[0]:null;
}
export function buildRaasMetricGradebook(
 trial:{nctId:string;ticker:string;drug?:string;indication?:string},stage:RaasStage,
 registry:RegistryTrialEvidence|null=null,stageVerified=false
):RaasTrialGradebook{
 if(stage!=="pre"&&stage!=="post")throw Error("RAAS_GRADEBOOK_STAGE_REQUIRED");
 if(!/^NCT\d{8}$/.test(trial.nctId)||!trial.ticker?.trim())
  throw Error("RAAS_GRADEBOOK_IDENTITY_INVALID");
 const sourcePilot=unique(pilot.records,trial,stage);
 const sourceProspective=unique(prospective.records,trial,stage);
 const leads:({metricIds:string[]}&MetricEvidenceLead)[]=[];
 for(const o of sourcePilot?.observations||[]){
  if(o.assessmentDate>pilot.sourceAsOf)continue;
  leads.push({id:o.id,metricIds:o.metricIds,kind:o.kind,sourceDate:o.assessmentDate,
   sourceUrl:o.sourceUrl,description:o.valueText||o.title,
   measurement:observedCalculation(o)});
 }
 for(const o of sourceProspective?.observations||[]){
  if(o.sourcePublishedAt>prospective.sourceAsOf||
     o.sourcePublishedAt>sourceProspective!.capturedOn)continue;
  leads.push({id:o.id,metricIds:o.metricIds,kind:o.kind,sourceDate:o.sourcePublishedAt,
   sourceUrl:o.sourceUrl,description:o.valueText,measurement:null});
 }
 const registryLeads=registryMetricLeads(registry,stage,trial);
 leads.push(...registryLeads);
 const reviewedCandidate=fullReviewedTrialCandidate(trial,stage,stageVerified);
 for(const r of reviewedCandidate.grades){
  leads.push({id:r.metricId+"-documented-review-"+r.assessedAt,
   metricIds:[r.metricId],kind:"SOURCE_GATED_DOCUMENTED_PROVISIONAL_REVIEW",
   sourceDate:r.sourceDate,sourceUrl:r.sourceUrl,description:r.explanation,
   measurement:null});
 }
 // Numeric component scoring is only enabled for narrowly source-gated pilot
 // rules, never inferred from a registry endpoint definition or a p-value.
 const provisional=provisionalScoresForTrial(trial,stage);
 const reviewedGrades:ProvisionalMetricGrade[]=reviewedCandidate.grades.map(g=>({
  metricId:g.metricId,stage:g.stage,snapshot:"CURRENT",
  score:g.score,ruleId:g.ruleVersion,kind:"RESEARCH_ONLY_NOT_VALIDATED",
  observationId:"documented-review-"+g.metricId+"-"+g.assessedAt,
  sourceUrl:g.sourceUrl,sourceDate:g.sourceDate,
  label:"Documented source-and-benchmark review; research only",
  inputs:g.explanation,explanation:g.explanation,
  limitations:"Not validated against out-of-sample FDA outcomes; does not establish an approval probability."
 }));
 const gradeMap=new Map(provisional.scoredMetrics.map(g=>[g.metricId,g]));
 for(const g of reviewedGrades)gradeMap.set(g.metricId,g);
 const reviewedIds=new Set(reviewedGrades.map(g=>g.metricId));
 const categories=RAAS_METRIC_CATALOG[stage].map(group=>{
  const rows=group.metrics.map(metric=>{
   const evidence=leads.filter(lead=>lead.metricIds.includes(metric.id))
    .map(({metricIds,...lead})=>lead);
   const grade=gradeMap.get(metric.id)||null;
   const status:MetricScoreStatus=reviewedIds.has(metric.id)?"REVIEWED_PROVISIONAL_GRADE":
    grade?"EXPERIMENTAL_GRADE":
    evidence.length?"SOURCE_LEADS_ONLY":"EVIDENCE_MISSING";
   const rubric=RAAS_PROVISIONAL_RUBRICS.find(r=>r.stage===stage&&r.metricId===metric.id);
   if(!rubric)throw Error("RAAS_GRADEBOOK_RUBRIC_MISSING:"+metric.id);
   return {id:metric.id,name:metric.name,requiredEvidence:metric.requiredEvidence,
    scoreRule:metric.scoreRule,criticalRisk:metric.criticalRisk,status,grade,evidence,rubric};
  });
  return {id:group.id,name:group.name,weight:group.weight,rows,
   graded:rows.filter(x=>x.grade!==null).length,
   withEvidence:rows.filter(x=>x.evidence.length>0).length,
   missingEvidence:rows.filter(x=>x.evidence.length===0).length};
 });
 const all=categories.flatMap(x=>x.rows);
 if(categories.length!==6||all.length!==30||new Set(all.map(x=>x.id)).size!==30)
  throw Error("RAAS_GRADEBOOK_CATALOG_INCOMPLETE");
 return {nctId:trial.nctId,ticker:trial.ticker,stage,total:30,
  graded:all.filter(x=>x.grade!==null).length,
  mappedOnly:all.filter(x=>x.status==="SOURCE_LEADS_ONLY").length,
  withoutEvidence:all.filter(x=>x.status==="EVIDENCE_MISSING").length,
  approvedOverallScore:null,categories,registrySourceLeadCount:registryLeads.length,
  registryNumericObservationCount:registryLeads.filter(x=>x.measurement!==null).length,
  rawDesignDiagnostic:rawRaasRegistryDesignDiagnostic(registry,trial),
  reviewedCandidate,
  provisionalDiagnostic:provisionalStageCoverage(stage,provisional.scoredMetrics)};
}
