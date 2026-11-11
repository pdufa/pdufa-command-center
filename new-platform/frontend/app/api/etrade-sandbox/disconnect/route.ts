import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../../lib/auth";
import {ACCESS_COOKIE,REQUEST_COOKIE,readAccess,revokeSandboxToken} from "../../../../lib/etrade-sandbox-oauth";
export const runtime="nodejs";export const dynamic="force-dynamic";
export async function POST(req:NextRequest){
  const origin=req.headers.get("origin");
  if(!origin||origin!==req.nextUrl.origin)return NextResponse.json({error:"Origin not allowed"},{status:403});
  if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error:"Authentication required"},{status:401});
  const access=readAccess(req.cookies.get(ACCESS_COOKIE)?.value);
  if(access){
    try{await revokeSandboxToken(access);}
    catch{return NextResponse.json({error:"E*TRADE could not confirm sandbox token revocation. Retry disconnect."},
      {status:503,headers:{"Cache-Control":"private, no-store"}});}
  }
  const response=NextResponse.json({connected:false,mode:"SANDBOX",orderPlacementEnabled:false},
    {headers:{"Cache-Control":"private, no-store"}});
  response.cookies.delete({name:ACCESS_COOKIE,path:"/api/etrade-sandbox"});
  response.cookies.delete({name:REQUEST_COOKIE,path:"/api/etrade-sandbox"});
  return response;
}
