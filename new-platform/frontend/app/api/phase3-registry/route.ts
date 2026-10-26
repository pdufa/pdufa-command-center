import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../lib/auth";
import { normalizeRegistryResearchRecord, REGISTRY_SOURCE_ORIGIN } from "../../../lib/phase3-live-registry";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 30;
const headers = { "Cache-Control":"private, no-store", "X-Content-Type-Options":"nosniff" };
const MAX_SOURCE_BYTES = 800_000;

export async function GET(req:NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({error:"Authentication required"}, {status:401,headers});
  }
  if (req.nextUrl.searchParams.size !== 1 || !req.nextUrl.searchParams.has("exact_nct")) {
    return NextResponse.json({error:"One exact NCT identifier is required"}, {status:422,headers});
  }
  const nct=req.nextUrl.searchParams.get("exact_nct");
  if (!nct || !/^NCT\d{8}$/.test(nct)) {
    return NextResponse.json({error:"Exact NCT identifier invalid"}, {status:422,headers});
  }
  let upstream:Response;
  try {
    // Fixed origin + strict exact-NCT path. No user-controlled URL, redirect,
    // internal credentials, cookie forwarding, POST, retries or data storage.
    upstream=await fetch(REGISTRY_SOURCE_ORIGIN+"/api/v2/studies/"+nct,{
      method:"GET",headers:{Accept:"application/json"},
      cache:"no-store",redirect:"error",signal:AbortSignal.timeout(12000),
    });
  } catch {
    return NextResponse.json({error:"ClinicalTrials.gov source unreachable; no evidence promoted"}, {status:503,headers});
  }
  if (!upstream.ok) {
    return NextResponse.json({
      error: upstream.status===404
        ? "Exact study is not currently returned by the registry"
        : "ClinicalTrials.gov source not available; no evidence promoted",
    }, {status:503,headers});
  }
  const claimedLength=Number(upstream.headers.get("content-length"));
  if (claimedLength>MAX_SOURCE_BYTES) {
    return NextResponse.json({error:"Registry source exceeds safe research limits"}, {status:503,headers});
  }
  try {
    const source=await upstream.text();
    if (source.length>MAX_SOURCE_BYTES) throw new Error("Oversized source");
    const normalized=normalizeRegistryResearchRecord(JSON.parse(source),nct,new Date().toISOString());
    return NextResponse.json(normalized,{headers});
  } catch {
    return NextResponse.json({
      error:"Registry source failed exact-study integrity validation; no research conclusions",
    },{status:503,headers});
  }
}
