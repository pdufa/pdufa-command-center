import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../lib/auth";
export const runtime="nodejs";
export const dynamic="force-dynamic";
export async function GET(req:NextRequest) {
  if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error:"Authentication required"},{status:401});
  const base=process.env.PDUFA_API_BASE_URL?.replace(/\/$/,"");
  const key=process.env.PDUFA_INTERNAL_API_KEY;
  if(!base||!/^https:\/\//.test(base)||!key)
    return NextResponse.json({error:"Backend not configured"},{status:503});
  try{
    const r=await fetch(base+"/api/trial-source-workspace",{
      headers:{"x-pdufa-internal-key":key},cache:"no-store",signal:AbortSignal.timeout(30000)});
    const data=await r.json().catch(()=>({}));
    return NextResponse.json(data,{status:r.status,
      headers:{"Cache-Control":"private, no-store"}});
  }catch{
    return NextResponse.json({error:"Read-only trial inventory unavailable"},{status:503});
  }
}
