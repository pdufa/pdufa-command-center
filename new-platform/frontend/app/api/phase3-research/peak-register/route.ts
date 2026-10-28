import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../../lib/auth";
import {hopBackendBase} from "../../../../lib/hop-backend";
import {fetchReadOnlyWithWarmRetry} from "../../../../lib/read-only-warm-retry";
import {validatePeakResearchView} from "../../../../lib/peak-research-view";
export const runtime="nodejs";
export const dynamic="force-dynamic";
export const maxDuration=60;
const headers={"Cache-Control":"private, no-store"};
export async function GET(req:NextRequest){
 if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))return NextResponse.json({error:"Authentication required"},{status:401,headers});
 const base=hopBackendBase(),key=process.env.PDUFA_HOP_INTERNAL_API_KEY??process.env.PDUFA_INTERNAL_API_KEY;
 if(!base||!key)return NextResponse.json({error:"Research source is not configured"},{status:503,headers});
 try{
  const response=await fetchReadOnlyWithWarmRetry(base+"/api/internal/phase3-research/peak-register",{headers:{"x-pdufa-internal-key":key},cache:"no-store",redirect:"error",signal:AbortSignal.timeout(45000)});
  if(!response.ok)throw new Error("unavailable");
  return NextResponse.json(validatePeakResearchView(await response.json()),{headers});
 }catch{return NextResponse.json({error:"Research evidence could not be verified; counts withheld"},{status:503,headers});}
}
