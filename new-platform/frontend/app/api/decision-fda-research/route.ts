import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../lib/auth";
import {retrieveDrugsFdaApplication} from "../../../lib/decision-openfda-client";
export const runtime="nodejs";export const dynamic="force-dynamic";
/** Authenticated, read-only research lookup; never assigns FDA outcomes or trade signals. */
export async function GET(req:NextRequest){
 if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))return NextResponse.json({error:"Authentication required"},{status:401,headers:{"Cache-Control":"private, no-store"}});
 const application=req.nextUrl.searchParams.get("application")||"";
 if(!/^(NDA|BLA|ANDA)\d{6}$/i.test(application))return NextResponse.json({error:"Valid FDA application number required"},{status:422,headers:{"Cache-Control":"private, no-store"}});
 const result=await retrieveDrugsFdaApplication(application);
 return NextResponse.json(result,{status:result.status==="NOT_READY"?503:200,headers:{"Cache-Control":"private, no-store"}});
}
