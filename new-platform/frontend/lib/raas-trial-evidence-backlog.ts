/** Full 762-trial research evidence backlog.
 * Source coverage is not independent RAAS review, readout classification,
 * current Pipeline qualification, a PDUFA action or a score.
 */
import {parseRegistryEvidenceIndex,type RegistryEvidenceIndex} from "./raas-registry-evidence";
import {parseReviewedMetricFeed} from "./raas-reviewed-full-score";
import {RAAS_METRIC_CATALOG} from "./raas-metric-specs";
import {auditRegistrySourceTrial,type RegistrySourceIssue} from "./raas-registry-source-integrity";
import reviewed from "../data/raas-reviewed-metric-assessments.json";
import currentPhase3 from "../data/raas-current-pipeline-pre-candidate-snapshots.json";
import currentFda from "../data/raas-current-accepted-fda-applications.json";
import readout from "../public/phase3-public-readout-evidence-2026-11-01.json";

export type EvidenceBacklogPriority=
 "FDA_ACCEPTED_PHASE3"|"CURRENT_PHASE3_TOP"|"DATED_READOUT_EVIDENCE"|
 "REGISTRY_COMPARATIVE_RESULTS"|"REGISTRY_RESULTS_OTHER"|"REGISTRY_PROTOCOL_ONLY";
export type EvidenceBacklogStage="pre"|"post"|"unverified";
export type TrialEvidenceBacklogItem={
 nctId:string;ticker:string;priority:EvidenceBacklogPriority;
 stage:EvidenceBacklogStage;stageEvidenceDate:string|null;
 stageSourceUrl:string|null;registeredStatus:string;registeredPhases:string[];
 conditions:string[];interventions:string[];trialName:string|null;
 acceptedPdufaGoal:string|null;applicationKey:string|null;
 sourceUrl:string;sourceDate:string;sourceHash:string;
 postedResults:boolean;postedPrimaryOutcomeCount:number;
 hasPrimaryComparisons:boolean;hasConfidenceIntervals:boolean;hasSeriousEventDenominators:boolean;
 primaryContrastCount:number;primaryNumericCICount:number;saeDenominatorGroupCount:number;
 sourceIntegrityIssues:RegistrySourceIssue[];
 reviewedTop:number;reviewedBottom:number;
 missingTopMetricIds:string[];missingBottomMetricIds:string[];
 ambiguousProgramReviews:boolean;nextEvidenceAction:string;
 approvedRaasScore:null;calibratedFdaProbability:null;
};
export type TrialEvidenceBacklog={
 scope:"RAAS_762_REGISTRY_RESEARCH_TRIAGE_NOT_APPROVED_SCORES";
 sourceAsOf:string;reviewSourceAsOf:string;items:TrialEvidenceBacklogItem[];
 totalTrials:number;trialsWithAnyProvisionalMetrics:number;
 provisionalMetricReviews:number;postedResults:number;protocolOnly:number;
 unverifiedStages:number;currentFdaPhase3:number;currentPhase3Top:number;
 trialsWithComparativeRegistryEvidence:number;trialsWithConfidenceIntervals:number;
 sourceIntegrityFlaggedTrials:number;sourceIntegrityFindings:number;
 independentReviewedMetrics:0;approvedScores:0;calibratedFdaPredictions:0;
};
const stageMetricIds={
 pre:RAAS_METRIC_CATALOG.pre.flatMap(c=>c.metrics.map(m=>m.id)),
 post:RAAS_METRIC_CATALOG.post.flatMap(c=>c.metrics.map(m=>m.id))
};
if(stageMetricIds.pre.length!==30||stageMetricIds.post.length!==30)
 throw Error("RAAS_BACKLOG_METRIC_SPEC_INVALID");
