import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../../lib/auth";
import {REQUEST_COOKIE,OAUTH_REQUEST_MAX_AGE,authorizeSandboxUrl,requestSandboxToken,
  sandboxConfigured,sealPending} from "../../../../lib/etrade-sandbox-oauth";
export const runtime="nodejs";export const dynamic="force-dynamic";
export async function GET(req:NextRequest){
  if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error:"Authentication required"},{status:401});
  if(!sandboxConfigured())return NextResponse.json({error:"Sandbox E*TRADE keys are not configured on the server"},
    {status:503,headers:{"Cache-Control":"private, no-store"}});
  try{
    const token=await requestSandboxToken();
    const response=NextResponse.redirect(authorizeSandboxUrl(token.token),{status:302});
    response.cookies.set(REQUEST_COOKIE,sealPending(token.token,token.secret),
      {httpOnly:true,secure:process.env.NODE_ENV==="production",sameSite:"lax",path:"/api/etrade-sandbox",maxAge:OAUTH_REQUEST_MAX_AGE});
    response.headers.set("Cache-Control","private, no-store");
    return response;
  }catch{
    return NextResponse.json({error:"Sandbox authorization could not be started; verify E*TRADE developer credentials"},
      {status:502,headers:{"Cache-Control":"private, no-store"}});
  }
}
