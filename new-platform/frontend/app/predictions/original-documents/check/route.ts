import {
 R86_ORIGINAL_DOCUMENT_MANIFEST,inspectR86CurrentStudy
} from "../../../../lib/focus-r86-original-document-inventory";

/** Exact, locked NCT to official ClinicalTrials.gov. GET-only, fail-closed. */
export const runtime="nodejs";
export const dynamic="force-dynamic";
const HEADERS={
 "Cache-Control":"private, no-store, max-age=0",
 "X-Content-Type-Options":"nosniff"
} as const;
function fail(status:number,code:string):Response{
 return Response.json({
  error:code,sourceEvidenceNotAdjudicated:true,
  signedSAPVersionsAuthenticated:0,independentFDAForecast:"ABSTAIN"
 },{status,headers:HEADERS});
}
export async function GET(request:Request):Promise<Response>{
 const source=R86_ORIGINAL_DOCUMENT_MANIFEST;
 if(!source)return fail(503,"LOCKED_ORIGINAL_RESEARCH_SOURCE_UNAVAILABLE");
 const nct=new URL(request.url).searchParams.get("nct");
 if(!nct||!/^NCT\d{8}$/u.test(nct))return fail(400,"EXACT_NCT_REQUIRED");
 const row=source.rows.find(r=>r.nct===nct);
 if(!row)return fail(404,"NCT_NOT_IN_LOCKED_FOCUS_ROSTER");
 try{
  const upstream=await fetch(
   "https://clinicaltrials.gov/api/v2/studies/"+row.nct+"?format=json",{
    method:"GET",redirect:"error",cache:"no-store",
    headers:{"Accept":"application/json"},signal:AbortSignal.timeout(10000)
   });
  if(!upstream.ok)return fail(502,"OFFICIAL_REGISTRY_UNAVAILABLE");
  const length=Number(upstream.headers.get("content-length")??0);
  if(!Number.isFinite(length)||length>2_000_000)return fail(502,"REGISTRY_RESPONSE_TOO_LARGE");
  const raw=await upstream.text();
  if(raw.length>2_000_000)return fail(502,"REGISTRY_RESPONSE_TOO_LARGE");
  const body:unknown=JSON.parse(raw);
  const result=inspectR86CurrentStudy(row,body);
  if(!result)return fail(502,"REGISTRY_SOURCE_IDENTITY_OR_STRUCTURE_INVALID");
  return Response.json(result,{headers:HEADERS});
 }catch{
  return fail(502,"OFFICIAL_REGISTRY_LOOKUP_FAILED");
 }
}