export function buildTrialEvidenceBacklog(rawIndex:unknown):TrialEvidenceBacklog{
 const registry:RegistryEvidenceIndex=parseRegistryEvidenceIndex(rawIndex);
 const review=parseReviewedMetricFeed(reviewed);
 const recordsByNct=new Map<string,typeof review.records>();
 for(const row of review.records){
  const rows=recordsByNct.get(row.nctId)??[];
  rows.push(row);recordsByNct.set(row.nctId,rows);
 }
 const current=new Map(currentPhase3.trialSnapshots.map(x=>[x.nctId,x]));
 const accepted=new Map(currentFda.applications.filter(x=>
  x.phaseOfPivotalEvidence>=3&&x.scoreResearchStage==="post")
  .map(x=>[x.trialNctId,x]));
 const dated=new Map(readout.entries.map(x=>[x.nctId,x]));
 const items=registry.records.map(r=>{
  const sourceAudit=auditRegistrySourceTrial(r,registry.sourceAsOf);
  const knownReview=(recordsByNct.get(r.nctId)??[]).filter(x=>x.ticker===r.ticker);
  const programIds=new Set(knownReview.map(x=>
   JSON.stringify([x.drug.trim().toLowerCase(),x.indication.trim().toLowerCase()])));
  // Fail closed: all metric-review identities remain exact trial+program+stage;
  // do not merge grades across competing therapy/indication programs.
  const ambiguousProgramReviews=programIds.size>1;
  const counted=ambiguousProgramReviews?[]:knownReview;
  const topIds=new Set(counted.filter(x=>x.stage==="pre").map(x=>x.metricId));
  const bottomIds=new Set(counted.filter(x=>x.stage==="post").map(x=>x.metricId));
  const fda=accepted.get(r.nctId);
  const fdaMatched=fda&&r.ticker===currentFda.issuer.ticker?fda:null;
  const pre=current.get(r.nctId);
  const preMatched=pre&&pre.ticker===r.ticker?pre:null;
  const direct=dated.get(r.nctId);
  const directMatched=direct&&direct.ticker===r.ticker?direct:null;
  const stage:EvidenceBacklogStage=fdaMatched?"post":preMatched?"pre":
   directMatched?.kind==="PRE_AS_OF_CHECK"?"pre":
   directMatched?.kind==="POST_PUBLIC_READOUT"?"post":"unverified";
  const stageEvidenceDate=fdaMatched?currentFda.sourceAsOf:
   preMatched?currentPhase3.asOf:
   directMatched?directMatched.evidenceDate:null;
  const stageSourceUrl=fdaMatched?fdaMatched.outcomeEvidenceUrl:
   preMatched?preMatched.issuerTrialSourceUrl:directMatched?.evidenceUrl??null;
  const hasPrimaryComparisons=r.primaryResults.some(x=>
   x.comparisons?.some(c=>c.groupIds?.length>=2)===true);
  const hasConfidenceIntervals=r.primaryResults.some(x=>
   x.comparisons?.some(c=>!!c.ciLowerLimit&&!!c.ciUpperLimit)===true);
  const hasSeriousEventDenominators=r.seriousEventDetails?.some(x=>
   x.groups.some(g=>typeof g.numAffected==="number"&&
    typeof g.numAtRisk==="number"&&g.numAtRisk>0))===true;
  const priority:EvidenceBacklogPriority=fdaMatched?"FDA_ACCEPTED_PHASE3":
   preMatched?"CURRENT_PHASE3_TOP":directMatched?"DATED_READOUT_EVIDENCE":
   hasPrimaryComparisons?"REGISTRY_COMPARATIVE_RESULTS":
   r.postedResults?"REGISTRY_RESULTS_OTHER":"REGISTRY_PROTOCOL_ONLY";
  const reviewedTop=topIds.size,reviewedBottom=bottomIds.size;
  const nextEvidenceAction=fdaMatched?
   "Recheck the exact FDA action cycle and source date; collect independently benchmarked BOTTOM metrics and independent human review. An accepted NDA is not a favorable decision.":
   preMatched?
   "Refresh issuer Phase 3 status, catalyst guidance, capitalization and timed clinical/financial comparators; then source-review the missing TOP metrics. No PDUFA date is established.":
   ambiguousProgramReviews?
   "Resolve the trial-to-therapy/indication mapping before combining any research metric reviews; obtain dated, independent exact-program source evidence.":
   stage==="unverified"?
   "First verify whether an exact Phase 3 public readout occurred, using a dated issuer or regulator source. Then assign TOP or BOTTOM and review trial-specific comparator, safety and financing evidence.":
   "Verify dated trial-specific program evidence and complete the unreviewed metrics for the documented research stage; obtain independent source and benchmark adjudication.";
  return {nctId:r.nctId,ticker:r.ticker,priority,stage,
   stageEvidenceDate,stageSourceUrl,registeredStatus:r.registryStatus,
   registeredPhases:r.registeredPhases,conditions:r.registeredConditions,
   interventions:r.registeredInterventions,trialName:fdaMatched?.trialName??
    preMatched?.trialName??null,
   acceptedPdufaGoal:fdaMatched?.pdufaTargetDate??null,
   applicationKey:fdaMatched?.applicationKey??null,
   sourceUrl:r.sourceUrl,sourceDate:r.registryLastUpdated??r.retrievedAt.slice(0,10),
   sourceHash:r.sourceHash,postedResults:r.postedResults,
   postedPrimaryOutcomeCount:r.postedPrimaryOutcomeCount,
   hasPrimaryComparisons,hasConfidenceIntervals,hasSeriousEventDenominators,
   primaryContrastCount:sourceAudit.primaryComparisons,
   primaryNumericCICount:sourceAudit.comparisonsWithNumericCI,
   saeDenominatorGroupCount:sourceAudit.safetyGroupsWithDenominators,
   sourceIntegrityIssues:sourceAudit.issues,
   reviewedTop,reviewedBottom,
   missingTopMetricIds:stageMetricIds.pre.filter(id=>!topIds.has(id)),
   missingBottomMetricIds:stageMetricIds.post.filter(id=>!bottomIds.has(id)),
   ambiguousProgramReviews,nextEvidenceAction,
   approvedRaasScore:null,calibratedFdaProbability:null};
 });
 const rank:Record<EvidenceBacklogPriority,number>={
  FDA_ACCEPTED_PHASE3:0,CURRENT_PHASE3_TOP:1,DATED_READOUT_EVIDENCE:2,
  REGISTRY_COMPARATIVE_RESULTS:3,REGISTRY_RESULTS_OTHER:4,REGISTRY_PROTOCOL_ONLY:5
 };
 items.sort((a,b)=>rank[a.priority]-rank[b.priority]||
  (b.reviewedTop+b.reviewedBottom)-(a.reviewedTop+a.reviewedBottom)||
  a.ticker.localeCompare(b.ticker)||a.nctId.localeCompare(b.nctId));
 const effectiveReviewed=items.reduce((s,x)=>s+x.reviewedTop+x.reviewedBottom,0);
 return {scope:"RAAS_762_REGISTRY_RESEARCH_TRIAGE_NOT_APPROVED_SCORES",
  sourceAsOf:registry.sourceAsOf,reviewSourceAsOf:review.sourceAsOf,items,
  totalTrials:items.length,
  trialsWithAnyProvisionalMetrics:items.filter(x=>x.reviewedTop+x.reviewedBottom>0).length,
  provisionalMetricReviews:effectiveReviewed,
  postedResults:items.filter(x=>x.postedResults).length,
  protocolOnly:items.filter(x=>!x.postedResults).length,
  unverifiedStages:items.filter(x=>x.stage==="unverified").length,
  currentFdaPhase3:items.filter(x=>x.priority==="FDA_ACCEPTED_PHASE3").length,
  currentPhase3Top:items.filter(x=>x.priority==="CURRENT_PHASE3_TOP").length,
  trialsWithComparativeRegistryEvidence:items.filter(x=>x.hasPrimaryComparisons).length,
  trialsWithConfidenceIntervals:items.filter(x=>x.hasConfidenceIntervals).length,
  sourceIntegrityFlaggedTrials:items.filter(x=>x.sourceIntegrityIssues.length>0).length,
  sourceIntegrityFindings:items.reduce((n,x)=>n+x.sourceIntegrityIssues.length,0),
  independentReviewedMetrics:0,approvedScores:0,calibratedFdaPredictions:0};
}
