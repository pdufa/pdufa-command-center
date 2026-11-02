import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../lib/auth";
import {verifiedReadoutSurveyFeed} from "../../../lib/phase3-survey-source";
import research from "../../../data/phase3-readout-survey-research.json";
import manifest from "../../../public/phase3-public-readout-evidence-2026-11-01.json";

export const runtime="nodejs";
export const dynamic="force-dynamic";

/** Exact-NCT, issuer-reported source observations for documented Phase 3
 * public readouts only. Never a PDUFA-qualified Pipeline or clinical score.
 */
export async function GET(req:NextRequest){
 if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
  return NextResponse.json({error:"Authentication required"},
   {status:401,headers:{"Cache-Control":"private, no-store"}});
 try{
  const feed=verifiedReadoutSurveyFeed(research,manifest);
  return NextResponse.json(feed,{headers:{"Cache-Control":"private, no-store"}});
 }catch{
  return NextResponse.json({error:"Issuer readout research failed exact-trial source verification."},
   {status:503,headers:{"Cache-Control":"private, no-store"}});
 }
}
