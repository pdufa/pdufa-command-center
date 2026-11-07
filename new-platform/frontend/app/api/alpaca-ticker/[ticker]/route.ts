import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Strictly authenticated, read-only ticker charts: keys never reach browsers.
export async function GET(req:NextRequest,context:{params:Promise<{ticker:string}>}){
 if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
  return NextResponse.json({error:"Authentication required"},{status:401});
 const {ticker}=await context.params;
 if(!/^[A-Z][A-Z0-9.-]{0,12}$/.test(ticker))
  return NextResponse.json({error:"Invalid ticker"},{status:422});
 const range=req.nextUrl.searchParams.get("range")||"6M";
 if(!["1M","3M","6M","1Y","ALL"].includes(range))
  return NextResponse.json({error:"Invalid chart range"},{status:422});
 const base=process.env.PDUFA_API_BASE_URL?.replace(/\/$/,"");
 const key=process.env.PDUFA_INTERNAL_API_KEY;
 if(!base||!/^https:\/\//.test(base)||!key)
  return NextResponse.json({error:"Backend not configured"},{status:503});
 try{
  const response=await fetch(base+"/api/alpaca-ticker/"+encodeURIComponent(ticker)+"?range="+encodeURIComponent(range),{
   headers:{"x-pdufa-internal-key":key},cache:"no-store",signal:AbortSignal.timeout(30000)
  });
  const data=await response.json().catch(()=>({error:"Alpaca response unavailable"}));
  return NextResponse.json(data,{status:response.status,headers:{"Cache-Control":"private, no-store"}});
 }catch{
  return NextResponse.json({error:"Alpaca market-data service unavailable"},{status:503});
 }
}
