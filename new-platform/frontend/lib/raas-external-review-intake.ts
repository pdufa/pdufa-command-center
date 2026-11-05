/** Research-only, source-frozen independent-review packet and receipt intake.
 * A matching receipt means a DOCUMENT was submitted, not that an independent
 * reviewer's identity, independence, signature, or clinical conclusions were
 * authenticated. Nothing in this module can approve RAAS/FDA predictions.
 */
import {createHash} from "node:crypto";
import type {RaasReviewQueueItem} from "./raas-independent-review-queue";
import {buildRaasIndependentReviewQueue} from "./raas-independent-review-queue";
import type {RaasProvisionalFinding} from "./raas-provisional-rubric-engine";
import receiptData from "../data/raas-external-review-receipts.json";

const hash=(s:string)=>createHash("sha256").update(s,"utf8").digest("hex");
const date=(x:unknown):x is string=>typeof x==="string"&&
 /^\d{4}-\d{2}-\d{2}$/.test(x)&&
 !Number.isNaN(Date.parse(x+"T00:00:00Z"))&&
 new Date(x+"T00:00:00Z").toISOString().slice(0,10)===x;
const nonempty=(x:unknown,min:number,max:number)=>typeof x==="string"&&
 x.trim().length>=min&&x.length<=max;
const sha=(x:unknown)=>typeof x==="string"&&/^[a-f0-9]{64}$/.test(x);

/** Fingerprint binds the full exact-program identity, stage, scored finding,
 * primary source and independent benchmark, uncertainty and risk statements.
 * Later changed source evidence requires a fresh reviewer packet.
 * The checksum is an integrity reference, NOT verification of source truth.
 */
