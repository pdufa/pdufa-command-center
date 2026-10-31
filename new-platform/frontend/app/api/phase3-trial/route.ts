import { NextRequest, NextResponse } from "next/server";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../lib/auth";
import { parsePhase3CensusCsv } from "../../../lib/phase3-census-rows";
import { normalizeRegistryStudy } from "../../../lib/pipeline-live-registry";

export const runtime="nodejs";
export const dynamic="force-dynamic";
export const maxDuration=30;
const base="https://clinicaltrials.gov/api/v2/studies/";

export async function GET(req:NextRequest){
 if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
  return NextResponse.json({error:"Authentication required"},{status:401,headers:{"Cache-Control":"private, no-store"}});
 const nct=(req.nextUrl.searchParams.get("nct")||"").trim();
 if(!/^NCT\d{8}$/.test(nct))
  return NextResponse.json({error:"A valid NCT ID is required"},{status:422});
 try{
  // Prevent an authenticated registry proxy from being used for arbitrary IDs.
  const csv=await readFile(join(process.cwd(),"public","phase3-census-2026-10-26.csv"),"utf8");
  const corpus=parsePhase3CensusCsv(csv);
  if(corpus.rows.length!==741||!corpus.rows.some(r=>r.nctId===nct))
   return NextResponse.json({error:"NCT not in the pinned historical Phase 3 review universe"},{status:404,headers:{"Cache-Control":"private, no-store"}});
  const upstream=await fetch(base+nct,{method:"GET",cache:"no-store",redirect:"manual",
   headers:{Accept:"application/json"},signal:AbortSignal.timeout(13000)});
  if(!upstream.ok || !(upstream.headers.get("content-type")||"").includes("json"))
   return NextResponse.json({error:"ClinicalTrials.gov record unavailable",sourceStatus:upstream.status},
    {status:503,headers:{"Cache-Control":"private, no-store"}});
  const raw:unknown=await upstream.json();
  const record=normalizeRegistryStudy(raw,nct,new Date().toISOString());
  return NextResponse.json(record,{headers:{"Cache-Control":"private, no-store"}});
 }catch{
  return NextResponse.json({error:"Cannot independently check the current trial registry. No eligibility status has changed."},
   {status:503,headers:{"Cache-Control":"private, no-store"}});
 }
}
