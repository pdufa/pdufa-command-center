import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../../lib/auth";
import {isolatedMedicalBackend} from "../../../../lib/medical-review-matrix";
import {validatePilotMethodAudit} from "../../../../lib/medical-method-audit";

export const runtime="nodejs";
export const dynamic="force-dynamic";
const headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"};
const json=(body:unknown,status=200)=>NextResponse.json(body,{status,headers});

function authenticated(req:NextRequest){
  return authConfigured()&&hasSession(req.cookies.get(COOKIE_NAME)?.value);
}
function baseAndKey(method:"GET"|"POST"){
  const base=isolatedMedicalBackend(process.env.PDUFA_MEDICAL_REVIEW_API_BASE_URL);
  const key=method==="GET"?
    (process.env.PDUFA_MEDICAL_REVIEW_READ_KEY??
     process.env.PDUFA_MEDICAL_INTERNAL_API_KEY??process.env.PDUFA_INTERNAL_API_KEY):
    (process.env.PDUFA_MEDICAL_INTERNAL_API_KEY??process.env.PDUFA_INTERNAL_API_KEY);
  return {base,key};
}
async function proxy(method:"GET"|"POST",nct:string){
  const {base,key}=baseAndKey(method);
  if(!base||!key)return json({error:"Isolated 800-position pilot source audit not configured"},503);
  try{
    const resource=base+"/api/internal/medical-method-audit/"+nct+
      (method==="GET"?"/latest":"/runs");
    const response=await fetch(resource,{
      method,headers:{"x-pdufa-internal-key":key,Accept:"application/json"},
      redirect:"error",cache:"no-store",signal:AbortSignal.timeout(15000)
    });
    if(!response.headers.get("content-type")?.includes("json"))throw Error("INVALID_TYPE");
    const body=await response.text();
    if(body.length>120_000)throw Error("OVERSIZED_STATUS");
    const decoded:unknown=JSON.parse(body);
    if(response.status===404&&method==="GET"&&
      decoded&&typeof decoded==="object"&&!Array.isArray(decoded)&&
      (decoded as {detail?:unknown}).detail==="No recorded pilot audit")
      return json({kind:"NO_RUN",nct,auditKind:"SAVED_TRIAGE_SOURCE_CLASSIFICATION_VERIFICATION"});
    if(!response.ok){
      const msg=decoded&&typeof decoded==="object"&&!Array.isArray(decoded)?
        (decoded as {detail?:unknown}).detail:null;
      return json({error:response.status===409?"Saved 800-position triage is required":
        typeof msg==="string"&&response.status===422?msg:
        "Isolated pilot audit route unavailable or not enabled"},response.status===409?409:503);
    }
    const audited=validatePilotMethodAudit(decoded);
    if(audited.nct!==nct)throw Error("WRONG_TRIAL_AUDIT");
    return json(audited);
  }catch{
    return json({error:"Live 800-method source audit status cannot be authenticated or verified"},503);
  }
}
export async function GET(req:NextRequest){
  if(!authenticated(req))return json({error:"Sign in required"},401);
  const nct=req.nextUrl.searchParams.get("nct");
  if(nct!=="NCT06081894")return json({error:"Pilot restricted to ACACIA-HCM NCT06081894"},422);
  return proxy("GET",nct);
}
export async function POST(req:NextRequest){
  if(!authenticated(req))return json({error:"Sign in required"},401);
  if(req.headers.get("origin")!==req.nextUrl.origin)
    return json({error:"Same-origin operator action required"},403);
  const nct=req.nextUrl.searchParams.get("nct");
  if(nct!=="NCT06081894")return json({error:"Pilot restricted to ACACIA-HCM NCT06081894"},422);
  if(Number(req.headers.get("content-length")||0)>128)
    return json({error:"Unexpected request payload"},413);
  // A click starts only an additive source-classification audit, not a new
  // trial evidence fetch, FDA prediction, scientific grade or clinical review.
  return proxy("POST",nct);
}