export function sourceFrozenFingerprint(item:RaasReviewQueueItem):string{
 return hash(JSON.stringify({
  version:"raas-human-review-packet-2026-11-04-v1",
  id:item.id,nctId:item.nctId,ticker:item.ticker,drug:item.drug,
  indication:item.indication,stage:item.stage,metricId:item.metricId,
  sourceAsOf:item.sourceAsOf,assessedAt:item.assessedAt,
  sourceDate:item.sourceDate,sourceUrl:item.sourceUrl,
  benchmarkSourceUrl:item.benchmarkSourceUrl,benchmarkId:item.benchmarkId,
  benchmarkContext:item.benchmarkContext,observedResult:item.observedResult,
  uncertaintyReview:item.uncertaintyReview,criticalRiskReview:item.criticalRiskReview,
  provisionalFinding:item.provisionalFinding,provisionalScore:item.provisionalScore
 }));
}
export type RaasExternalReviewReceipt={
 receiptId:string;taskId:string;sourceFingerprint:string;
 reviewerReference:string;reviewerAffiliation:string;
 reviewedOn:string;decision:"CONFIRM"|"REVISE"|"REJECT";
 proposedFinding:RaasProvisionalFinding|null;
 rationale:string;conflicts:"NONE_DECLARED"|"DISCLOSED_REQUIRES_REVIEW";
 signedArtifactSha256:string;artifactReference:string;
 attestation:string;
};
export type RaasReceiptFeed={
 schemaVersion:1;scope:"RAAS_EXTERNAL_REVIEW_RECEIPTS_UNAUTHENTICATED_INTAKE";
 note:string;records:RaasExternalReviewReceipt[];
};
export type RaasReceiptCheck={
 receiptId:string;taskId:string;
 status:"INTAKE_COMPLETE_PENDING_EXTERNAL_AUTHENTICATION"|"BLOCKED";
 reasons:string[];
};
export function auditRaasExternalReviewReceipts(
 feed:unknown,items:readonly RaasReviewQueueItem[]
):{submitted:number;pendingExternalAuthentication:number;blocked:number;
 certifiedIndependentSignoffs:0;approvedRaasScores:0;calibratedFdaForecasts:0;
 checks:RaasReceiptCheck[]}{
 const doc=feed as RaasReceiptFeed;
 if(!doc||doc.schemaVersion!==1||
  doc.scope!=="RAAS_EXTERNAL_REVIEW_RECEIPTS_UNAUTHENTICATED_INTAKE"||
  !Array.isArray(doc.records)||doc.records.length>50000)
  throw Error("RAAS_REVIEW_RECEIPT_LEDGER_INVALID");
 const map=new Map(items.map(i=>[i.id,i]));
 if(map.size!==items.length)throw Error("RAAS_REVIEW_RECEIPT_DUPLICATE_TASK");
 const usedIds=new Set<string>();
 const usedReviewerTask=new Set<string>();
 const checks=doc.records.map((r,index):RaasReceiptCheck=>{
  const reasons:string[]=[];
  const receiptId=typeof r?.receiptId==="string"?r.receiptId:"INVALID-"+index;
  const taskId=typeof r?.taskId==="string"?r.taskId:"";
  const item=map.get(taskId);
  if(!nonempty(receiptId,8,120)||usedIds.has(receiptId))reasons.push("DUPLICATE_OR_INVALID_RECEIPT_ID");
  usedIds.add(receiptId);
  if(!item)reasons.push("UNKNOWN_EXACT_TRIAL_AND_METRIC");
  else if(r?.sourceFingerprint!==sourceFrozenFingerprint(item))
   reasons.push("SOURCE_VERSION_CHANGED_OR_MISMATCHED");
  if(!nonempty(r?.reviewerReference,3,120))reasons.push("MISSING_REVIEWER_REFERENCE");
  if(!nonempty(r?.reviewerAffiliation,3,200))reasons.push("MISSING_REVIEWER_AFFILIATION");
  const identity=taskId+"|"+(typeof r?.reviewerReference==="string"?
   r.reviewerReference.trim().toLowerCase():"");
  if(usedReviewerTask.has(identity))reasons.push("DUPLICATE_REVIEWER_ON_TASK");
  usedReviewerTask.add(identity);
  if(!date(r?.reviewedOn)||(item&&r.reviewedOn<item.assessedAt))
   reasons.push("INVALID_OR_PRE_ASSESSMENT_REVIEW_DATE");
  if(!["CONFIRM","REVISE","REJECT"].includes(r?.decision))
   reasons.push("INVALID_DECISION");
  const allowed=["MATERIAL_ADVERSE","BELOW_BENCHMARK","MIXED_EVIDENCE",
   "ABOVE_BENCHMARK","EXCEPTIONAL_EVIDENCE"];
  if(r?.decision==="REVISE"?!allowed.includes(r.proposedFinding as string):
   r?.decision==="CONFIRM"?!item||r.proposedFinding!==item.provisionalFinding:
   r?.proposedFinding!==null)
   reasons.push("INVALID_PROPOSED_FINDING");
  if(!nonempty(r?.rationale,80,8000))reasons.push("INSUFFICIENT_REVIEW_RATIONALE");
  if(!["NONE_DECLARED","DISCLOSED_REQUIRES_REVIEW"].includes(r?.conflicts))
   reasons.push("MISSING_CONFLICT_DECLARATION");
  if(!sha(r?.signedArtifactSha256))reasons.push("INVALID_SIGNED_DOCUMENT_DIGEST");
  if(!nonempty(r?.artifactReference,12,400))
   reasons.push("MISSING_SECURE_ARCHIVE_REFERENCE");
  if(!nonempty(r?.attestation,50,4000))
   reasons.push("MISSING_REVIEWER_ATTESTATION");
  return {receiptId,taskId,status:reasons.length?
   "BLOCKED":"INTAKE_COMPLETE_PENDING_EXTERNAL_AUTHENTICATION",reasons};
 });
 return {submitted:checks.length,
  pendingExternalAuthentication:checks.filter(x=>
   x.status==="INTAKE_COMPLETE_PENDING_EXTERNAL_AUTHENTICATION").length,
  blocked:checks.filter(x=>x.status==="BLOCKED").length,
  certifiedIndependentSignoffs:0,approvedRaasScores:0,calibratedFdaForecasts:0,checks};
}
export function currentReviewIntakeAudit(){
 return auditRaasExternalReviewReceipts(receiptData,buildRaasIndependentReviewQueue().items);
}
export function frozenReviewPacket(taskId:string){
 const item=buildRaasIndependentReviewQueue().items.find(x=>x.id===taskId);
 if(!item)return null;
 const fingerprint=sourceFrozenFingerprint(item);
 return {
  schemaVersion:1,scope:"RAAS_EXACT_METRIC_SOURCE_FROZEN_EXTERNAL_REVIEW_PACKET",
  createdFromSourceAsOf:item.sourceAsOf,
  sourceFingerprint:fingerprint,task:item,
  reviewInstructions:[
   "Use an independent human reviewer with verified professional identity and conflicts policy.",
   "Recheck the exact NCT, therapy, indication, stage, dated source and comparator.",
   "Reproduce effect estimates, uncertainties, controls, safety and conflicting evidence.",
   "Document corrections, conflicts and the signed artifact in a restricted evidence archive.",
   "Submit only a structured receipt reference through a reviewed repository change; do not commit private personal data or raw signed documents to this public repository.",
   "A completed receipt is STILL not a certified independent sign-off until an administrator verifies reviewer identity, independence, authentic signature and evidence; no metric or FDA probability is automatically approved."
  ],
  receiptDraft:{
   receiptId:"",taskId:item.id,sourceFingerprint:fingerprint,
   reviewerReference:"",reviewerAffiliation:"",reviewedOn:"",
   decision:"",proposedFinding:null,rationale:"",
   conflicts:"",signedArtifactSha256:"",artifactReference:"",
   attestation:""
  },
  status:"UNSIGNED_TEMPLATE_NOT_VALIDATED",
  approvedRaasScore:null,calibratedFdaProbability:null
 };
}
