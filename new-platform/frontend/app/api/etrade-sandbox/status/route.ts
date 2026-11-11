import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../../lib/auth";
import {ACCESS_COOKIE,readAccess,sandboxConfigured} from "../../../../lib/etrade-sandbox-oauth";
export const runtime="nodejs";export const dynamic="force-dynamic";
export async function GET(req:NextRequest){
  if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error:"Authentication required"},{status:401});
  return NextResponse.json({mode:"SANDBOX",configured:sandboxConfigured(),
    connected:Boolean(readAccess(req.cookies.get(ACCESS_COOKIE)?.value)),
    allowsProductionTrading:false,orderPlacementEnabled:false,brokerPreviewEnabled:false},
    {headers:{"Cache-Control":"private, no-store"}});
}
