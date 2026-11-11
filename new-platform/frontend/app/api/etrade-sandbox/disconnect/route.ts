import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../../lib/auth";
import {ACCESS_COOKIE,REQUEST_COOKIE} from "../../../../lib/etrade-sandbox-oauth";
export const runtime="nodejs";export const dynamic="force-dynamic";
export async function POST(req:NextRequest){
  const origin=req.headers.get("origin");
  if(!origin||origin!==req.nextUrl.origin)return NextResponse.json({error:"Origin not allowed"},{status:403});
  if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error:"Authentication required"},{status:401});
  const response=NextResponse.json({connected:false,mode:"SANDBOX",orderPlacementEnabled:false},
    {headers:{"Cache-Control":"private, no-store"}});
  response.cookies.delete({name:ACCESS_COOKIE,path:"/api/etrade-sandbox"});
  response.cookies.delete({name:REQUEST_COOKIE,path:"/api/etrade-sandbox"});
  return response;
}
