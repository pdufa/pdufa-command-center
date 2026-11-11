import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../../lib/auth";
import {ACCESS_COOKIE,listSandboxAccounts,readAccess} from "../../../../lib/etrade-sandbox-oauth";
export const runtime="nodejs";export const dynamic="force-dynamic";
export async function GET(req:NextRequest){
  if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error:"Authentication required"},{status:401});
  const access=readAccess(req.cookies.get(ACCESS_COOKIE)?.value);
  if(!access)return NextResponse.json({error:"Sandbox authorization required"},{status:401});
  try{
    const accounts=await listSandboxAccounts(access);
    return NextResponse.json({mode:"SANDBOX",accounts,liveAccounts:false,orderPlacementEnabled:false},
      {headers:{"Cache-Control":"private, no-store"}});
  }catch{
    return NextResponse.json({error:"Sandbox account listing unavailable; reauthorize if session is inactive"},
      {status:503,headers:{"Cache-Control":"private, no-store"}});
  }
}
