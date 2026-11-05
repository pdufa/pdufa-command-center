/** Audit-ready research worklist: ONLY the two phase-3 research spreadsheets: one checklist per NCT.
 * TOP (registry not posted) 425 rows; BOTTOM (registry posted) 337 rows,
 * for 22,860 distinct metric slots in the current dated research snapshot.
 *
 * The only numerical values carried forward are existing, dated,
 * source-checked provisional review grades. A registry protocol, a
 * posted result, or an unmapped trial NEVER becomes a metric grade.
 * Stage and FDA eligibility remain UNVERIFIED. Nothing is persisted or
 * backdated by preparing this export.
 */
import {RAAS_METRIC_CATALOG,RAAS_SPEC_VERSION,type RaasStage}
 from "./raas-metric-specs";
import {RAAS_PROVISIONAL_RUBRICS}
 from "./raas-provisional-rubric-engine";
import {stageResearchReviewsForUnverifiedTrial}
 from "./raas-reviewed-full-score";
import {registryMetricLeads,type RegistryEvidenceIndex,type RegistryTrialEvidence}
 from "./raas-registry-evidence";

export type Raas762MetricQueueSummary={
 exactNcts:762;stageResearchRows:762;metricSlots:22860;
 topTrialRows:number;bottomTrialRows:number;
 otherStageReviewsPreserved:number;
 provisionalReviewSlots:number;independentlyReviewedMetricSlots:number;
 registryLeadOnlySlots:number;metricSlotsRequiringReviewedGrades:number;
 noMappedEvidenceSlots:number;
 researchOnly:true;fullyValidatedRaasScores:0;calibratedFdaPredictions:0;
};
const names=[
 "nctId","ticker","stageChecklist","readoutStageVerified",
 "metricId","category","metric","categoryWeightPct",
 "reviewStatus","provisionalComponentScoreOrBlank",
 "reviewAssessedAt","reviewSourceDate","reviewSourceUrl",
 "benchmarkSourceUrl","mappedRegistryEvidenceLeadCount",
 "registryEvidenceLeadUrl","registryResultsPosted",
 "registeredPhase","nextReviewAction","requiredEvidence",
 "benchmarkRequirement","criticalRisk","modelSpec","overallRaasScore"
] as const;
const serialize=(x:unknown):string=>{
 const s=x===null||x===undefined?"":String(x);
 // Avoid spreadsheet formula execution for external labels/text.
 const safe=/^[=+@-]/.test(s)?"'"+s:s;
 return /[",\r\n]/.test(safe)?'"'+safe.replace(/"/g,'""')+'"':safe;
};
const output=(fields:readonly unknown[])=>fields.map(serialize).join(",");
const slug=(x:RaasStage)=>x==="pre"?"TOP_RESEARCH_ONLY":"BOTTOM_RESEARCH_ONLY";

export function buildRaas762MetricEvidenceQueue(index:RegistryEvidenceIndex):{
 csv:string;summary:Raas762MetricQueueSummary
}{
 if(!index||index.schemaVersion!==1||
  index.scope!=="RAAS_REGISTRY_TRIAL_EVIDENCE_INDEX"||
  index.records?.length!==762||index.summary?.researchNcts!==762||
  index.summary.registryRecords!==762||
  index.summary.approvedOverallRaasScores!==0||
  new Set(index.records.map(x=>x.nctId)).size!==762)
  throw Error("RAAS_762_METRIC_QUEUE_EXACT_ROSTER_REQUIRED");
 for(const stage of ["pre","post"] as const){
  const groups=RAAS_METRIC_CATALOG[stage];
  if(groups.length!==6||groups.some(x=>x.metrics.length!==5)||
   groups.flatMap(x=>x.metrics).length!==30)
   throw Error("RAAS_762_METRIC_QUEUE_INCOMPLETE_30_STAGE_CATALOG");
 }
 if(RAAS_PROVISIONAL_RUBRICS.length!==60||
  new Set(RAAS_PROVISIONAL_RUBRICS.map(x=>x.metricId)).size!==60)
  throw Error("RAAS_762_METRIC_QUEUE_PROVISIONAL_RULES_INCOMPLETE");
 const rows:string[]=[names.join(",")];
 const ids=new Set<string>();
 let provisional=0,independent=0,registryLeadsOnly=0,noMapped=0;
 let top=0,bottom=0,otherStageReviewsPreserved=0;
 for(const record of [...index.records].sort((a,b)=>a.nctId.localeCompare(b.nctId))){
  const {nctId,ticker}=record;
  if(!/^NCT\d{8}$/.test(nctId)||!ticker?.trim()||
   record.sourceUrl!=="https://clinicaltrials.gov/study/"+nctId||
   ids.has(nctId))
   throw Error("RAAS_762_METRIC_QUEUE_INVALID_SOURCE_IDENTITY");
  ids.add(nctId);
  if(typeof record.postedResults!=="boolean")
   throw Error("RAAS_TOP_BOTTOM_STAGE_SOURCE_UNKNOWN");
  const stage:RaasStage=record.postedResults?"post":"pre";
  if(stage==="pre")top++;else bottom++;
  // Preserve different-stage historical evidence as history. It does NOT
  // become a grade on the currently selected research spreadsheet.
  const otherStage=stage==="pre"?"post":"pre";
  otherStageReviewsPreserved+=
   stageResearchReviewsForUnverifiedTrial({nctId,ticker},otherStage)?.reviewedCount??0;
  {
   const reviewed=stageResearchReviewsForUnverifiedTrial({nctId,ticker},stage);
   const reviewedById=new Map(reviewed?.grades.map(x=>[x.metricId,x])??[]);
   if(reviewedById.size!==(reviewed?.reviewedCount??0))
    throw Error("RAAS_762_METRIC_QUEUE_DUPLICATE_REVIEWED_METRIC");
   const leads=registryMetricLeads(record,stage,{nctId,ticker});
   const leadsById=new Map<string,typeof leads>();
   for(const lead of leads){
    for(const metricId of lead.metricIds){
     const a=leadsById.get(metricId)??[];
     a.push(lead);leadsById.set(metricId,a);
    }
   }
   for(const group of RAAS_METRIC_CATALOG[stage]){
    for(const metric of group.metrics){
     const key=nctId+"|"+stage+"|"+metric.id;
     const grade=reviewedById.get(metric.id);
     const knownLeads=leadsById.get(metric.id)??[];
     const rubric=RAAS_PROVISIONAL_RUBRICS.find(
      x=>x.metricId===metric.id&&x.stage===stage);
     if(!rubric||rubric.approvedForComposite!==false)
      throw Error("RAAS_762_METRIC_QUEUE_RUBRIC_NOT_RESEARCH_ONLY");
     if(grade){
      provisional++;
      if(grade.reviewClass==="INDEPENDENT_REVIEW")independent++;
     }else if(knownLeads.length)registryLeadsOnly++;
     else noMapped++;
     const reviewStatus=grade?
      grade.reviewClass==="INDEPENDENT_REVIEW"?
       "DOCUMENTED_PROVISIONAL_INDEPENDENT_REVIEW_NOT_VALIDATED":
       "AI_SOURCE_CROSSCHECKED_PROVISIONAL_NOT_VALIDATED":
      knownLeads.length?"REGISTRY_SOURCE_LEAD_NOT_GRADED":
       "REVIEW_MISSING_NO_MAPPED_METRIC_SOURCE";
     const nextAction=grade?
      "Verify independent reviewer, uncertainty, timing and model calibration before any validated RAAS rating":
      knownLeads.length?
       "Review dated same-trial registry facts and independently verify comparator, indication and metric benchmark":
       "Find dated same-therapy primary metric source and independent comparator; review before assigning a score";
     const fields=[
      nctId,ticker,slug(stage),"NO",metric.id,group.name,metric.name,
      group.weight,reviewStatus,grade?.score??null,
      grade?.assessedAt??null,grade?.sourceDate??null,grade?.sourceUrl??null,
      grade?.benchmarkSourceUrl??null,knownLeads.length,
      knownLeads[0]?.sourceUrl??null,record.postedResults?"YES":"NO",
      record.registeredPhases.join(";"),nextAction,metric.requiredEvidence,
      rubric.benchmarkRequirement,metric.criticalRisk,RAAS_SPEC_VERSION,null
     ];
     if(fields.length!==names.length||!key)
      throw Error("RAAS_762_METRIC_QUEUE_COLUMNS_MISMATCH");
     rows.push(output(fields));
    }
   }
  }
 }
 if(ids.size!==762||top+bottom!==762||rows.length!==22861||
  provisional+registryLeadsOnly+noMapped!==22860)
  throw Error("RAAS_762_METRIC_QUEUE_COMPLETENESS_MISMATCH");
 const summary:Raas762MetricQueueSummary={
  exactNcts:762,stageResearchRows:762,metricSlots:22860,
  topTrialRows:top,bottomTrialRows:bottom,otherStageReviewsPreserved,
  provisionalReviewSlots:provisional,independentlyReviewedMetricSlots:independent,
  registryLeadOnlySlots:registryLeadsOnly,
  metricSlotsRequiringReviewedGrades:22860-provisional,
  noMappedEvidenceSlots:noMapped,
  researchOnly:true,fullyValidatedRaasScores:0,calibratedFdaPredictions:0
 };
 return {csv:rows.join("\r\n")+"\r\n",summary};
}
