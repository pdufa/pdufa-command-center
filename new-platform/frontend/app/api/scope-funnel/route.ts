import { createHash } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../lib/auth";
import { reconcilePoolPipeline, funnelPage, type FunnelResult, type ScopeView, POOL_STAGE_GROUPS, POOL_STAGES, type PoolStageGroup, type PoolRecordKind } from "../../../lib/pool-pipeline-funnel";
import { fetchReadOnlyWithWarmRetry } from "../../../lib/read-only-warm-retry";
import { renderPhase3CensusCsv } from "../../../lib/pipeline-census-csv";

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
      // One bounded retry for a sleeping/restarting Render instance. Share a
      // single deadline; never retry auth errors, invalid data or source drift.
      fetchReadOnlyWithWarmRetry(base+"/api/workspace?require_fresh=true",{
        method:"GET",headers:{"x-pdufa-internal-key":key},
        cache:"no-store",signal:AbortSignal.timeout(50000)
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
  const format=params.get("format")||"json";
  const stageGroup=params.get("stageGroup")||"all";
  const stage=params.get("stage")||"";
  const recordKind=params.get("recordKind")||"all";
  const stagesParam=params.get("stages")||"";
  const selectedStages=stagesParam?stagesParam.split(","):[];
  if(!["pool","pipeline","readout-review","census-review"].includes(view)
     || !/^(0|[1-9]\d{0,7})$/.test(offset)
     || !(/^(?:[1-9]|[1-4]\d|50)$/.test(limit) || (view==="pipeline" && /^(?:[1-9]\d?|1\d\d|200|500)$/.test(limit)))
     || query.length>100 || !["json","csv"].includes(format) || (format==="csv" && view!=="census-review")
     || !["all",...Object.keys(POOL_STAGE_GROUPS)].includes(stageGroup)
     || (stage && !(POOL_STAGES as readonly string[]).includes(stage))
     || !["all","trials","other"].includes(recordKind)
     || selectedStages.length>POOL_STAGES.length
     || new Set(selectedStages).size!==selectedStages.length
     || selectedStages.some(selected=>!(POOL_STAGES as readonly string[]).includes(selected))
     || (selectedStages.length>0 && (stageGroup!=="all" || stage!==""))
     || (view!=="pool" && (stageGroup!=="all" || stage || recordKind!=="all" || selectedStages.length>0)))
    return NextResponse.json({error:"Invalid scope or pagination"},{status:422});
  try {
    const data=await source();
    const datasetVersion=createHash("sha256").update(JSON.stringify({overview:data.overview,rows:data.reviewRows})).digest("hex");
    if(view==="census-review" && format==="csv"){
      if(query.trim()||offset!=="0")return NextResponse.json({error:"CSV is a full, unfiltered source snapshot"},{status:422});
      const csv=renderPhase3CensusCsv(data);
      return new NextResponse(csv,{headers:{
        "Content-Type":"text/csv; charset=utf-8",
        "Content-Disposition":"attachment; filename=\"pdufa-phase3-historical-review-2026-10-26.csv\"",
        "Cache-Control":"private, no-store",
        "X-PDUFA-Source-Version":datasetVersion,
      }});
    }
    return NextResponse.json({...funnelPage(data,view as ScopeView,Number(offset),Number(limit),query,stageGroup as PoolStageGroup,stage,recordKind as PoolRecordKind,selectedStages),datasetVersion},
      {headers:{"Cache-Control":"private, no-store"}});
  }catch(cause){
    // Only a finite cause category is returned to the signed-in operator.
    // Never expose backend URLs, credentials, clinical rows or private trace text.
    let reasonCode="SOURCE_RECONCILIATION_FAILED";
    if(cause instanceof Error){
      if(cause.message==="Backend not configured")reasonCode="BACKEND_NOT_CONFIGURED";
      else if(cause.message==="Published source POOL unavailable")reasonCode="BACKEND_SOURCE_HTTP_ERROR";
      else if(cause.message.includes("integrity or freshness"))reasonCode="POOL_SOURCE_INTEGRITY_OR_STALE";
      else if(cause.message.startsWith("Research inventory unavailable"))reasonCode="PINNED_CENSUS_CSV_INVALID";
      else if(cause.message.startsWith("Census research sources blocked"))reasonCode="PINNED_CENSUS_SOURCES_INVALID";
      else if(cause.message.includes("ENOENT"))reasonCode="PINNED_SERVERLESS_ASSET_MISSING";
      else if(cause.name==="TimeoutError"||cause.name==="AbortError")reasonCode="BACKEND_TIMEOUT";
    }
    return NextResponse.json({
      error:"Cannot verify master POOL and historical Phase 3 source reconciliation; no qualified Pipeline count is available",
      reasonCode
    },{status:503,headers:{"Cache-Control":"private, no-store"}});
  }
}

