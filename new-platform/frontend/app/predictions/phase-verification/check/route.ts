import {
  R85_PHASE_MANIFEST,compareR85CurrentRegistry
} from "../../../../lib/focus-r85-registry-phase-crosscheck";

/** Exact-NCT only, source-read-only ClinicalTrials.gov API comparison.
 * Do not expose the result as an authorized phase review or clinical score.
 */
export const runtime="nodejs";
export const dynamic="force-dynamic";
const H={
 "Cache-Control":"private, no-store, max-age=0",
 "X-Content-Type-Options":"nosniff"
} as const;
function error(status:number,code:string):Response{
 return Response.json({error:code,independentPhaseReview:"NOT_SIGNED",
  FDAForecast:"ABSTAIN"}, {status,headers:H});
}
export async function GET(request:Request):Promise<Response> {
 const manifest=R85_PHASE_MANIFEST;
 if(!manifest)return error(503,"ARCHIVED_RESEARCH_SOURCE_INTEGRITY_UNAVAILABLE");
 const query=new URL(request.url).searchParams;
 const nct=query.get("nct");
 if(!nct||!/^(?:NCT)\d{8}$/u.test(nct))return error(400,"EXACT_NCT_REQUIRED");
 const row=manifest.rows.find(r=>r.nct===nct);
 if(!row)return error(404,"NCT_NOT_IN_LOCKED_29_TRIAL_FOCUS_ROSTER");
 const sourceUrl="https://clinicaltrials.gov/api/v2/studies/"+row.nct+"?format=json";
 try {
  const response=await fetch(sourceUrl,{
   method:"GET",redirect:"error",cache:"no-store",
   headers:{"Accept":"application/json"},signal:AbortSignal.timeout(10000)
  });
  if(!response.ok)return error(502,"CURRENT_OFFICIAL_REGISTRY_UNAVAILABLE");
  const contentLength=Number(response.headers.get("content-length")??0);
  if(contentLength>2_000_000)return error(502,"CURRENT_REGISTRY_RESPONSE_TOO_LARGE");
  const body=await response.text();
  if(body.length>2_000_000)return error(502,"CURRENT_REGISTRY_RESPONSE_TOO_LARGE");
  const current:unknown=JSON.parse(body);
  const result=compareR85CurrentRegistry(row,current);
  if(!result)return error(502,"CURRENT_REGISTRY_IDENTITY_MISMATCH_OR_MALFORMED");
  return Response.json(result,{headers:H});
 }catch{
  return error(502,"CURRENT_OFFICIAL_REGISTRY_CHECK_FAILED");
 }
}
