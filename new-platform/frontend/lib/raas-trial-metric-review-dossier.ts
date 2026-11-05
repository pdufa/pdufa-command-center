/** Exact-NCT research dossier connecting 30 TOP + 30 BOTTOM RAAS metric
 * requirements to source-frozen registry leads and existing provisional
 * per-metric reviews. This is a REVIEW WORKSPACE, NOT an automated grade.
 * Never infer a public readout from registry result posting or mix programs.
 */
import {parseRegistryEvidenceIndex} from "./raas-registry-evidence";
import {buildTrialEvidenceBacklog,type TrialEvidenceBacklogItem}
 from "./raas-trial-evidence-backlog";
import {buildRaasRegistryClinicalFactLedger,type RaasRegistryClinicalFact}
 from "./raas-registry-clinical-fact-ledger";
import {parseReviewedMetricFeed} from "./raas-reviewed-full-score";
import {RAAS_METRIC_CATALOG,type RaasStage} from "./raas-metric-specs";
import {RAAS_PROVISIONAL_FINDINGS,type RaasProvisionalFinding}
 from "./raas-provisional-rubric-engine";
import savedReviewData from "../data/raas-reviewed-metric-assessments.json";

export type TrialMetricReview={
 metricId:string;name:string;categoryName:string;categoryWeightPercent:number;
 metricWeightPercent:number;requiredEvidence:string;scoreRule:string;criticalRisk:string;
 registryLeadCount:number;registryRawNumericCount:number;registryLeads:RaasRegistryClinicalFact[];
 /** Provisional source-backed research finding, not an authenticated signoff. */
 provisionalReview:null|{
  drug:string;indication:string;finding:RaasProvisionalFinding;researchBand:number;
  assessedAt:string;sourceDate:string;sourceUrl:string;benchmarkSourceUrl:string;
  benchmarkId:string;benchmarkContext:string;observedResult:string;
  uncertaintyReview:string;criticalRiskReview:string;reviewerMethod:string;
  feedReviewClass:"AI_SOURCE_CROSSCHECKED"|"PASSED";
 };
 authenticatedHumanSignoff:false;approvedRaasGrade:null;
 missingRequiredIndependentEvidence:boolean;
};
export type TrialMetricReviewCategory={
 id:string;name:string;weight:number;metrics:TrialMetricReview[];
};
export type TrialMetricReviewDossier={
 scope:"RAAS_EXACT_NCT_60_METRIC_REVIEW_WORKSPACE_UNAPPROVED";
 trial:TrialEvidenceBacklogItem;registrySnapshotAsOf:string;
 provisionalReviewFeedAsOf:string;
 acceptedStageSource:null|{stage:"pre"|"post";date:string;url:string};
 sourceIntegrityFlagCount:number;ambiguousProgramReviews:boolean;
 researchStageAvailability:"STAGE_UNVERIFIED"|"TOP_SOURCE"|"BOTTOM_SOURCE";
 perStage:Record<RaasStage,{
  reviewCount:number;rawSourceFactCount:number;
  withRegistryLeads:number;missingMetricCount:number;
  independentlyAuthenticatedReviews:0;approvedFullStageScore:null;
  categories:TrialMetricReviewCategory[];
 }>;
 certifiedMetrics:0;approvedScores:0;fdaPassCrlExtensionProbability:null;
};

