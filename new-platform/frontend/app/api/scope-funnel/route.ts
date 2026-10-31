import { NextRequest, NextResponse } from "next/server";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../lib/auth";
import { reconcilePoolPipeline, funnelPage, type FunnelResult, type ScopeView } from "../../../lib/pool-pipeline-funnel";

export const runtime="nodejs";
export const dynamic="force-dynamic";
export const maxDuration=60;

let cached:{at:number;funnel:FunnelResult}|null=null;
let active:Promise<FunnelResult>|null=null;
async function source():Promise<FunnelResult> {
  if(cached && Date.now()-cached.at<60000)return cached.funnel;
  if(active)return active;
  active=(async()=>{
    const base=process.env.PDUFA_API_BASE_URL?.replace(/\/$/,"");
    const key=process.env.PDUFA_INTERNAL_API_KEY;
    if(!base || !/^https:\/\//.test(base) || !key) throw new Error("Backend not configured");
    const [csv,json,response]=await Promise.all([
      readFile(join(process.cwd(),"public","phase3-census-2026-10-26.csv"),"utf8"),
      readFile(join(process.cwd(),"public","phase3-census-sources-2026-10-26.json"),"utf8"),
      fetch(base+"/api/workspace",{
        headers:{"x-pdufa-internal-key":key},cache:"no-store",signal:AbortSignal.timeout(45000)
      }),
    ]);
    if(!response.ok)throw new Error("Published source POOL unavailable");
    const raw:unknown=await response.json();
    const funnel=reconcilePoolPipeline(raw,csv,JSON.parse(json));
    cached={at:Date.now(),funnel};
    return funnel;
  })();
  try{return await active}finally{active=null}
}

export async function GET(req:NextRequest) {
  if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error:"Authentication required"},{status:401});
  const params=req.nextUrl.searchParams;
  const view=params.get("view")||"pool";
  const offset=params.get("offset")||"0",limit=params.get("limit")||"50";
  const query=params.get("query")||"";
  if(!["pool","pipeline"].includes(view)
     || !/^(0|[1-9]\d{0,7})$/.test(offset)
     || !/^(?:[1-9]|[1-4]\d|50)$/.test(limit)
     || query.length>100)
    return NextResponse.json({error:"Invalid scope or pagination"},{status:422});
  try {
    const data=await source();
    return NextResponse.json(funnelPage(data,view as ScopeView,Number(offset),Number(limit),query),
      {headers:{"Cache-Control":"private, no-store"}});
  }catch{
    return NextResponse.json({error:"Cannot verify master POOL and historical Phase 3 source reconciliation; no qualified Pipeline count is available"},
      {status:503,headers:{"Cache-Control":"private, no-store"}});
  }
}
