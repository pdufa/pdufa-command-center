import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../lib/auth";
export const runtime="nodejs";
export const dynamic="force-dynamic";
export const maxDuration=20;
const headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"} as const;
const json=(body:unknown,status:number)=>NextResponse.json(body,{status,headers});

/** Read-only status; never starts an analysis on a page visit. */
export async function GET(req:NextRequest){
  if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return json({state:"AUTH_REQUIRED",note:"Sign in to view automatic-reassessment readiness."},401);
  const base=process.env.PDUFA_API_BASE_URL?.trim().replace(/\/$/,"");
  const key=process.env.PDUFA_INTERNAL_API_KEY?.trim();
  if(!base?.startsWith("https://")||!key)
    return json({state:"NOT_CONNECTED",note:"Durable medical backend is not connected."},503);
  try{
    const response=await fetch(base+"/api/news-automation/status",{method:"GET",cache:"no-store",
      redirect:"error",signal:AbortSignal.timeout(14000),headers:{"X-Pdufa-Internal-Key":key,Accept:"application/json"}});
    if(!response.ok||!response.headers.get("content-type")?.toLowerCase().includes("json"))
      return json({state:"NOT_VERIFIED",note:"Automatic news reassessment is not verified as operational."},503);
    const data:unknown=await response.json();
    if(!data||typeof data!=="object"||Array.isArray(data))
      return json({state:"NOT_VERIFIED",note:"Backend status was invalid."},503);
    const s=data as Record<string,unknown>;
    const statuses=s.statuses&&typeof s.statuses==="object"&&!Array.isArray(s.statuses)?s.statuses:{};
    return json({state:s.watchEnabled===true&&typeof s.lastCheckedAt==="string"?"RUNNING":"NOT_ENABLED",
      baselineAt:typeof s.baselineAt==="string"?s.baselineAt:null,
      lastCheckedAt:typeof s.lastCheckedAt==="string"?s.lastCheckedAt:null,
      statuses, reassessmentType:"SOURCE_COLLECTION_ONLY",modelDecision:"ABSTAIN"},200);
  }catch{
    return json({state:"NOT_VERIFIED",note:"Automatic news reassessment status unavailable; no run inferred."},503);
  }
}
