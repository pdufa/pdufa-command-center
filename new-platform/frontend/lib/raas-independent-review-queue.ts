/** Source-backed RAAS metric adjudication *queue*, not independently validated
 * scores. Each task is exact NCT + therapy + indication + stage + metric.
 * FDA cases are application-level and never inferred from ticker alone.
 */
import {parseReviewedMetricFeed} from "./raas-reviewed-full-score";
import {RAAS_PROVISIONAL_FINDINGS,RAAS_PROVISIONAL_RUBRICS,
 type RaasProvisionalReview} from "./raas-provisional-rubric-engine";
import type {RaasStage} from "./raas-metric-specs";
import reviews from "../data/raas-reviewed-metric-assessments.json";
import currentPhase3 from "../data/raas-current-pipeline-pre-candidate-snapshots.json";
import acceptedApplications from "../data/raas-current-accepted-fda-applications.json";

export type RaasReviewPriority="FDA_ACCEPTED_PHASE3"|"CURRENT_PHASE3_TOP"|"OTHER_RESEARCH";
export type RaasReviewQueueItem={
 id:string;nctId:string;ticker:string;drug:string;indication:string;
 stage:RaasStage;metricId:string;metricName:string;categoryName:string;
 priority:RaasReviewPriority;trialName:string|null;applicationKey:string|null;
 sourceAsOf:string;sourceDate:string;assessedAt:string;
 sourceUrl:string;benchmarkSourceUrl:string;benchmarkId:string;
 benchmarkContext:string;observedResult:string;uncertaintyReview:string;
 criticalRiskReview:string;reviewerMethod:string;
 provisionalFinding:string;provisionalScore:number;metricWeightPercent:number;
 reviewState:"AI_ASSISTED_AWAITING_HUMAN_REVIEW"|"MARKED_PASSED_NEEDS_AUDIT_RECEIPT";
 approvedOverallRaasScore:null;calibratedFdaProbability:null;
};
export type RaasIndependentReviewQueue={
 asOf:string;items:RaasReviewQueueItem[];
 total:number;uniqueNcts:number;issuerCount:number;
 currentFdaPhase3Metrics:number;currentTopPhase3Metrics:number;otherResearchMetrics:number;
 aiPending:number;markedIndependentWithoutAuditedReceipt:number;
 independentlyVerifiedSignoffs:0;approvedRaasScores:0;calibratedFdaForecasts:0;
};
const rank:Record<RaasReviewPriority,number>={
 FDA_ACCEPTED_PHASE3:0,CURRENT_PHASE3_TOP:1,OTHER_RESEARCH:2
};
const unique=(values:readonly string[])=>new Set(values).size;
const key=(r:RaasProvisionalReview)=>[
 r.nctId,r.ticker,r.drug.toLowerCase().trim(),r.indication.toLowerCase().trim(),
 r.stage,r.metricId
].join("|");

export function buildRaasIndependentReviewQueue():RaasIndependentReviewQueue{
 const feed=parseReviewedMetricFeed(reviews);
 const current=new Map(currentPhase3.trialSnapshots.map(t=>[t.nctId,t]));
 const fda=new Map(acceptedApplications.applications.filter(a=>
  a.phaseOfPivotalEvidence>=3&&a.scoreResearchStage==="post")
  .map(a=>[a.trialNctId,a]));
 const rubrics=new Map(RAAS_PROVISIONAL_RUBRICS.map(r=>[r.metricId,r]));
 const seen=new Set<string>();
 const items=feed.records.map(r=>{
  const id=key(r);
  if(seen.has(id))throw Error("RAAS_REVIEW_QUEUE_DUPLICATE_IDENTITY");
  seen.add(id);
  const rubric=rubrics.get(r.metricId);
  if(!rubric||rubric.stage!==r.stage)throw Error("RAAS_REVIEW_QUEUE_METRIC_MISMATCH");
  const application=fda.get(r.nctId);
  const phase3=current.get(r.nctId);
  // Application/phase matches require exact NCT AND ticker, not issuer grouping.
  const fdaMatched=!!application&&acceptedApplications.issuer.ticker===r.ticker&&
   r.stage==="post";
  const topMatched=!!phase3&&phase3.ticker===r.ticker&&
   phase3.researchStage==="pre"&&r.stage==="pre";
  const priority:RaasReviewPriority=fdaMatched?"FDA_ACCEPTED_PHASE3":
   topMatched?"CURRENT_PHASE3_TOP":"OTHER_RESEARCH";
  return {id,nctId:r.nctId,ticker:r.ticker,drug:r.drug,
   indication:r.indication,stage:r.stage,metricId:r.metricId,
   metricName:rubric.name,categoryName:rubric.categoryName,
   priority,trialName:topMatched?phase3!.trialName:
    fdaMatched?application!.trialName:null,
   applicationKey:fdaMatched?application!.applicationKey:null,
   sourceAsOf:feed.sourceAsOf,sourceDate:r.sourceDate,assessedAt:r.assessedAt,
   sourceUrl:r.sourceUrl,benchmarkSourceUrl:r.benchmarkSourceUrl,
   benchmarkId:r.benchmarkId,benchmarkContext:r.benchmarkContext,
   observedResult:r.observedResult,uncertaintyReview:r.uncertaintyReview,
   criticalRiskReview:r.criticalRiskReview,reviewerMethod:r.reviewerMethod,
   provisionalFinding:r.finding,provisionalScore:RAAS_PROVISIONAL_FINDINGS[r.finding],
   metricWeightPercent:rubric.metricWeightPercent,
   reviewState:r.independentReview==="AI_SOURCE_CROSSCHECKED"?
    "AI_ASSISTED_AWAITING_HUMAN_REVIEW" as const:
    "MARKED_PASSED_NEEDS_AUDIT_RECEIPT" as const,
   approvedOverallRaasScore:null,calibratedFdaProbability:null};
 }).sort((a,b)=>rank[a.priority]-rank[b.priority]||
  a.ticker.localeCompare(b.ticker)||a.nctId.localeCompare(b.nctId)||
  a.metricId.localeCompare(b.metricId));
 return {
  asOf:feed.sourceAsOf,items,total:items.length,
  uniqueNcts:unique(items.map(x=>x.nctId)),issuerCount:unique(items.map(x=>x.ticker)),
  currentFdaPhase3Metrics:items.filter(x=>x.priority==="FDA_ACCEPTED_PHASE3").length,
  currentTopPhase3Metrics:items.filter(x=>x.priority==="CURRENT_PHASE3_TOP").length,
  otherResearchMetrics:items.filter(x=>x.priority==="OTHER_RESEARCH").length,
  aiPending:items.filter(x=>x.reviewState==="AI_ASSISTED_AWAITING_HUMAN_REVIEW").length,
  markedIndependentWithoutAuditedReceipt:items.filter(x=>
   x.reviewState==="MARKED_PASSED_NEEDS_AUDIT_RECEIPT").length,
  independentlyVerifiedSignoffs:0,approvedRaasScores:0,calibratedFdaForecasts:0
 };
}
