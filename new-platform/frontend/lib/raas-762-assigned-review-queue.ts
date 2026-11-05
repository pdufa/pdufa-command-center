/** Per-metric research assignment export for the 762 exact registry NCTs.
 * One current ClinicalTrials.gov results-posting stage per trial, never
 * two speculative stages, issuer readout, verified overall RAAS, or FDA odds.
 * Raw registry leads and AI-checked findings remain explicitly unapproved.
 */
import {RAAS_METRIC_CATALOG,type RaasStage} from "./raas-metric-specs";
import {registryMetricLeads,type RegistryEvidenceIndex}
 from "./raas-registry-evidence";
import {stageResearchReviewsForUnverifiedTrial}
 from "./raas-reviewed-full-score";

export type AssignedRaasMetricTask={
 nctId:string;ticker:string;registryStage:"Before"|"Past";
 stageBasis:"REGISTRY_RESULTS_NOT_POSTED"|"REGISTRY_RESULTS_POSTED";
 metricId:string;category:string;categoryWeightPct:number;metricName:string;
 requiredEvidence:string;criticalRisk:string;
 sourceLeadCount:number;registrySourceUrl:string;
 preliminaryMetricScore:number|null;
 preliminaryReviewClass:"AI_SOURCE_CROSSCHECKED"|"INDEPENDENT_REVIEW"|null;
 preliminaryReviewSourceUrl:string|null;
 reviewState:"PROVISIONAL_UNVALIDATED"|"NO_REVIEWED_GRADE";
 independentSignoffState:"NOT_CERTIFIED";
 validatedOverallRaasScore:null;fdaPassProbability:null;fdaCrlProbability:null;
 fdaExtensionProbability:null;
 nextAction:string;
};
export type AssignedRaasQueue={
 summary:{
  exactNctCount:number;beforeTrials:number;pastTrials:number;
  assignedMetricTasks:number;sourceLeads:number;metricTasksWithSourceLeads:number;
  trialRowsWithSourceLeads:number;provisionalMetricTasks:number;
  independentCertifiedMetricTasks:0;validatedOverallScores:0;
  calibratedFdaPredictions:0;
 };
 items:AssignedRaasMetricTask[];
};
export function buildRaas762AssignedReviewQueue(index:RegistryEvidenceIndex):AssignedRaasQueue{
 if(!index||!Array.isArray(index.records)||index.records.length!==762||
  index.summary.researchNcts!==762||
  new Set(index.records.map(e=>e.nctId)).size!==762)
  throw Error("RAAS_762_SOURCE_SCOPE_INVALID");
 const items:AssignedRaasMetricTask[]=[];
 let before=0,past=0,sourceLeads=0,metricTasksWithSourceLeads=0,
  trialRowsWithSourceLeads=0,provisional=0;
 for(const e of index.records){
  const stage:RaasStage=e.postedResults?"post":"pre";
  if(stage==="pre")before++;else past++;
  const trial={nctId:e.nctId,ticker:e.ticker};
  const reviews=stageResearchReviewsForUnverifiedTrial(trial,stage);
  const byGrade=new Map((reviews?.grades||[]).map(g=>[g.metricId,g]));
  const source=registryMetricLeads(e,stage,trial);
  const byLead=new Map<string,number>();
  for(const lead of source)for(const metricId of lead.metricIds)
   byLead.set(metricId,(byLead.get(metricId)||0)+1);
  sourceLeads+=source.length;
  if(source.length>0)trialRowsWithSourceLeads++;
  const groups=RAAS_METRIC_CATALOG[stage];
  if(groups.length!==6||groups.some(g=>g.metrics.length!==5))
   throw Error("RAAS_762_METRIC_CATALOG_INVALID");
  for(const group of groups)for(const metric of group.metrics){
   const grade=byGrade.get(metric.id);
   const sourceLeadCount=byLead.get(metric.id)||0;
   if(sourceLeadCount>0)metricTasksWithSourceLeads++;
   if(grade)provisional++;
   items.push({
    nctId:e.nctId,ticker:e.ticker,registryStage:stage==="pre"?"Before":"Past",
    stageBasis:e.postedResults?"REGISTRY_RESULTS_POSTED":"REGISTRY_RESULTS_NOT_POSTED",
    metricId:metric.id,category:group.name,categoryWeightPct:group.weight,
    metricName:metric.name,requiredEvidence:metric.requiredEvidence,
    criticalRisk:metric.criticalRisk,sourceLeadCount,
    registrySourceUrl:e.sourceUrl,
    preliminaryMetricScore:grade?.score??null,
    preliminaryReviewClass:grade?.reviewClass??null,
    preliminaryReviewSourceUrl:grade?.sourceUrl??null,
    reviewState:grade?"PROVISIONAL_UNVALIDATED":"NO_REVIEWED_GRADE",
    independentSignoffState:"NOT_CERTIFIED",
    validatedOverallRaasScore:null,fdaPassProbability:null,
    fdaCrlProbability:null,fdaExtensionProbability:null,
    nextAction:grade?
     "Independently authenticate the exact trial, therapy, primary source, matched comparator, bias and uncertainty; no certification is recorded.":
     sourceLeadCount>0?
     "Inspect the linked registry lead; obtain independent comparison, prespecified benchmark, uncertainty and signed review before metric grading.":
     "Find metric-specific original primary and comparator evidence for this exact NCT and therapy; document missingness; do not impute a score."
   });
  }
 }
 const expected=index.records.length*30;
 if(before+past!==762||items.length!==expected||
  metricTasksWithSourceLeads>items.length||provisional>items.length)
  throw Error("RAAS_762_ASSIGNMENT_COUNT_MISMATCH");
 return {summary:{
  exactNctCount:762,beforeTrials:before,pastTrials:past,assignedMetricTasks:expected,
  sourceLeads,metricTasksWithSourceLeads,trialRowsWithSourceLeads,
  provisionalMetricTasks:provisional,
  independentCertifiedMetricTasks:0,validatedOverallScores:0,
  calibratedFdaPredictions:0
 },items};
}
export const RAAS_762_REVIEW_CSV_FIELDS=[
 "nctId","ticker","registryStage","stageBasis","metricId","category",
 "categoryWeightPct","metricName","requiredEvidence","criticalRisk",
 "sourceLeadCount","registrySourceUrl","preliminaryMetricScore",
 "preliminaryReviewClass","preliminaryReviewSourceUrl","reviewState",
 "independentSignoffState","validatedOverallRaasScore",
 "fdaPassProbability","fdaCrlProbability","fdaExtensionProbability",
 "nextAction"
] as const;
function csvCell(value:string|number|null){
 const raw=value===null?"":String(value);
 const safe=/^\s*[=+@-]/.test(raw)?"'"+raw:raw;
 return '"'+safe.replaceAll('"','""')+'"';
}
export function exportRaas762AssignedReviewCsv(queue:AssignedRaasQueue):string{
 const rows=[RAAS_762_REVIEW_CSV_FIELDS.join(",")];
 for(const task of queue.items){
  rows.push(RAAS_762_REVIEW_CSV_FIELDS.map(key=>csvCell(task[key])).join(","));
 }
 return "\uFEFF"+rows.join("\r\n")+"\r\n";
}
