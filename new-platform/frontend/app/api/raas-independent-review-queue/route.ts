/** Downloadable handoff for independent external review.
 * No approval, signature or trading advice is conveyed by CSV generation.
 */
import {buildRaasIndependentReviewQueue} from "../../../lib/raas-independent-review-queue";
const fields=[
 "priority","ticker","nctId","drug","indication","stage","metricId","metricName",
 "provisionalFinding","provisionalScore","metricWeightPercent","sourceDate",
 "assessedAt","sourceAsOf","sourceUrl","benchmarkSourceUrl","benchmarkId",
 "benchmarkContext","observedResult","uncertaintyReview","criticalRiskReview",
 "reviewState","applicationKey"
] as const;
function cell(value:unknown){
 const s=String(value??"");
 // Prevent spreadsheet formula execution; preserve all original evidence text.
 const safe=/^[\s]*[=+@-]/.test(s)?"'"+s:s;
 return '"'+safe.replaceAll('"','""')+'"';
}
export function GET(){
 const queue=buildRaasIndependentReviewQueue();
 const lines=[fields.join(","),...queue.items.map(row=>
  fields.map(f=>cell(row[f])).join(","))];
 const csv="\uFEFF"+lines.join("\r\n")+"\r\n";
 return new Response(csv,{status:200,headers:{
  "Content-Type":"text/csv; charset=utf-8",
  "Content-Disposition":'attachment; filename="raas-independent-metric-review-queue.csv"',
  "Cache-Control":"no-store",
  "X-Content-Type-Options":"nosniff"
 }});
}
