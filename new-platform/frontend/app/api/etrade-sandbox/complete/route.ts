import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../../lib/auth";
import {ACCESS_COOKIE,REQUEST_COOKIE,ACCESS_MAX_AGE,exchangeSandboxVerifier,
  readPending,sandboxConfigured,sealAccess} from "../../../../lib/etrade-sandbox-oauth";
export const runtime="nodejs";export const dynamic="force-dynamic";
export async function POST(req:NextRequest){
  const origin=req.headers.get("origin");
  if(!origin||origin!==req.nextUrl.origin)return NextResponse.json({error:"Origin not allowed"},{status:403});
  if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error:"Authentication required"},{status:401});
  if(!sandboxConfigured())return NextResponse.json({error:"Sandbox credentials not installed"},{status:503});
  const input=await req.json().catch(()=>({}));
  const verifier=typeof input.verifier==="string"?input.verifier.trim():"";
  if(!/^[A-Za-z0-9]{4,64}$/.test(verifier))
    return NextResponse.json({error:"Paste a valid E*TRADE authorization code"},{status:422});
  const pending=readPending(req.cookies.get(REQUEST_COOKIE)?.value);
  if(!pending)return NextResponse.json({error:"Sandbox authorization expired. Start again."},{status:409});
  try{
    const access=await exchangeSandboxVerifier(pending,verifier);
    const response=NextResponse.json({mode:"SANDBOX",connected:true,allowsProductionTrading:false,
      orderPlacementEnabled:false,brokerPreviewEnabled:false},
      {headers:{"Cache-Control":"private, no-store"}});
    response.cookies.set(ACCESS_COOKIE,sealAccess(access.token,access.secret),
      {httpOnly:true,secure:process.env.NODE_ENV==="production",sameSite:"strict",path:"/api/etrade-sandbox",maxAge:ACCESS_MAX_AGE});
    response.cookies.delete({name:REQUEST_COOKIE,path:"/api/etrade-sandbox"});
    return response;
  }catch{
    return NextResponse.json({error:"Sandbox token exchange rejected. Start a new authorization."},
      {status:502,headers:{"Cache-Control":"private, no-store"}});
  }
}
