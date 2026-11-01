import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../lib/auth";
import saved from "../../../data/benefit-assessment-research.json";
import {parseBenefitFeed} from "../../../lib/benefit-assessments";
import {benefitsFromPipeline} from "../../../lib/benefit-research-source";
import {loadCompleteResearch} from "../../../lib/pipeline-research-pagination";
import {pacificToday} from "../../../lib/pipeline-timeline";
import {GET as readScope} from "../scope-funnel/route";

export const runtime="nodejs";
export const dynamic="force-dynamic";
export const maxDuration=60;

/** Read the same authenticated, source-reconciled Pipeline dataset as the
 * existing research views. Never use unscreened POOL rows as a fallback.
 */
export async function GET(req:NextRequest){
  if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error:"Authentication required"},{status:401});
  try{
    const reviewed=parseBenefitFeed(saved);
    const complete=await loadCompleteResearch(async(offset,limit)=>{
      const url=new URL(req.url);
      url.pathname="/api/scope-funnel";
      url.search="";
      url.searchParams.set("view","pipeline");
      url.searchParams.set("offset",String(offset));
      url.searchParams.set("limit",String(limit));
      const response=await readScope(new NextRequest(url,{headers:req.headers}));
      if(!response.ok)throw Error("PIPELINE_RESEARCH_UNAVAILABLE");
      return response.json();
    });
    const feed=benefitsFromPipeline(complete.rows,pacificToday(),reviewed);
    return NextResponse.json(feed,{headers:{"Cache-Control":"private, no-store"}});
  }catch{
    return NextResponse.json({error:"Source-backed benefit research could not be reconciled; no research conclusions returned."},
      {status:503,headers:{"Cache-Control":"private, no-store"}});
  }
}
