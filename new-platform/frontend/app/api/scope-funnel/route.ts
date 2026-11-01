import { createHash } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../lib/auth";
import { reconcilePoolPipeline, funnelPage, type FunnelResult, type ScopeView, POOL_STAGE_GROUPS, POOL_STAGES, type PoolStageGroup, type PoolRecordKind } from "../../../lib/pool-pipeline-funnel";
import { fetchReadOnlyWithWarmRetry } from "../../../lib/read-only-warm-retry";
import { renderPhase3CensusCsv } from "../../../lib/pipeline-census-csv";
import {buildDesignationIndex, applyReviewedDesignationLinks, SPECIAL_DESIGNATION_CATEGORIES, type DesignationIndex, type DesignationKey} from "../../../lib/trial-designations";
import {isPoolTrial} from "../../../lib/pool-pipeline-funnel";
import {toolSpreadsheetRow,renderToolsSpreadsheetCsv} from "../../../lib/tools-spreadsheet";
import {normalizePoolStage, type PoolTrialRecord} from "../../../lib/pool-pipeline-funnel";
import {verifiedToolPool,buildToolsResults,filterToolTrials,selectToolTrialIds,renderUnlinkedFdaProgramCsv} from "../../../lib/tools-pool-inventory";

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

const DESIGNATION_SOURCE="https://raw.githubusercontent.com/pdufa/pdufa-command-center/main/data/";
async function designationEvidence():Promise<DesignationIndex>{
  // Reuse the same saved source files and exact-linking policy as /api/trial-designations.
  const [evidence,applications,reviewedCrosswalk]=await Promise.all(
    ["prediction_engine_designations.csv","pdufa_candidates.csv","fda_designation_nct_evidence.csv"].map(async file=>{
      const response=await fetch(DESIGNATION_SOURCE+file,{
        next:{revalidate:300},signal:AbortSignal.timeout(20000)
      });
      if(!response.ok)throw new Error("DESIGNATION_SOURCE_UNAVAILABLE");
      const csv=await response.text();
      if(csv.length>2_000_000)throw new Error("DESIGNATION_SOURCE_UNAVAILABLE");
      return csv;
    })
  );
  return applyReviewedDesignationLinks(buildDesignationIndex(evidence,applications,new Date().toISOString()),reviewedCrosswalk);
}
function linkedDesignationTrialIds(data:FunnelResult,index:DesignationIndex,selected:readonly DesignationKey[]):Set<string>{
  const matched=new Set<string>();
  for(const trial of data.poolRows){
    if(!isPoolTrial(trial))continue;
    const nct=trial.id.slice("TRIAL|".length);
    const keys=index.trialEvents[nct]||[];
    if(keys.some(key=>{
      const program=index.programs[key];
      if(!program||!trial.ticker||program.ticker!==trial.ticker.toUpperCase())return false;
      return selected.some(type=>{
        const evidence=program.designations[type];
        return evidence?.status==="GRANTED" && evidence.verification!=="UNVERIFIED" && !!evidence.source;
      });
    }))matched.add(trial.id);
  }
  return matched;
}

// Immutable at build time: the same verified published-source NCT inventory
// is refreshed by the scheduled, authenticated GitHub source snapshot audit.
// Never serve a stale, unverified, corrupt or mismatched snapshot.
let publishedToolSnapshot:ReturnType<typeof verifiedToolPool>|null=null;
let publishedToolSnapshotChecked=false;
async function publishedPoolSource():Promise<ReturnType<typeof verifiedToolPool>|null>{
  if(publishedToolSnapshotChecked)return publishedToolSnapshot;
  publishedToolSnapshotChecked=true;
  try{
    const file=join(process.cwd(),"data","tools-pool-snapshot.json");
    const raw=JSON.parse(await readFile(file,"utf8")) as Record<string,unknown>;
    const timestamp=typeof raw.snapshotGeneratedAt==="string"?Date.parse(raw.snapshotGeneratedAt):NaN;
    if(!Number.isFinite(timestamp)||timestamp>Date.now()+300000||Date.now()-timestamp>36*3600000)
      throw Error("Published static POOL snapshot expired");
    if(raw.schemaVersion!==1)throw Error("Published static POOL schema mismatch");
    publishedToolSnapshot=verifiedToolPool(raw);
    return publishedToolSnapshot;
  }catch{
    // Freshness/parity errors fall back to the authenticated live backend.
    return null;
  }
}

