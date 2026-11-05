/** Unapproved nightly ClinicalTrials.gov revision -> metric-review *intake*.
 * The 82 source-reviewed provisional metric packets remain a separate queue.
 * Registry source changes may suggest candidate metric investigation, never
 * prove readout stage, clinical benefit, human signoff or model calibration.
 */
import {parseRegistryEvidenceIndex} from "./raas-registry-evidence";
import {RAAS_METRIC_CATALOG,type RaasStage} from "./raas-metric-specs";
import {buildRaasIndependentReviewQueue,type RaasIndependentReviewQueue}
 from "./raas-independent-review-queue";

type HistoryEvent={
 eventId:string;observedAt:string;nctId:string;ticker:string;sourceUrl:string;
 previousSourceHash:string;newSourceHash:string;
 changeCategories:string[];reviewFlag:string;candidateResearchMetricIds:string[];
 approvedRaasScore:null;calibratedFdaProbability:null;
};
type HistoryInput={
 schemaVersion:1;scope:string;events:HistoryEvent[];
};
type StatusInput={
 schemaVersion:1;scope:string;auditState:string;
 recordedAt:string|null;latestSourceAsOf:string|null;
 trackedResearchNcts:number;totalRetainedHistoricalEvents:number;
 approvedRaasScoreUpdates:0;calibratedFdaForecastUpdates:0;
};
export type RaasRegistryRevisionReviewTask={
 id:string;nctId:string;ticker:string;metricId:string;
 metricName:string;metricStage:RaasStage;categoryName:string;
 categoryWeightPercent:number;
 observedAt:string;firstObservedAt:string;
 sourceUrl:string;previousSourceHash:string;newSourceHash:string;
 eventId:string;changeCategories:string[];
 revisionCountForMetric:number;currentRegistryHash:string;
 sourceMatch:"MATCHES_SAVED_REGISTRY"|"SOURCE_VERSION_SUPERSEDED_OR_UNSYNCED";
 matchingExistingProvisionalResearchReviews:number;
 provisionalResearchIdentity:
  "NO_EXISTING_PROVISIONAL_REVIEW"|"EXACT_NCT_METRIC_REVIEW_EXISTS"|
  "MULTIPLE_PROGRAM_IDENTITIES_NEED_ADJUDICATION";
 state:"REQUIRES_INDEPENDENT_EVIDENCE_REASSESSMENT";
 approvedRaasMetricGrade:null;approvedRaasScore:null;calibratedFdaForecast:null;
};
export type RaasRegistryRevisionReviewInbox={
 scope:"RAAS_SOURCE_REVISIONS_TO_60_METRIC_HUMAN_REVIEW_NO_AUTO_GRADE";
 auditState:string;lastComparedAt:string|null;
 registryAsOf:string;historyEvents:number;revisionReviewEvents:number;
 candidateMetricAssignments:number;uniqueTrialMetricTasks:number;
 uniqueNcts:number;existingProvisionalReviewPairs:number;
 supersededOrUnsyncedTasks:number;independentlyApprovedMetrics:0;
 approvedRaasScores:0;calibratedFdaForecasts:0;
 tasks:RaasRegistryRevisionReviewTask[];
};
const nct=/^NCT\d{8}$/;
const sha=/^[a-f0-9]{64}$/;
const eventId=/^[a-f0-9]{64}$/;
const routing:Record<string,readonly string[]>={
 RESULTS_FIRST_POSTED:["post-1-1","post-1-3","post-1-5"],
 RESULTS_POSTING_REVERSED:["post-1-1","post-1-3","post-1-5"],
 PRIMARY_OUTCOME_RESULTS_CHANGED:["post-1-1","post-1-3"],
 SERIOUS_ADVERSE_EVENT_RESULTS_CHANGED:["post-1-5"],
 PRIMARY_ENDPOINT_PROTOCOL_CHANGED:["pre-1-2"],
 TRIAL_DESIGN_CHANGED:["pre-1-2"],
 TRIAL_CONTEXT_CHANGED:["pre-1-2"]
};
const instant=(s:string):number=>{
 const t=Date.parse(s);
 if(!s||!Number.isFinite(t)||!/(Z|[+-]\d\d:\d\d)$/.test(s))
  throw Error("RAAS_REVISION_INBOX_EVENT_TIME_INVALID");
 return t;
};
export function buildRaasRegistryRevisionReviewInbox(
 rawHistory:unknown,rawStatus:unknown,rawRegistry:unknown,
 existingQueue:RaasIndependentReviewQueue=buildRaasIndependentReviewQueue()
):RaasRegistryRevisionReviewInbox{
 const history=rawHistory as HistoryInput,status=rawStatus as StatusInput;
 if(!history||history.schemaVersion!==1||
  history.scope!=="RAAS_EXACT_NCT_REGISTRY_SOURCE_CHANGE_HISTORY_UNGRADED"||
  !Array.isArray(history.events)||
  !status||status.schemaVersion!==1||
  status.scope!=="RAAS_NIGHTLY_REGISTRY_CHANGE_AUDIT_RESEARCH_ONLY"||
  !["COMPLETE","COMPLETED_WITH_SOURCE_ERRORS",
    "AWAITING_FIRST_COMPARATIVE_SCAN"].includes(status.auditState)||
  status.trackedResearchNcts!==762||
  status.totalRetainedHistoricalEvents!==history.events.length||
  status.approvedRaasScoreUpdates!==0||
  status.calibratedFdaForecastUpdates!==0)
  throw Error("RAAS_REVISION_INBOX_AUDIT_INTEGRITY_INVALID");
 if(status.auditState==="AWAITING_FIRST_COMPARATIVE_SCAN"&&
    (status.recordedAt!==null||history.events.length>0))
  throw Error("RAAS_REVISION_INBOX_UNPERFORMED_SCAN_WITH_EVENTS");
 if(status.auditState!=="AWAITING_FIRST_COMPARATIVE_SCAN"&&
    (!status.recordedAt||!status.latestSourceAsOf))
  throw Error("RAAS_REVISION_INBOX_MISSING_SCAN_RECEIPT");
 const registry=parseRegistryEvidenceIndex(rawRegistry);
 if(registry.records.length!==762)throw Error("RAAS_REVISION_INBOX_ROSTER_MISMATCH");
 const indexById=new Map(registry.records.map(x=>[x.nctId,x]));
 const metrics=new Map((["pre","post"] as const).flatMap(stage=>
  RAAS_METRIC_CATALOG[stage].flatMap(category=>category.metrics.map(metric=>
   [metric.id,{stage,name:metric.name,categoryName:category.name,
    categoryWeightPercent:category.weight}] as const))));
 const provisionalByExactMetric=new Map<string,Set<string>>();
 for(const r of existingQueue.items){
  const key=[r.nctId,r.ticker.toUpperCase(),r.metricId].join("|");
  const set=provisionalByExactMetric.get(key)??new Set<string>();
  set.add(JSON.stringify([r.drug.toLowerCase().trim(),r.indication.toLowerCase().trim()]));
  provisionalByExactMetric.set(key,set);
 }
 const newest=new Map<string,RaasRegistryRevisionReviewTask>();
 const uniqueEvents=new Set<string>();
 let recent=0,metricAssignments=0,reviewEvents=0;
 for(const event of history.events){
  if(!event||!eventId.test(event.eventId)||uniqueEvents.has(event.eventId)||
   !nct.test(event.nctId)||!sha.test(event.previousSourceHash)||
   !sha.test(event.newSourceHash)||
   event.previousSourceHash===event.newSourceHash||
   !Array.isArray(event.changeCategories)||!event.changeCategories.length||
   !Array.isArray(event.candidateResearchMetricIds)||
   event.approvedRaasScore!==null||event.calibratedFdaProbability!==null||
   !["CLINICAL_OR_DESIGN_REVIEW_REQUIRED","OTHER_OFFICIAL_REGISTRY_UPDATE"].includes(event.reviewFlag))
   throw Error("RAAS_REVISION_INBOX_EVENT_INVALID");
  const ts=instant(event.observedAt);
  if(ts<recent)throw Error("RAAS_REVISION_INBOX_NONMONOTONIC_HISTORY");
  if(status.recordedAt&&ts>instant(status.recordedAt))
   throw Error("RAAS_REVISION_INBOX_EVENT_AFTER_LAST_SCAN");
  recent=ts;uniqueEvents.add(event.eventId);
  const current=indexById.get(event.nctId);
  if(!current||current.ticker.toUpperCase()!==event.ticker.toUpperCase()||
   current.sourceUrl!==event.sourceUrl)
   throw Error("RAAS_REVISION_INBOX_CROSS_TRIAL_SOURCE_IDENTITY");
  const ids=new Set(event.candidateResearchMetricIds);
  if(ids.size!==event.candidateResearchMetricIds.length)
   throw Error("RAAS_REVISION_INBOX_DUPLICATE_METRIC_IDS");
  const expected=new Set(event.changeCategories.flatMap(x=>[...(routing[x]??[])]));
  if(ids.size!==expected.size||[...ids].some(x=>!expected.has(x)))
   throw Error("RAAS_REVISION_INBOX_CATEGORY_METRIC_ROUTING_MISMATCH");
  if(event.reviewFlag==="CLINICAL_OR_DESIGN_REVIEW_REQUIRED"&&
   expected.size===0)
   throw Error("RAAS_REVISION_INBOX_REVIEW_EVENT_WITHOUT_METRIC");
  if(event.reviewFlag==="OTHER_OFFICIAL_REGISTRY_UPDATE"&&ids.size>0)
   throw Error("RAAS_REVISION_INBOX_ADMIN_EVENT_CANNOT_GRADE_METRIC");
  if(event.reviewFlag==="CLINICAL_OR_DESIGN_REVIEW_REQUIRED"){
   reviewEvents++;
   if(ids.size===0)throw Error("RAAS_REVISION_INBOX_REVIEW_EVENT_WITHOUT_METRIC");
  }
  for(const metricId of ids){
   const rubric=metrics.get(metricId);
   if(!rubric)throw Error("RAAS_REVISION_INBOX_UNKNOWN_METRIC");
   metricAssignments++;
   const key=[event.nctId,event.ticker.toUpperCase(),metricId].join("|");
   const existing=provisionalByExactMetric.get(key);
   const prior=newest.get(key);
   newest.set(key,{
    id:key,nctId:event.nctId,ticker:event.ticker,metricId,
    metricName:rubric.name,metricStage:rubric.stage,
    categoryName:rubric.categoryName,categoryWeightPercent:rubric.categoryWeightPercent,
    observedAt:event.observedAt,firstObservedAt:prior?.firstObservedAt??event.observedAt,
    sourceUrl:event.sourceUrl,previousSourceHash:event.previousSourceHash,
    newSourceHash:event.newSourceHash,eventId:event.eventId,
    changeCategories:event.changeCategories,
    revisionCountForMetric:(prior?.revisionCountForMetric??0)+1,
    currentRegistryHash:current.sourceHash,
    sourceMatch:current.sourceHash===event.newSourceHash?
     "MATCHES_SAVED_REGISTRY":"SOURCE_VERSION_SUPERSEDED_OR_UNSYNCED",
    matchingExistingProvisionalResearchReviews:existing?.size??0,
    provisionalResearchIdentity:!existing?.size?"NO_EXISTING_PROVISIONAL_REVIEW":
     existing.size===1?"EXACT_NCT_METRIC_REVIEW_EXISTS":
     "MULTIPLE_PROGRAM_IDENTITIES_NEED_ADJUDICATION",
    state:"REQUIRES_INDEPENDENT_EVIDENCE_REASSESSMENT",
    approvedRaasMetricGrade:null,approvedRaasScore:null,calibratedFdaForecast:null
   });
  }
 }
 const tasks=[...newest.values()].sort((a,b)=>
  b.observedAt.localeCompare(a.observedAt)||
  a.nctId.localeCompare(b.nctId)||a.metricId.localeCompare(b.metricId));
 return {
  scope:"RAAS_SOURCE_REVISIONS_TO_60_METRIC_HUMAN_REVIEW_NO_AUTO_GRADE",
  auditState:status.auditState,lastComparedAt:status.recordedAt,
  registryAsOf:registry.sourceAsOf,historyEvents:history.events.length,
  revisionReviewEvents:reviewEvents,candidateMetricAssignments:metricAssignments,
  uniqueTrialMetricTasks:tasks.length,
  uniqueNcts:new Set(tasks.map(x=>x.nctId)).size,
  existingProvisionalReviewPairs:tasks.filter(x=>
   x.matchingExistingProvisionalResearchReviews>0).length,
  supersededOrUnsyncedTasks:tasks.filter(x=>
   x.sourceMatch!=="MATCHES_SAVED_REGISTRY").length,
  independentlyApprovedMetrics:0,approvedRaasScores:0,calibratedFdaForecasts:0,tasks
 };
}

