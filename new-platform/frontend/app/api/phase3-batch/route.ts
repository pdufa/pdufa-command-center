import { NextRequest, NextResponse } from "next/server";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../lib/auth";
import { parsePhase3CensusCsv } from "../../../lib/phase3-census-rows";
import { normalizeRegistryStudy } from "../../../lib/pipeline-live-registry";
import { renderRegistryEvidenceBatchCsv } from "../../../lib/pipeline-registry-evidence";

export const runtime="nodejs";
export const dynamic="force-dynamic";
export const maxDuration=30;

type RegistryListResponse={studies?:unknown[];nextPageToken?:unknown};
const PUBLIC_REGISTRY="https://clinicaltrials.gov/api/v2/studies";
const limitAllowed=new Set([5,10,25]);

/** A signed-in, bounded, read-only review export, NOT automatic Sheet write-back. */
export async function GET(req:NextRequest){
 if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
  return NextResponse.json({error:"Authentication required"},{status:401,headers:{"Cache-Control":"private, no-store"}});
 const p=req.nextUrl.searchParams;
 const offsetText=p.get("offset")||"0",limitText=p.get("limit")||"25";
 const offset=Number(offsetText),limit=Number(limitText);
 if(p.get("format")!=="csv"||!/^(0|[1-9]\d{0,2})$/.test(offsetText)
  ||!/^(5|10|25)$/.test(limitText)||!limitAllowed.has(limit)
  ||!Number.isSafeInteger(offset)||offset>=741||offset%limit!==0)
  return NextResponse.json({error:"Invalid registry batch offset, limit or export format"},{status:422,headers:{"Cache-Control":"private, no-store"}});
 try{
  const original=await readFile(join(process.cwd(),"public","phase3-census-2026-10-26.csv"),"utf8");
  const pinned=parsePhase3CensusCsv(original);
  if(pinned.rows.length!==741)throw Error("Historical census incomplete");
  const current=pinned.rows.slice(offset,Math.min(offset+limit,741));
  if(!current.length)throw Error("Historical census selection empty");
  const ids=current.map(x=>x.nctId),wanted=new Set(ids);
  if(wanted.size!==ids.length)throw Error("Repeated census NCT");
  const url=new URL(PUBLIC_REGISTRY);
  url.searchParams.set("filter.ids",ids.join(","));
  url.searchParams.set("pageSize",String(current.length));
  url.searchParams.set("format","json");
  const upstream=await fetch(url.toString(),{method:"GET",redirect:"manual",cache:"no-store",
    headers:{Accept:"application/json"},signal:AbortSignal.timeout(18000)});
  if(!upstream.ok||(upstream.headers.get("content-type")||"").toLowerCase().includes("json")===false)
   throw Error("Current official registry batch unavailable");
  const raw:unknown=await upstream.json();
  if(!raw||typeof raw!=="object"||Array.isArray(raw))throw Error("Unexpected official registry response");
  const result=raw as RegistryListResponse;
  if(!Array.isArray(result.studies)||result.studies.length!==current.length||result.nextPageToken)
   throw Error("Incomplete official registry batch");
  const byNct=new Map<string,unknown>();
  for(const item of result.studies){
   if(!item||typeof item!=="object")throw Error("Invalid study in registry batch");
   const study=item as {protocolSection?:{identificationModule?:{nctId?:unknown}}};
   const id=study.protocolSection?.identificationModule?.nctId;
   if(typeof id!=="string"||!wanted.has(id)||byNct.has(id))throw Error("Duplicate or unexpected registry NCT");
   byNct.set(id,item);
  }
  if(byNct.size!==ids.length)throw Error("Incomplete exact-NCT registry batch");
  const timestamp=new Date().toISOString();
  const records=current.map(row=>({pinned:{nctId:row.nctId,ticker:row.ticker,company:row.company},
    review:normalizeRegistryStudy(byNct.get(row.nctId),row.nctId,timestamp)}));
  const csv=renderRegistryEvidenceBatchCsv(records);
  return new NextResponse(csv,{headers:{
   "Content-Type":"text/csv; charset=utf-8",
   "Content-Disposition":`attachment; filename="pdufa-registry-review-offset-${offset}-count-${current.length}.csv"`,
   "Cache-Control":"private, no-store",
   "X-PDUFA-Registry-Records":String(current.length),
   "X-PDUFA-Registry-Status":"REVIEW_REQUIRED",
   "X-PDUFA-Registry-Snapshot":"2026-10-26"
  }});
 }catch{
  // No partial export: absent, duplicate, stale or mismatched IDs must never look reviewed.
  return NextResponse.json({error:"Current registry batch could not be fully verified. No rows were exported or qualified. Retry a smaller batch."},
   {status:503,headers:{"Cache-Control":"private, no-store"}});
 }
}
