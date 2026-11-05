/** Source-frozen 82-packet independent-review assignment planning.
 * Not a clinician assignment, signed opinion, final grade, or FDA forecast.
 * Keep NCT, therapy, indication and TOP/BOTTOM distinct.
 */
import {buildRaasIndependentReviewQueue,
 type RaasIndependentReviewQueue,type RaasReviewPriority}
 from "./raas-independent-review-queue";
import {auditRaasExternalReviewReceipts,sourceFrozenFingerprint}
 from "./raas-external-review-intake";
import receiptLedger from "../data/raas-external-review-receipts.json";

export type RaasReviewAssignmentTask={
 taskId:string;metricId:string;metricName:string;metricWeightPercent:number;
 sourceDate:string;sourceUrl:string;benchmarkSourceUrl:string;
 sourceFingerprint:string;
 receiptState:"NO_RECEIPT"|"BLOCKED_RECEIPT"|"RECEIPT_PENDING_AUTHENTICATION";
 approvedMetricGrade:null;calibratedFdaProbability:null;
};
export type RaasReviewAssignmentGroup={
 id:string;nctId:string;ticker:string;drug:string;indication:string;
 stage:"pre"|"post";priority:RaasReviewPriority;applicationKey:string|null;
 trialName:string|null;sourceAsOf:string;
 provisionalMetrics:number;remainingStageMetrics:number;
 receiptPending:number;receiptBlocked:number;
 tasks:RaasReviewAssignmentTask[];
 externalReviewerAssigned:false;approvedStageScore:null;
};
export type RaasReviewAssignmentPlan={
 scope:"RAAS_SOURCE_FROZEN_EXPERT_REVIEW_ASSIGNMENT_PLAN_NOT_APPROVAL";
 asOf:string;totalPackets:number;distinctPrograms:number;
 fdaAcceptedPhase3Packets:number;currentPhase3TopPackets:number;
 otherResearchPackets:number;
 externallyAssignedReviewers:0;certifiedIndependentMetricSignoffs:0;
 submittedReceiptReferences:number;pendingReceiptAuthentication:number;
 blockedReceiptReferences:number;approvedStageScores:0;
 calibratedFdaForecasts:0;
 groups:RaasReviewAssignmentGroup[];
};
const priorityRank:Record<RaasReviewPriority,number>={
 FDA_ACCEPTED_PHASE3:0,CURRENT_PHASE3_TOP:1,OTHER_RESEARCH:2
};
/** Same NCT may refer to several drug/indication programs. Never pool them. */
const identity=(task:RaasIndependentReviewQueue["items"][number])=>
 JSON.stringify([task.nctId,task.ticker,task.drug.trim().toLowerCase(),
 task.indication.trim().toLowerCase(),task.stage,task.applicationKey]);

