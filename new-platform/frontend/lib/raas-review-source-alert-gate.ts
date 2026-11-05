/** Research-only change-control gate for 30-metric external handoffs.
 * A clean saved audit is NOT proof that all clinical or FDA sources are current.
 * Any unresolved exact-NCT registry metric revision prevents a "no alerts"
 * handoff. Never promotes a metric, approved score or three-way FDA forecast.
 */
import {parseRegistryEvidenceIndex} from "./raas-registry-evidence";
import type {RaasReviewAssignmentPlan} from "./raas-review-assignment-plan";
import type {RaasRegistryRevisionReviewInbox} from "./raas-registry-revision-review-inbox";

export type RaasReviewSourceGate={
 programId:string;nctId:string;ticker:string;stage:"pre"|"post";
 status:"RECHECK_SOURCE_REVISIONS"|"SOURCE_AUDIT_INCOMPLETE_OR_UNSYNCED"|
  "NO_RECORDED_METRIC_REVISIONS";
 auditState:string;registryAsOf:string;registryLastUpdated:string|null;
 registrySourceHash:string|null;reviewFeedAsOf:string;
 sourceChangedMetricIds:string[];
 relevantRevisionAlertCount:number;supersededOrUnsyncedAlertCount:number;
 approvedRaasScore:null;calibratedFdaProbability:null;
 explanation:string;
};
export type RaasReviewSourceGateSummary={
 totalPrograms:number;needRevisionRecheck:number;sourceAuditUnconfirmed:number;
 noRecordedMetricRevisions:number;approvedRaasScores:0;
 calibratedFdaForecasts:0;gates:RaasReviewSourceGate[];
};
/** Accept only already integrity-validated inbox objects in production.
 * Fail closed against missing or mismatched snapshot/source identities.
 */
export function auditRaasReviewProgramSourceGates(
 plan:RaasReviewAssignmentPlan,inbox:RaasRegistryRevisionReviewInbox,
 rawRegistry:unknown
):RaasReviewSourceGateSummary{
 const registry=parseRegistryEvidenceIndex(rawRegistry);
 const byNct=new Map(registry.records.map(x=>[x.nctId,x]));
 if(registry.records.length!==762||
  inbox.registryAsOf!==registry.sourceAsOf&&inbox.auditState==="COMPLETE")
  throw Error("RAAS_SOURCE_GATE_REGISTRY_AUDIT_SNAPSHOT_MISMATCH");
 const gates=plan.groups.map((group):RaasReviewSourceGate=>{
  const original=byNct.get(group.nctId);
  const correctIdentity=!!original&&original.ticker.toUpperCase()===
   group.ticker.toUpperCase()&&
   original.sourceUrl==="https://clinicaltrials.gov/study/"+group.nctId;
  // Recheck any unresolved candidate metric, including one that has never
  // had a provisional research packet (30 stage requirements, not just 5).
  const alerts=inbox.tasks.filter(task=>
   task.nctId===group.nctId&&
   task.ticker.toUpperCase()===group.ticker.toUpperCase()&&
   task.metricStage===group.stage);
  const changedIds=[...new Set(alerts.map(x=>x.metricId))].sort();
  const unsynced=alerts.filter(x=>
   x.sourceMatch==="SOURCE_VERSION_SUPERSEDED_OR_UNSYNCED").length;
  const auditReady=correctIdentity&&inbox.auditState==="COMPLETE"&&
   inbox.registryAsOf===registry.sourceAsOf;
  const status:RaasReviewSourceGate["status"]=!auditReady?
   "SOURCE_AUDIT_INCOMPLETE_OR_UNSYNCED":
   changedIds.length?"RECHECK_SOURCE_REVISIONS":
   "NO_RECORDED_METRIC_REVISIONS";
  const explanation=status==="SOURCE_AUDIT_INCOMPLETE_OR_UNSYNCED"?
   "The saved official registry audit is incomplete, unsynced, or lacks this exact NCT/ticker. Reconcile source coverage before relying on the handoff.":
   status==="RECHECK_SOURCE_REVISIONS"?
   "Unresolved official registry source revisions affect this program stage. Independently recheck the exact metric evidence and any previous provisional packet before signing.":
   "No unresolved metric-level registry revisions were recorded in the saved comparison. This does not prove the evidence is current, complete, clinically verified, or FDA-confirmed.";
  return {
   programId:group.id,nctId:group.nctId,ticker:group.ticker,stage:group.stage,
   status,auditState:inbox.auditState,
   registryAsOf:registry.sourceAsOf,
   registryLastUpdated:correctIdentity?original!.registryLastUpdated:null,
   registrySourceHash:correctIdentity?original!.sourceHash:null,
   reviewFeedAsOf:group.sourceAsOf,sourceChangedMetricIds:changedIds,
   relevantRevisionAlertCount:alerts.length,
   supersededOrUnsyncedAlertCount:unsynced,
   approvedRaasScore:null,calibratedFdaProbability:null,explanation
  };
 });
 return {totalPrograms:gates.length,
  needRevisionRecheck:gates.filter(x=>
   x.status==="RECHECK_SOURCE_REVISIONS").length,
  sourceAuditUnconfirmed:gates.filter(x=>
   x.status==="SOURCE_AUDIT_INCOMPLETE_OR_UNSYNCED").length,
  noRecordedMetricRevisions:gates.filter(x=>
   x.status==="NO_RECORDED_METRIC_REVISIONS").length,
  approvedRaasScores:0,calibratedFdaForecasts:0,gates};
}
