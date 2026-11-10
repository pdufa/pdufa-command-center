import {createHash} from "node:crypto";
import {R92_CURRENT_PROTOCOL_RESULTS_ROSTER,inspectR92CurrentProtocolResults} from
 "../../../../../lib/focus-r92-protocol-results-crosswalk";

export const runtime="nodejs";
export const dynamic="force-dynamic";
const HEADERS={
 "Cache-Control":"private, no-store, max-age=0",
 "X-Content-Type-Options":"nosniff"
} as const;
const MAX_CHARS=4_000_000;
function fail(status:number,code:string){
 return Response.json({
  error:code,
  signedOriginalSAPsAuthenticated:0,
  independentEndpointAdjudications:0,
  historicalFDAAccuracyValidated:false,
  FDAForecast:"ABSTAIN"
 },{status,headers:HEADERS});
}
/** Current protocol-v-posted comparison only. No signoff or score writes. */
export async function GET(request:Request):Promise<Response>{
 const roster=R92_CURRENT_PROTOCOL_RESULTS_ROSTER;
 if(!roster)return fail(503,"ORIGINAL_SOURCE_ROSTER_CROSSWALK_INVALID");
 const nct=new URL(request.url).searchParams.get("nct")??"";
 if(!/^NCT\d{8}$/u.test(nct))return fail(400,"EXACT_NCT_REQUIRED");
 const row=roster.rows.find(x=>x.nct===nct);
 if(!row)return fail(404,"NCT_OUTSIDE_12_POSTED_REGISTRY_RESULT_SCOPE");
 const api="https://clinicaltrials.gov/api/v2/studies/"+row.nct+"?format=json";
 try{
  const resp=await fetch(api,{
   method:"GET",cache:"no-store",redirect:"error",
   headers:{"Accept":"application/json"},
   signal:AbortSignal.timeout(12000)
  });
  if(!resp.ok)return fail(502,"OFFICIAL_PUBLIC_ORIGINAL_SOURCE_UNAVAILABLE");
  const length=Number(resp.headers.get("content-length")??0);
  if(!Number.isFinite(length)||length>MAX_CHARS)
   return fail(502,"OFFICIAL_SOURCE_TOO_LARGE");
  const text=await resp.text();
  if(text.length>MAX_CHARS)return fail(502,"OFFICIAL_SOURCE_TOO_LARGE");
  const original:unknown=JSON.parse(text);
  const result=inspectR92CurrentProtocolResults(row,original);
  if(!result)return fail(502,"CURRENT_PROTOCOL_OR_RESULT_IDENTITY_SCHEMA_INVALID");
  const responseSha256=createHash("sha256").update(text,"utf8").digest("hex");
  return Response.json({
   ...result,
   currentOriginalApiSha256:responseSha256,
   currentOriginalSourceMatchesR91Receipt:
    responseSha256===row.datedOriginalResultsSHA256,
   archiveOriginalSourceSha256:row.datedOriginalResultsSHA256,
   originalSourceApiUrl:api,
   retrievedAtUtc:new Date().toISOString(),
   independentClinicalEndPointJudgments:0,
   signedProspectiveSAPsConfirmed:0,
   FDAForecast:"ABSTAIN" as const
  },{headers:HEADERS});
 }catch{
  return fail(502,"OFFICIAL_ORIGINAL_SOURCE_LOOKUP_FAILED");
 }
}
