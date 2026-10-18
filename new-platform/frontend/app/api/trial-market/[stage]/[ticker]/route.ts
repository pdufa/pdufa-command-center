import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../../../lib/auth";
export const runtime="nodejs";
export const dynamic="force-dynamic";
export async function GET(req:NextRequest,context:{params:Promise<{stage:string;ticker:string}>}){
  if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error:"Authentication required"},{status:401});
  const {stage,ticker}=await context.params;
  if(!["GEM","GEM_JR"].includes(stage)||!/^[A-Z][A-Z0-9.-]{0,12}$/.test(ticker))
    return NextResponse.json({error:"Invalid GEM stage or ticker"},{status:422});
  const feed=req.nextUrl.searchParams.get("feed")||"sip";
  if(!["sip","iex"].includes(feed))
    return NextResponse.json({error:"Invalid market feed"},{status:422});
  const base=process.env.PDUFA_API_BASE_URL?.replace(/\/$/,"");
  const key=process.env.PDUFA_INTERNAL_API_KEY;
  if(!base||!/^https:\/\//.test(base)||!key)
    return NextResponse.json({error:"Backend not configured"},{status:503});
  try{
    const url=base+"/api/trial-market/"+stage+"/"+encodeURIComponent(ticker)+"?feed="+feed;
    const response=await fetch(url,{headers:{"x-pdufa-internal-key":key},
      cache:"no-store",signal:AbortSignal.timeout(30000)});
    const data=await response.json().catch(()=>({}));
    return NextResponse.json(data,{status:response.status,
      headers:{"Cache-Control":"private, no-store"}});
  }catch{
    return NextResponse.json({error:"Alpaca trial data temporarily unavailable"},{status:503});
  }
}
