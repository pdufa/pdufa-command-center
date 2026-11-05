/** Reviewer assignment manifest, one source-frozen row per provisional metric.
 * CSV contains no reviewer identity, signed artifact or clinical approval.
 */
import {buildRaasReviewAssignmentPlan}
 from "../../../lib/raas-review-assignment-plan";
export const dynamic="force-dynamic";
const columns=[
 "priority","ticker","nctId","drug","indication","stage",
 "applicationKey","metricId","metricName","metricWeightPercent",
 "sourceAsOf","sourceDate","sourceUrl","benchmarkSourceUrl",
 "sourceFingerprint","exactPacketDownloadPath",
 "receiptState","assignmentState","approvedMetricGrade",
 "approvedStageScore","calibratedFdaForecast"
] as const;
const cell=(value:unknown)=>{
 const input=String(value??"");
 const safe=/^\s*[=+@-]/.test(input)?"'"+input:input;
 return '"'+safe.replaceAll('"','""')+'"';
};
export function GET(){
 const plan=buildRaasReviewAssignmentPlan();
 const rows=plan.groups.flatMap(group=>group.tasks.map(task=>[
  group.priority,group.ticker,group.nctId,group.drug,group.indication,
  group.stage,group.applicationKey,task.metricId,task.metricName,
  task.metricWeightPercent,group.sourceAsOf,task.sourceDate,
  task.sourceUrl,task.benchmarkSourceUrl,task.sourceFingerprint,
  "/api/raas-independent-review-packet?task="+encodeURIComponent(task.taskId),
  task.receiptState,"UNASSIGNED","N/A","N/A","N/A"
 ]));
 if(rows.length!==plan.totalPackets)throw Error("RAAS_ASSIGNMENT_MANIFEST_COUNT_MISMATCH");
 const csv="\uFEFF"+columns.join(",")+"\r\n"+
  rows.map(row=>row.map(cell).join(",")).join("\r\n")+"\r\n";
 return new Response(csv,{status:200,headers:{
  "Content-Type":"text/csv; charset=utf-8",
  "Content-Disposition":'attachment; filename="raas-independent-review-assignment-manifest.csv"',
  "Cache-Control":"no-store","X-Content-Type-Options":"nosniff"
 }});
}
