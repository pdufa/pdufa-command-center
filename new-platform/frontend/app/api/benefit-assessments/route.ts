import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../lib/auth";
import saved from "../../../data/benefit-assessment-research.json";
import {parseBenefitFeed} from "../../../lib/benefit-assessments";
export const dynamic="force-dynamic";
/** Verified published research only. A null/empty feed is not evidence of zero advantages. */
export function GET(req:NextRequest){
  if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error:"Authentication required"},{status:401});
  try {
    const feed=parseBenefitFeed(saved);
    return NextResponse.json(feed,{headers:{"Cache-Control":"private, no-store"}});
  }catch{
    return NextResponse.json({error:"Research feed could not be verified"},{status:503,headers:{"Cache-Control":"private, no-store"}});
  }
}
