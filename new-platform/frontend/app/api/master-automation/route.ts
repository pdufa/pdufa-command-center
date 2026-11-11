import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({error:"Unauthorized"},{status:401});
  }
  const base=process.env.PDUFA_API_BASE_URL?.replace(/\/$/,"");
  const key=process.env.PDUFA_INTERNAL_API_KEY;
  if(!base || !/^https:\/\//.test(base) || !key) {
    return NextResponse.json({error:"Controller backend not configured"},{status:503});
  }
  try {
    const response=await fetch(base+"/api/master-automation",{
      cache:"no-store",
      headers:{"x-pdufa-internal-key":key},
      signal:AbortSignal.timeout(20000)
    });
    const data=await response.json().catch(()=>({error:"Unparseable controller response"}));
    return NextResponse.json(data,{
      status:response.status,headers:{"Cache-Control":"private, no-store"}
    });
  }catch{
    return NextResponse.json({error:"Controller status unavailable; no stage was started"},{status:503});
  }
}
