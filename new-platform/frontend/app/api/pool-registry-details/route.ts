import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../lib/auth";
import {normalizePoolRegistryDetail} from "../../../lib/pool-registry-details";

export const runtime="nodejs";
export const dynamic="force-dynamic";
export const maxDuration=30;
const privateHeaders={"Cache-Control":"private, no-store"};

/** Exact-NCT, authenticated, read-only registry enrichment for POOL.
 * Fetch only on user action; never make 50 registry requests per table page.
 * CT.gov source facts are not RAAS/FDA eligibility or approved scores.
 */
export async function GET(req:NextRequest){
 if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
  return NextResponse.json({error:"Authentication required"},{status:401,headers:privateHeaders});
 const nct=(req.nextUrl.searchParams.get("nct")||"").trim();
 if(!/^NCT\d{8}$/.test(nct))
  return NextResponse.json({error:"Valid NCT ID required"},{status:422,headers:privateHeaders});
 try{
  const response=await fetch("https://clinicaltrials.gov/api/v2/studies/"+nct,{
   method:"GET",headers:{Accept:"application/json"},cache:"no-store",
   redirect:"manual",signal:AbortSignal.timeout(14000)
  });
  if(!response.ok||!(response.headers.get("content-type")||"").includes("json"))
   throw Error("Registry request failed");
  const size=Number(response.headers.get("content-length")||"0");
  if(size>4_000_000)throw Error("Registry response exceeds bounded detail size");
  const raw:unknown=await response.json();
  const details=normalizePoolRegistryDetail(raw,nct,new Date().toISOString());
  return NextResponse.json(details,{headers:privateHeaders});
 }catch{
  return NextResponse.json({error:"Official ClinicalTrials.gov record unavailable or invalid. No POOL data or scores were changed."},
   {status:503,headers:privateHeaders});
 }
}
