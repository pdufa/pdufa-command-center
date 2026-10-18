import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest, context: {params:Promise<{programId:string}>}) {
  if(!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error:"Authentication required"},{status:401});
  const {programId}=await context.params;
  if(!/^PDUFA-[0-9]{6,}$/.test(programId))
    return NextResponse.json({error:"Invalid Program ID"},{status:422});
  const base=process.env.PDUFA_API_BASE_URL?.replace(/\/$/,"");
  const key=process.env.PDUFA_INTERNAL_API_KEY;
  if(!base||!/^https:\/\//.test(base)||!key)
    return NextResponse.json({error:"Backend not configured"},{status:503});
  try {
    const response=await fetch(base+"/api/exit-signal/"+encodeURIComponent(programId),{
      headers:{"x-pdufa-internal-key":key},
      cache:"no-store",signal:AbortSignal.timeout(30000)});
    const data=await response.json();
    return NextResponse.json(data,{status:response.status,
      headers:{"Cache-Control":"private, no-store"}});
  } catch {
    return NextResponse.json({error:"Exit check currently unavailable"},{status:503});
  }
}
