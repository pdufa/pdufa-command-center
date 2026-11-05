/** Download a fillable reviewer worksheet for exact NCT, with 60 unsigned metrics.
 * Source evidence and expected CSV columns share the validation contract.
 * EXTERNAL_AUTHENTICATION_REQUIRED on every row. No submissions, authenticated approvals or predictions are created.
 */
import registry from "../../../public/raas-registry-evidence-index.json";
import {buildTrialMetricReviewDossier}
 from "../../../lib/raas-trial-metric-review-dossier";
import {serializeReviewerWorksheet}
 from "../../../lib/raas-review-worksheet-preflight";
export const dynamic="force-dynamic";
export function GET(request:Request){
 const url=new URL(request.url);
 const nctId=url.searchParams.get("nctId")||"";
 const ticker=url.searchParams.get("ticker")||"";
 if(!/^NCT\d{8}$/.test(nctId)||!/^[A-Za-z0-9.\-]{1,20}$/.test(ticker))
  return Response.json({error:"INVALID_EXACT_TRIAL_IDENTITY"},{status:400});
 const docket=buildTrialMetricReviewDossier(registry,nctId,ticker);
 if(!docket)return Response.json({error:"EXACT_NCT_TICKER_NOT_IN_RESEARCH_SNAPSHOT"},
  {status:404});
 return new Response(serializeReviewerWorksheet(docket),{
  status:200,headers:{
   "Content-Type":"text/csv; charset=utf-8",
   "Content-Disposition":'attachment; filename="raas-unsigned-review-'+nctId+'.csv"',
   "Cache-Control":"no-store","X-Content-Type-Options":"nosniff"
  }
 });
}