const same=(a:string,b:string)=>a.trim().toLowerCase()===b.trim().toLowerCase();
export function buildTrialMetricReviewDossier(
 rawRegistry:unknown,nctId:string,ticker:string
):TrialMetricReviewDossier|null{
 if(!/^NCT\d{8}$/.test(nctId)||!/^[A-Za-z0-9.\-]{1,20}$/.test(ticker))
  return null;
 const registry=parseRegistryEvidenceIndex(rawRegistry);
 const item=buildTrialEvidenceBacklog(registry).items.find(x=>
  x.nctId===nctId&&same(x.ticker,ticker));
 if(!item)return null;
 const record=registry.records.find(x=>x.nctId===nctId&&same(x.ticker,ticker));
 if(!record||record.sourceHash!==item.sourceHash)
  throw Error("RAAS_TRIAL_DOSSIER_SOURCE_IDENTITY_MISMATCH");
 const feed=parseReviewedMetricFeed(savedReviewData);
 const reviews=feed.records.filter(r=>r.nctId===nctId&&same(r.ticker,ticker));
 const programs=new Set(reviews.map(r=>
  JSON.stringify([r.drug.trim().toLowerCase(),r.indication.trim().toLowerCase()])));
 const ambiguous=programs.size>1||item.ambiguousProgramReviews;
 const admissibleReviews=ambiguous?[]:reviews;
 const registryFacts=buildRaasRegistryClinicalFactLedger(registry).facts.filter(f=>
  f.nctId===nctId&&same(f.ticker,ticker)&&f.sourceHash===item.sourceHash);
 const perStage={} as TrialMetricReviewDossier["perStage"];
 for(const stage of ["pre","post"] as const){
  const categories:TrialMetricReviewCategory[]=RAAS_METRIC_CATALOG[stage].map(category=>({
   id:category.id,name:category.name,weight:category.weight,
   metrics:category.metrics.map(metric=>{
    const facts=registryFacts.filter(x=>
     x.candidateStage===stage&&x.metricIds.includes(metric.id));
    const evidence=admissibleReviews.filter(x=>x.stage===stage&&x.metricId===metric.id);
    if(evidence.length>1)throw Error("RAAS_TRIAL_DOSSIER_DUPLICATE_PROGRAM_METRIC");
    const review=evidence[0];
    return {
     metricId:metric.id,name:metric.name,categoryName:category.name,
     categoryWeightPercent:category.weight,metricWeightPercent:category.weight/5,
     requiredEvidence:metric.requiredEvidence,scoreRule:metric.scoreRule,
     criticalRisk:metric.criticalRisk,
     registryLeadCount:facts.length,
     registryRawNumericCount:facts.filter(f=>f.measurementValue!==null).length,
     registryLeads:facts,
     provisionalReview:review?{
      drug:review.drug,indication:review.indication,
      finding:review.finding,researchBand:RAAS_PROVISIONAL_FINDINGS[review.finding],
      assessedAt:review.assessedAt,sourceDate:review.sourceDate,
      sourceUrl:review.sourceUrl,benchmarkSourceUrl:review.benchmarkSourceUrl,
      benchmarkId:review.benchmarkId,benchmarkContext:review.benchmarkContext,
      observedResult:review.observedResult,
      uncertaintyReview:review.uncertaintyReview,
      criticalRiskReview:review.criticalRiskReview,
      reviewerMethod:review.reviewerMethod,feedReviewClass:review.independentReview
     }:null,
     authenticatedHumanSignoff:false as const,approvedRaasGrade:null,
     missingRequiredIndependentEvidence:true
    };
   })
  }));
  const metrics=categories.flatMap(x=>x.metrics);
  if(metrics.length!==30||new Set(metrics.map(x=>x.metricId)).size!==30)
   throw Error("RAAS_TRIAL_DOSSIER_INCOMPLETE_METRIC_SPEC");
  const reviewCount=metrics.filter(x=>x.provisionalReview!==null).length;
  if(reviewCount!==(stage==="pre"?item.reviewedTop:item.reviewedBottom))
   throw Error("RAAS_TRIAL_DOSSIER_REVIEW_COUNT_MISMATCH");
  perStage[stage]={
   reviewCount,rawSourceFactCount:registryFacts.filter(x=>x.candidateStage===stage).length,
   withRegistryLeads:metrics.filter(x=>x.registryLeadCount>0).length,
   missingMetricCount:30-reviewCount,independentlyAuthenticatedReviews:0,
   approvedFullStageScore:null,categories
  };
 }
 return {
  scope:"RAAS_EXACT_NCT_60_METRIC_REVIEW_WORKSPACE_UNAPPROVED",
  trial:item,registrySnapshotAsOf:registry.sourceAsOf,
  provisionalReviewFeedAsOf:feed.sourceAsOf,
  acceptedStageSource:item.stage==="unverified"||!item.stageSourceUrl||!item.stageEvidenceDate?
   null:{stage:item.stage,date:item.stageEvidenceDate,url:item.stageSourceUrl},
  sourceIntegrityFlagCount:item.sourceIntegrityIssueCount,
  ambiguousProgramReviews:ambiguous,
  researchStageAvailability:item.stage==="unverified"?"STAGE_UNVERIFIED":
   item.stage==="pre"?"TOP_SOURCE":"BOTTOM_SOURCE",
  perStage,certifiedMetrics:0,approvedScores:0,fdaPassCrlExtensionProbability:null
 };
}
