import {NextRequest,NextResponse} from "next/server";
import {readFile} from "node:fs/promises";
import {join} from "node:path";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../lib/auth";
import {registryCoverageFromSnapshot} from "../../../lib/registry-benefit-coverage";
import {discoverRegistryPeerLeads} from "../../../lib/registry-competitor-leads";
import type {RegistryBenefitResearch} from "../../../lib/registry-benefit-research";

export const runtime="nodejs";
export const dynamic="force-dynamic";
export const maxDuration=25;
const headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"};

export async function GET(req:NextRequest){
  if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error:"Authentication required"},{status:401,headers});
  if(req.nextUrl.searchParams.size!==0)
    return NextResponse.json({error:"Unexpected parameters"},{status:422,headers});
  try{
    const raw=JSON.parse(await readFile(join(process.cwd(),"data","registry-benefit-research-snapshot.json"),"utf8"));
    // Ensure each receipt is exact-source and that archive coverage is fresh.
    const audited=registryCoverageFromSnapshot(raw);
    const records=raw.records as RegistryBenefitResearch[];
    if(records.length!==audited.records.length)throw Error("REGISTRY_PEER_COVERAGE_MISMATCH");
    const result=discoverRegistryPeerLeads(records,8);
    return NextResponse.json({schemaVersion:1,sourceAsOf:audited.sourceAsOf,
      status:"UNVERIFIED_DISCOVERY_ONLY",scope:"375_HISTORICAL_PHASE3_ARCHIVE",
      records:result},{headers});
  }catch{
    return NextResponse.json({error:"Competitor discovery archive unavailable or stale; do not infer zero competitors"},
      {status:503,headers});
  }
}
