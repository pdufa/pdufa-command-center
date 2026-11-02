import {NextRequest,NextResponse} from "next/server";
import {readFile} from "node:fs/promises";
import {join} from "node:path";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../lib/auth";
import {verifiedToolPool} from "../../../lib/tools-pool-inventory";
import {parseRegistryBenefitResearch} from "../../../lib/registry-benefit-research";

export const runtime="nodejs";
export const dynamic="force-dynamic";
export const maxDuration=30;
const headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"};
const registryBase="https://clinicaltrials.gov/api/v2/studies/";
/** Live, read-only results for a specific NCT from the saved TOOLS source pool.
 * The pool is an NCT identity allowlist, NOT a claim about live issuer market cap,
 * Phase 3 success, public sponsor readout, FDA deadline or investment eligibility.
 * Individual trials outside the original 375-study historical archive are supported.
 */
export async function GET(req:NextRequest){
  if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error:"Authentication required"},{status:401,headers});
  const params=req.nextUrl.searchParams;
  if(params.size!==1||!params.has("nct"))return NextResponse.json(
    {error:"Exactly one NCT ID is required"},{status:422,headers});
  const nct=params.get("nct")||"";
  if(!/^NCT\d{8}$/.test(nct))return NextResponse.json(
    {error:"Invalid NCT ID"},{status:422,headers});
  try{
    const raw=JSON.parse(await readFile(
      join(process.cwd(),"data","tools-pool-snapshot.json"),"utf8"));
    if(raw.schemaVersion!==1||typeof raw.snapshotGeneratedAt!=="string")
      throw Error("TOOLS_POOL_SOURCE_INVALID");
    const snapshot=verifiedToolPool(raw);
    // Source membership alone does not certify the market-cap subset or readout.
    if(!snapshot.poolRows.some(item=>item.id==="TRIAL|"+nct))
      return NextResponse.json({error:"NCT not in published TOOLS trial universe"},
        {status:404,headers});
    const response=await fetch(registryBase+nct,{
      method:"GET",redirect:"error",cache:"no-store",
      headers:{Accept:"application/json"},signal:AbortSignal.timeout(15000)
    });
    if(!response.ok||
      !(response.headers.get("content-type")||"").toLowerCase().includes("json"))
      throw Error("PRIMARY_REGISTRY_UNAVAILABLE");
    const max=800000,declared=Number(response.headers.get("content-length"));
    if(Number.isFinite(declared)&&declared>max)throw Error("REGISTRY_SOURCE_TOO_LARGE");
    const body=await response.text();
    if(body.length>max)throw Error("REGISTRY_SOURCE_TOO_LARGE");
    const evidence=parseRegistryBenefitResearch(JSON.parse(body),nct,new Date().toISOString());
    return NextResponse.json({
      ...evidence,
      qualification:"NOT_VERIFIED",
      poolSourceAsOf:snapshot.sourceAsOf,
      scope:"EXACT_NCT_SOURCE_RESEARCH_ONLY",
      clinicalComparisonVerified:false,
      stockAppreciationRank:null
    },{headers});
  }catch{
    return NextResponse.json(
      {error:"Verified source data unavailable; no clinical or investment rating calculated."},
      {status:503,headers});
  }
}