let toolsCache:{at:number;value:ReturnType<typeof verifiedToolPool>}|null=null;
let toolsActive:Promise<ReturnType<typeof verifiedToolPool>>|null=null;
async function toolsPoolSource():Promise<ReturnType<typeof verifiedToolPool>>{
  const published=await publishedPoolSource();
  if(published)return published;
  if(toolsCache && Date.now()-toolsCache.at<60000)return toolsCache.value;
  if(toolsActive)return toolsActive;
  toolsActive=(async()=>{
    const rawBase=process.env.PDUFA_API_BASE_URL||"";
    const base=rawBase.endsWith("/")?rawBase.slice(0,-1):rawBase;
    const key=process.env.PDUFA_INTERNAL_API_KEY;
    if(!base.startsWith("https://")||!key)throw Error("Backend not configured");
    const response=await fetchReadOnlyWithWarmRetry(base+"/api/workspace?require_fresh=true",{
      method:"GET",headers:{"x-pdufa-internal-key":key},cache:"no-store",
      signal:AbortSignal.timeout(50000)
    });
    if(!response.ok)throw Error("Published source POOL unavailable");
    const raw:unknown=await response.json();
    const verified=verifiedToolPool(raw);
    toolsCache={at:Date.now(),value:verified};
    return verified;
  })();
  try{return await toolsActive}finally{toolsActive=null}
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
  const toolsParam=params.get("tools")||"";
  const toolMode=toolsParam==="1";
  const designationsParam=params.get("designations")||"";
  const selectedDesignations=designationsParam?designationsParam.split(",") as DesignationKey[]:[];
  if(!["pool","pipeline","readout-review","census-review"].includes(view)
     || !/^(0|[1-9]\d{0,7})$/.test(offset)
     || !(/^(?:[1-9]|[1-4]\d|50)$/.test(limit) || (view==="pipeline" && /^(?:[1-9]\d?|1\d\d|200|500)$/.test(limit)))
     || query.length>100 || !["json","csv"].includes(format) || (format==="csv" && view!=="census-review" && !(view==="pool" && toolMode))
     || !["all",...Object.keys(POOL_STAGE_GROUPS)].includes(stageGroup)
     || (stage && !(POOL_STAGES as readonly string[]).includes(stage))
     || !["all","trials","other"].includes(recordKind)
     || selectedStages.length>POOL_STAGES.length
     || new Set(selectedStages).size!==selectedStages.length
     || selectedStages.some(selected=>!(POOL_STAGES as readonly string[]).includes(selected))
     || (selectedStages.length>0 && (stageGroup!=="all" || stage!==""))
     || !["","1"].includes(toolsParam)
     || selectedDesignations.length>SPECIAL_DESIGNATION_CATEGORIES.length
     || new Set(selectedDesignations).size!==selectedDesignations.length
     || selectedDesignations.some(key=>!SPECIAL_DESIGNATION_CATEGORIES.some(item=>item.key===key))
     || (selectedDesignations.length>0 && (!toolMode || recordKind!=="trials"))
     || (toolMode && (view!=="pool" || recordKind!=="trials" || stageGroup!=="all" || !!stage))
     || (format==="csv" && toolMode && (offset!=="0" || (selectedStages.length===0 && selectedDesignations.length===0)))
     || (view!=="pool" && (stageGroup!=="all" || stage || recordKind!=="all" || selectedStages.length>0)))
    return NextResponse.json({error:"Invalid scope or pagination"},{status:422});
  try {
    if(toolMode){
      // TOOLS must not fail just because the independent 741-row Phase 3 census
      // or its market-cap research directory cannot be reconciled.
      const [inventory,index]=await Promise.all([
        toolsPoolSource(),
        selectedDesignations.length>0?designationEvidence():Promise.resolve(null)
      ]);
      if(index && selectedDesignations.some(key=>!index.availableKeys?.[key])){
        return NextResponse.json({
          error:"Selected FDA category has no tracked saved source field",
          reasonCode:"DESIGNATION_FIELD_NOT_TRACKED"
        },{status:422,headers:{"Cache-Control":"private, no-store"}});
      }
      // A saved designation grant on an FDA application is not sufficient to
      // associate that designation with a specific NCT trial. Do not report a
      // fabricated zero when no exact application-to-NCT crosswalk exists.
      if(selectedDesignations.length>0 && index
        && Object.keys(index.trialEvents).length===0){
        return NextResponse.json({
          error:"No verified NCT-to-application links are recorded for the FDA designations. The stage filter remains available, but the combined trial total cannot be calculated from the current sources.",
          reasonCode:"DESIGNATION_NCT_LINKAGE_UNAVAILABLE"
        },{status:422,headers:{"Cache-Control":"private, no-store"}});
      }
      const result=buildToolsResults(inventory,index,selectedStages,selectedDesignations,
        query,Number(offset),Number(limit));
      const datasetVersion=createHash("sha256")
        .update(JSON.stringify({asOf:inventory.sourceAsOf,recordCount:inventory.poolRows.length}))
        .digest("hex");
      if(format==="csv"){
        if(result.designationCoverage?.noVerifiedNctLinks){
          const csv=renderUnlinkedFdaProgramCsv(result.designationCoverage,inventory.sourceAsOf);
          return new NextResponse(csv,{headers:{
            "Content-Type":"text/csv; charset=utf-8",
            "Content-Disposition":'attachment; filename="pdufa-tools-fda-program-records-unlinked.csv"',
            "Cache-Control":"private, no-store",
            "X-PDUFA-Record-Type":"FDA_PROGRAM_EVENT_NOT_NCT",
            "X-PDUFA-Source-Version":datasetVersion
          }});
        }
        const matches=index?selectToolTrialIds(inventory.poolRows,index,selectedDesignations):null;
        const rows=filterToolTrials(inventory.poolRows,selectedStages,matches,query);
        if(rows.length>25000)return NextResponse.json({error:"Selection exceeds export row limit"},{status:413});
        const csv=renderToolsSpreadsheetCsv(rows,selectedStages,selectedDesignations,index,inventory.sourceAsOf);
        return new NextResponse(csv,{headers:{
          "Content-Type":"text/csv; charset=utf-8",
          "Content-Disposition":'attachment; filename="pdufa-tools-selected-trials.csv"',
          "Cache-Control":"private, no-store",
          "X-PDUFA-Source-Version":datasetVersion
        }});
      }
      return NextResponse.json({...result,datasetVersion},{headers:{"Cache-Control":"private, no-store"}});
    }
    // Stage counts always come from the full POOL. Designation selection is
    // intersected with those records server-side BEFORE pagination.
    const [data,designationIndex]=await Promise.all([
      source(),selectedDesignations.length>0?designationEvidence():Promise.resolve(null)
    ]);
    if(designationIndex && selectedDesignations.some(key=>!designationIndex.availableKeys?.[key])){
      return NextResponse.json({error:"Selected FDA category has no available saved source field",reasonCode:"DESIGNATION_FIELD_NOT_TRACKED"},
        {status:422,headers:{"Cache-Control":"private, no-store"}});
    }
    const designationMatches=designationIndex
      ?linkedDesignationTrialIds(data,designationIndex,selectedDesignations):null;
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
    const page=funnelPage(data,view as ScopeView,Number(offset),Number(limit),query,
      stageGroup as PoolStageGroup,stage,recordKind as PoolRecordKind,selectedStages,designationMatches,toolMode);
    const stageSelectors=toolMode?selectedStages.map(label=>({
      label,trials:data.poolRows.filter(row=>isPoolTrial(row)&&normalizePoolStage(row.stage)===label).length
    })):[];
    const designationSelectors=toolMode?selectedDesignations.map(key=>({
      key,label:SPECIAL_DESIGNATION_CATEGORIES.find(category=>category.key===key)!.label,
      linkedTrials:designationIndex?linkedDesignationTrialIds(data,designationIndex,[key]).size:0
    })):[];
    const selectionSummary=toolMode?{
      selectedCount:selectedStages.length+selectedDesignations.length,
      stageSelectedCount:selectedStages.length,
      designationSelectedCount:selectedDesignations.length,
      stageTotal:stageSelectors.reduce((sum,item)=>sum+item.trials,0),
      // Each designation's NCT matches may overlap another designation.
      designationCountSum:designationSelectors.reduce((sum,item)=>sum+item.linkedTrials,0),
      designationUniqueTrials:designationMatches?.size??null,
      matchingUniqueTrials:page.total,
      stageSelectors,designationSelectors
    }:null;
    if(toolMode && format==="csv"){
      // Export exactly the current filtered result set, not merely the visible 50-row page.
      const all=funnelPage(data,"pool",0,data.poolRows.length,query,"all","","trials",
        selectedStages,designationMatches,true);
      if(all.rows.length>25000)return NextResponse.json({error:"Selection exceeds the export row limit"},{status:413});
      const csv=renderToolsSpreadsheetCsv(all.rows as PoolTrialRecord[],selectedStages,
        selectedDesignations,designationIndex,data.overview.poolAsOf||"");
      return new NextResponse(csv,{headers:{
        "Content-Type":"text/csv; charset=utf-8",
        "Content-Disposition":"attachment; filename=\"pdufa-tools-selected-trials.csv\"",
        "Cache-Control":"private, no-store",
        "X-PDUFA-Source-Version":datasetVersion
      }});
    }
    return NextResponse.json({...page,
      spreadsheetRows:toolMode?page.rows.map(row=>toolSpreadsheetRow(
        row as PoolTrialRecord,selectedStages,selectedDesignations,designationIndex)):undefined,
      selectionSummary,
      designationLinkage:designationIndex?{basis:"EXACT_NCT_AND_TICKER",sourceLinkedTrials:designationMatches?.size??0}:null,
      datasetVersion},
      {headers:{"Cache-Control":"private, no-store"}});
  }catch(cause){
    // Only a finite cause category is returned to the signed-in operator.
    // Never expose backend URLs, credentials, clinical rows or private trace text.
    let reasonCode="SOURCE_RECONCILIATION_FAILED";
    if(cause instanceof Error){
      if(cause.message==="POOL_SOURCE_STALE")reasonCode="POOL_SOURCE_STALE";
      else if(cause.message==="POOL_SOURCE_PARITY_FAILED")reasonCode="POOL_SOURCE_PARITY_FAILED";
      else if(cause.message==="POOL_INVALID_RESPONSE")reasonCode="POOL_INVALID_RESPONSE";
      else if(cause.message==="DESIGNATION_SOURCE_UNAVAILABLE")reasonCode="DESIGNATION_SOURCE_UNAVAILABLE";
      else if(cause.message==="Backend not configured")reasonCode="BACKEND_NOT_CONFIGURED";
      else if(cause.message==="Published source POOL unavailable")reasonCode="BACKEND_SOURCE_HTTP_ERROR";
      else if(cause.message.includes("integrity or freshness"))reasonCode="POOL_SOURCE_INTEGRITY_OR_STALE";
      else if(cause.message.startsWith("Research inventory unavailable"))reasonCode="PINNED_CENSUS_CSV_INVALID";
      else if(cause.message.startsWith("Census research sources blocked"))reasonCode="PINNED_CENSUS_SOURCES_INVALID";
      else if(cause.message.includes("ENOENT"))reasonCode="PINNED_SERVERLESS_ASSET_MISSING";
      else if(cause.name==="TimeoutError"||cause.name==="AbortError")reasonCode="BACKEND_TIMEOUT";
    }
    return NextResponse.json({
      error:reasonCode==="POOL_SOURCE_STALE"?"The published POOL is temporarily stale; stage counts are withheld until refresh completes":
        reasonCode==="POOL_SOURCE_PARITY_FAILED"?"The published POOL trial count disagrees with its source metadata; counts are withheld":
        reasonCode==="POOL_INVALID_RESPONSE"?"The published POOL response is missing required inventory data":
        reasonCode==="DESIGNATION_SOURCE_UNAVAILABLE"
        ?"FDA designation evidence unavailable; combined trial matches cannot be calculated"
        :"Cannot verify master POOL and historical Phase 3 source reconciliation; no qualified Pipeline count is available",
      reasonCode
    },{status:503,headers:{"Cache-Control":"private, no-store"}});
  }
}

