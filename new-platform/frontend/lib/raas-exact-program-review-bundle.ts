/** One bounded, source-frozen 30-requirement reviewer handoff per exact
 * program and RAAS stage. NO human assignment, signature, approved grade,
 * probability, or automatic adjudication is made by this export.
 */
import {createHash} from "node:crypto";
import {buildRaasReviewAssignmentPlan} from "./raas-review-assignment-plan";
import {frozenReviewPacket} from "./raas-external-review-intake";
import {RAAS_PROVISIONAL_RUBRICS} from "./raas-provisional-rubric-engine";
import {RAAS_SPEC_VERSION} from "./raas-metric-specs";

const checksum=(value:unknown)=>createHash("sha256")
 .update(JSON.stringify(value),"utf8").digest("hex");

/** The task lookup, rather than a ticker or NCT alone, prevents mixing
 * indications or the TOP and BOTTOM stage for the same study.
 */
export function buildRaasExactProgramReviewBundle(taskId:string){
 const plan=buildRaasReviewAssignmentPlan();
 const group=plan.groups.find(g=>g.tasks.some(t=>t.taskId===taskId));
 if(!group)return null;
 if(group.tasks.length!==group.provisionalMetrics)
  throw Error("RAAS_BUNDLE_TASK_PARITY");
 const defined=RAAS_PROVISIONAL_RUBRICS.filter(r=>r.stage===group.stage);
 if(defined.length!==30||new Set(defined.map(r=>r.metricId)).size!==30)
  throw Error("RAAS_BUNDLE_EXPECTED_30_RUBRICS");
 const packetByMetric=new Map(group.tasks.map(t=>[t.metricId,t]));
 const requirements=defined.map(rubric=>{
  const task=packetByMetric.get(rubric.metricId);
  const frozen=task?frozenReviewPacket(task.taskId):null;
  if(task&&(!frozen||
   frozen.sourceFingerprint!==task.sourceFingerprint||
   frozen.task.nctId!==group.nctId||
   frozen.task.ticker!==group.ticker||
   frozen.task.drug!==group.drug||
   frozen.task.indication!==group.indication||
   frozen.task.stage!==group.stage||
   frozen.task.metricId!==rubric.metricId))
   throw Error("RAAS_BUNDLE_SOURCE_PACKET_IDENTITY_MISMATCH");
  return {
   metricId:rubric.metricId,
   categoryName:rubric.categoryName,metricName:rubric.name,
   metricWeightPercent:rubric.metricWeightPercent,
   requiredEvidence:rubric.requiredEvidence,
   independentBenchmarkRequirement:rubric.benchmarkRequirement,
   assessmentRule:rubric.assessmentRule,
   criticalRisk:rubric.criticalRisk,
   packetStatus:task?"PROVISIONAL_SOURCE_PACKET_UNAUTHENTICATED" as const:
    "MISSING_PROVISIONAL_EVIDENCE_NOT_ZERO" as const,
   sourceFingerprint:task?.sourceFingerprint??null,
   priorResearchPacket:frozen,
   requiredReviewerEvidence:task?[
    "Independently confirm and reproduce the recorded source result",
    "Reassess comparator, uncertainty, safety, dated sources and dissenting evidence",
    "Sign and archive the review outside the public repository"
   ]:[
    "Obtain appropriate dated primary evidence for this exact metric and program",
    "Identify a distinct source-backed external benchmark; document missing or inaccessible data",
    "Assess uncertainty, critical risk and limitations; never assign a score from absence"
   ],
   certifiedIndependentReview:null,
   approvedMetricGrade:null
  };
 });
 if(requirements.length!==30)throw Error("RAAS_BUNDLE_REQUIREMENT_COUNT");
 const provisional=requirements.filter(r=>r.priorResearchPacket!==null).length;
 if(provisional!==group.provisionalMetrics||
  30-provisional!==group.remainingStageMetrics)
  throw Error("RAAS_BUNDLE_RESEARCH_COVERAGE_MISMATCH");
 const snapshot={
  schemaVersion:1,
  scope:"RAAS_EXACT_PROGRAM_30_METRIC_EXTERNAL_REVIEW_HANDOFF_UNSIGNED" as const,
  sourceAsOf:group.sourceAsOf,rubricVersion:RAAS_SPEC_VERSION,
  program:{
   ticker:group.ticker,nctId:group.nctId,drug:group.drug,
   indication:group.indication,stage:group.stage,priority:group.priority,
   applicationKey:group.applicationKey,trialName:group.trialName
  },
  inventory:{
   requiredMetrics:30,sourceReviewedProvisionalMetrics:provisional,
   missingProvisionalMetricEvidence:30-provisional,
   certifiedIndependentMetrics:0,approvedStageScore:null,
   calibratedFdaForecast:null
  },
  requirements
 };
 const integrity={
  digestAlgorithm:"SHA-256" as const,
  canonicalPayloadHash:checksum(snapshot),
  meaning:"Digest identifies exactly this saved research handoff snapshot, not its clinical truth, independent source verification or reviewer authenticity."
 };
 return {
  ...snapshot,integrity,
  reviewerWorkflow:[
   "Verify the exact NCT, therapy, indication, study phase, TOP/BOTTOM stage, and source date; do not transfer a finding across programs.",
   "Review each of 30 requirements: retain null for missing evidence; explicitly mark unverified studies and outcomes.",
   "Independently reproduce and document clinical/statistical results and benchmark comparisons with dated primary source links, uncertainties and safety risks.",
   "Declare reviewer qualifications, independence and conflicts in a restricted records system; do not publish personally identifying reviewer material or signed reports in public GitHub.",
   "Record a signed independent report in a private archive, then submit only a minimal fingerprint-bound receipt reference via audited change control.",
   "An authenticated receipt is necessary but not sufficient for adjudicating clinical correctness. No part of this bundle approves RAAS metrics, stage scores or FDA PASS/CRL/EXTENSION probabilities."
  ],
  handoffState:"READY_FOR_EXTERNAL_HUMAN_REVIEW_NOT_CERTIFIED" as const,
  approvedOverallRaasScore:null,
  calibratedFdaProbabilities:null
 };
}
