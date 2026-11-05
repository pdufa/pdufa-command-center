/** Export nightly source change -> candidate RAAS metric tasks, never grades. */
import history from "../../../data/raas-registry-evidence-change-history.json";
import status from "../../../data/raas-registry-evidence-change-status.json";
import registry from "../../../public/raas-registry-evidence-index.json";
import {buildRaasRegistryRevisionReviewInbox}
 from "../../../lib/raas-registry-revision-review-inbox";
export const dynamic="force-dynamic";
const headers=[
 "nctId","ticker","metricId","metricName","metricStage","categoryName",
 "observedAt","firstObservedAt","eventId","revisionCountForMetric",
 "changeCategories","sourceUrl","previousSourceHash","newSourceHash",
 "currentRegistryHash","sourceMatch","matchingExistingProvisionalResearchReviews",
 "provisionalResearchIdentity","state","approvedRaasMetricGrade",
 "approvedRaasScore","calibratedFdaForecast"
] as const;
function cell(v:unknown):string{
 const value=String(v??"");
 return '"'+(/^\s*[=+@-]/.test(value)?"'"+value:value)
  .replaceAll('"','""')+'"';
}
export function GET(){
 const inbox=buildRaasRegistryRevisionReviewInbox(history,status,registry);
 const rows=inbox.tasks.map(x=>[
  x.nctId,x.ticker,x.metricId,x.metricName,x.metricStage,x.categoryName,
  x.observedAt,x.firstObservedAt,x.eventId,x.revisionCountForMetric,
  x.changeCategories.join("|"),x.sourceUrl,x.previousSourceHash,
  x.newSourceHash,x.currentRegistryHash,x.sourceMatch,
  x.matchingExistingProvisionalResearchReviews,x.provisionalResearchIdentity,
  x.state,"N/A","N/A","N/A"
 ]);
 const csv="\uFEFF"+headers.join(",")+"\r\n"+
  rows.map(r=>r.map(cell).join(",")).join("\r\n")+"\r\n";
 return new Response(csv,{status:200,headers:{
  "Content-Type":"text/csv; charset=utf-8",
  "Content-Disposition":'attachment; filename="raas-registry-source-metric-review-alerts.csv"',
  "Cache-Control":"no-store","X-Content-Type-Options":"nosniff"
 }});
}
