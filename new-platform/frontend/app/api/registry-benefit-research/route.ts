import {NextRequest,NextResponse} from "next/server";
import {readFile} from "node:fs/promises";
import {join} from "node:path";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../lib/auth";
import {parsePhase3CensusCsv} from "../../../lib/phase3-census-rows";
import {parseRegistryBenefitResearch,type RegistryBenefitResearch} from "../../../lib/registry-benefit-research";

export const runtime="nodejs";
export const dynamic="force-dynamic";
export const maxDuration=30;
const origin="https://clinicaltrials.gov/api/v2/studies/";
const headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"};
const snapshotPath=join(process.cwd(),"data","registry-benefit-research-snapshot.json");
async function archivedEvidence(nct:string):Promise<RegistryBenefitResearch|null>{
  try{
    const raw=JSON.parse(await readFile(snapshotPath,"utf8")) as Record<string,unknown>;
    if(raw.schemaVersion!==1||!Array.isArray(raw.records)||raw.records.length>375)return null;
    const packet=raw.records.find((r:unknown)=>!!r&&typeof r==="object"&&
      (r as Record<string,unknown>).nctId===nct) as RegistryBenefitResearch|undefined;
    if(!packet||packet.sourceUrl!=="https://clinicaltrials.gov/study/"+nct
      ||packet.comparisonVerified!==false||packet.benefitRank!==null
      ||packet.fdaDecisionVerified!==false||!Array.isArray(packet.primary)
      ||!Array.isArray(packet.secondary)||!Array.isArray(packet.seriousAdverseEvents)
      ||typeof packet.resultsPosted!=="boolean")return null;
    const age=Date.now()-Date.parse(packet.retrievedAt);
    return Number.isFinite(age)&&age>=0&&age<48*3600000?packet:null;
  }catch{return null;}
}
/** Per-study independent evidence retrieval. No arbitrary URLs and no
 * unsupported sponsor/source claims are promoted into assessments.
 */
export async function GET(req:NextRequest){
  if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error:"Authentication required"},{status:401,headers});
  if(req.nextUrl.searchParams.size!==1||!req.nextUrl.searchParams.has("nct"))
    return NextResponse.json({error:"One exact NCT is required"},{status:422,headers});
  const nct=req.nextUrl.searchParams.get("nct");
  if(!nct||!/^NCT\d{8}$/.test(nct))
    return NextResponse.json({error:"Invalid NCT"},{status:422,headers});
  try{
    const file=await readFile(join(process.cwd(),"public","phase3-census-2026-10-26.csv"),"utf8");
    const pinned=parsePhase3CensusCsv(file);
    if(pinned.rows.length!==741||!pinned.rows.some(row=>row.nctId===nct))
      return NextResponse.json({error:"Not a pinned historical Phase 3 research NCT"},{status:404,headers});
    const fromArchive=await archivedEvidence(nct);
    if(fromArchive)return NextResponse.json(fromArchive,{headers:{...headers,"X-PDUFA-Evidence-Origin":"dated-primary-source-archive"}});
    const response=await fetch(origin+nct,{
      method:"GET",cache:"no-store",redirect:"error",
      headers:{Accept:"application/json"},signal:AbortSignal.timeout(15000)
    });
    if(!response.ok||!(response.headers.get("content-type")||"").toLowerCase().includes("json"))
      return NextResponse.json({error:"Primary registry study temporarily unavailable"},{status:503,headers});
    const max=800000,declared=Number(response.headers.get("content-length"));
    if(declared>max)return NextResponse.json({error:"Registry evidence exceeds source limit"},{status:503,headers});
    const body=await response.text();
    if(body.length>max)throw Error("REGISTRY_TOO_LARGE");
    const evidence=parseRegistryBenefitResearch(JSON.parse(body),nct,new Date().toISOString());
    return NextResponse.json(evidence,{headers});
  }catch{
    return NextResponse.json({error:"Registry evidence could not be verified. No assessment results were changed."},{status:503,headers});
  }
}