/** Change-category and existing-packet filters are triage only, never a
 * relative clinical severity score, reviewer approval or FDA forecast.
 * One source update can belong to multiple clinical-review focus categories.
 */
export type RaasReviewChangeFocus="all"|"primary"|"safety"|"design";
export type RaasReviewPriorPacketFilter="all"|"existing"|"new";
export function matchesRaasRevisionReviewTriage(
 task:Pick<RaasRegistryRevisionReviewTask,
  "changeCategories"|"matchingExistingProvisionalResearchReviews">,
 focus:RaasReviewChangeFocus,prior:RaasReviewPriorPacketFilter
):boolean{
 const categories=new Set(task.changeCategories);
 const focusMatch=focus==="all"||
  (focus==="primary"&&[
   "RESULTS_FIRST_POSTED","RESULTS_POSTING_REVERSED",
   "PRIMARY_OUTCOME_RESULTS_CHANGED"
  ].some(category=>categories.has(category)))||
  (focus==="safety"&&categories.has("SERIOUS_ADVERSE_EVENT_RESULTS_CHANGED"))||
  (focus==="design"&&[
   "PRIMARY_ENDPOINT_PROTOCOL_CHANGED","TRIAL_DESIGN_CHANGED",
   "TRIAL_CONTEXT_CHANGED"
  ].some(category=>categories.has(category)));
 const priorMatch=prior==="all"||
  (prior==="existing"&&task.matchingExistingProvisionalResearchReviews>0)||
  (prior==="new"&&task.matchingExistingProvisionalResearchReviews===0);
 return focusMatch&&priorMatch;
}
