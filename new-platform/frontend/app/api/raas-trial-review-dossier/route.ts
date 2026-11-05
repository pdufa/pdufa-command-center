/** Read-only, exact-trial downloadable 60-metric research docket.
 * No sign-off intake, human certification, scores or forecasts are created.
 */
import registry from "../../../public/raas-registry-evidence-index.json";
import {buildTrialMetricReviewDossier}
 from "../../../lib/raas-trial-metric-review-dossier";
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
 return new Response(JSON.stringify(docket,null,2)+"\n",{
  status:200,headers:{
   "Content-Type":"application/json; charset=utf-8",
   "Content-Disposition":'attachment; filename="raas-60-metric-'+nctId+'-review-docket.json"',
   "Cache-Control":"no-store","X-Content-Type-Options":"nosniff"
  }
 });
}