export function buildRaasReviewAssignmentPlan(
 queue:RaasIndependentReviewQueue=buildRaasIndependentReviewQueue()
):RaasReviewAssignmentPlan{
 // Check exact task identity before passing it to the external receipt auditor.
 // The independently audited receipt parser also fails closed on duplicates.
 if(new Set(queue.items.map(item=>item.id)).size!==queue.items.length)
  throw Error("RAAS_ASSIGNMENT_DUPLICATE_EXACT_TASK");
 const receipts=auditRaasExternalReviewReceipts(receiptLedger,queue.items);
 const receiptByTask=new Map<string,Set<RaasReviewAssignmentTask["receiptState"]>>();
 for(const check of receipts.checks){
  const state=check.status==="BLOCKED"?
   "BLOCKED_RECEIPT" as const:"RECEIPT_PENDING_AUTHENTICATION" as const;
  const taskStates=receiptByTask.get(check.taskId)??new Set();
  taskStates.add(state);receiptByTask.set(check.taskId,taskStates);
 }
 const byProgram=new Map<string,RaasReviewAssignmentGroup>();
 const uniqueTasks=new Set<string>();
 for(const item of queue.items){
  if(uniqueTasks.has(item.id))throw Error("RAAS_ASSIGNMENT_DUPLICATE_EXACT_TASK");
  uniqueTasks.add(item.id);
  const key=identity(item);
  let group=byProgram.get(key);
  if(!group){
   group={id:key,nctId:item.nctId,ticker:item.ticker,
    drug:item.drug,indication:item.indication,stage:item.stage,
    priority:item.priority,applicationKey:item.applicationKey,
    trialName:item.trialName,sourceAsOf:item.sourceAsOf,
    provisionalMetrics:0,remainingStageMetrics:30,
    receiptPending:0,receiptBlocked:0,tasks:[],
    externalReviewerAssigned:false,approvedStageScore:null};
   byProgram.set(key,group);
  }
  if(group.sourceAsOf!==item.sourceAsOf||group.priority!==item.priority)
   throw Error("RAAS_ASSIGNMENT_INCONSISTENT_PROGRAM_SNAPSHOT");
  if(group.tasks.some(t=>t.metricId===item.metricId))
   throw Error("RAAS_ASSIGNMENT_DUPLICATE_PROGRAM_METRIC");
  const states=receiptByTask.get(item.id);
  const receiptState=states?.has("BLOCKED_RECEIPT")?"BLOCKED_RECEIPT":
   states?.has("RECEIPT_PENDING_AUTHENTICATION")?
   "RECEIPT_PENDING_AUTHENTICATION":"NO_RECEIPT";
  group.tasks.push({
   taskId:item.id,metricId:item.metricId,metricName:item.metricName,
   metricWeightPercent:item.metricWeightPercent,sourceDate:item.sourceDate,
   sourceUrl:item.sourceUrl,benchmarkSourceUrl:item.benchmarkSourceUrl,
   sourceFingerprint:sourceFrozenFingerprint(item),receiptState,
   approvedMetricGrade:null,calibratedFdaProbability:null
  });
 }
 const groups=[...byProgram.values()];
 for(const group of groups){
  group.tasks.sort((a,b)=>a.metricId.localeCompare(b.metricId));
  group.provisionalMetrics=group.tasks.length;
  group.remainingStageMetrics=30-group.tasks.length;
  group.receiptPending=group.tasks.filter(t=>
   t.receiptState==="RECEIPT_PENDING_AUTHENTICATION").length;
  group.receiptBlocked=group.tasks.filter(t=>
   t.receiptState==="BLOCKED_RECEIPT").length;
  if(group.remainingStageMetrics<0)throw Error("RAAS_ASSIGNMENT_MORE_THAN_30_STAGE_METRICS");
 }
 groups.sort((a,b)=>priorityRank[a.priority]-priorityRank[b.priority]||
  a.ticker.localeCompare(b.ticker)||a.nctId.localeCompare(b.nctId)||
  a.stage.localeCompare(b.stage)||a.id.localeCompare(b.id));
 const sum=groups.reduce((n,g)=>n+g.provisionalMetrics,0);
 if(sum!==queue.total||sum!==uniqueTasks.size)
  throw Error("RAAS_ASSIGNMENT_COVERAGE_MISMATCH");
 return {scope:"RAAS_SOURCE_FROZEN_EXPERT_REVIEW_ASSIGNMENT_PLAN_NOT_APPROVAL",
  asOf:queue.asOf,totalPackets:sum,distinctPrograms:groups.length,
  fdaAcceptedPhase3Packets:queue.currentFdaPhase3Metrics,
  currentPhase3TopPackets:queue.currentTopPhase3Metrics,
  otherResearchPackets:queue.otherResearchMetrics,
  externallyAssignedReviewers:0,certifiedIndependentMetricSignoffs:0,
  submittedReceiptReferences:receipts.submitted,
  pendingReceiptAuthentication:receipts.pendingExternalAuthentication,
  blockedReceiptReferences:receipts.blocked,
  approvedStageScores:0,calibratedFdaForecasts:0,groups};
}
