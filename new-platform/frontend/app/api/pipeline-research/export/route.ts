import { NextRequest, NextResponse } from "next/server";
import { GET as readScope } from "../../scope-funnel/route";
import { canonicalResearchPage } from "../../../../lib/pipeline-research-export";
import { pacificToday } from "../../../../lib/pipeline-timeline";
export const runtime="nodejs";
export const dynamic="force-dynamic";
export const maxDuration=60;
export async function GET(req:NextRequest){
 const url=new URL(req.url);url.pathname="/api/scope-funnel";url.searchParams.set("view","pipeline");
 const upstream=await readScope(new NextRequest(url,{headers:req.headers}));
 if(!upstream.ok)return upstream;
 const raw=await upstream.json();
 if(!/^[a-f0-9]{64}$/.test(raw.datasetVersion||""))return NextResponse.json({error:"Canonical research version unavailable"},{status:503});
 return NextResponse.json({...canonicalResearchPage(raw,pacificToday()),deploymentCommit:process.env.VERCEL_GIT_COMMIT_SHA||null},{headers:{"Cache-Control":"private, no-store"}});
}
