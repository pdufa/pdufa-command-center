/** Download exact 762-NCT current-stage metric research tasks as an audit CSV.
 * Source leads are ungraded; provisional findings are not certified RAAS scores.
 */
import savedRegistry from "../../../public/raas-registry-evidence-index.json";
import {parseRegistryEvidenceIndex} from "../../../lib/raas-registry-evidence";
import {buildRaas762AssignedReviewQueue,exportRaas762AssignedReviewCsv}
 from "../../../lib/raas-762-assigned-review-queue";

export const dynamic="force-dynamic";
export function GET(){
 try{
  const index=parseRegistryEvidenceIndex(savedRegistry);
  const queue=buildRaas762AssignedReviewQueue(index);
  return new Response(exportRaas762AssignedReviewCsv(queue),{
   status:200,headers:{
    "Content-Type":"text/csv; charset=utf-8",
    "Content-Disposition":'attachment; filename="raas-762-assigned-metric-reviews.csv"',
    "Cache-Control":"no-store",
    "X-Content-Type-Options":"nosniff"
   }
  });
 }catch{
  return Response.json({error:"SOURCE_RECONCILIATION_FAILED",scoresValidated:0},
   {status:503,headers:{"Cache-Control":"no-store"}});
 }
}
