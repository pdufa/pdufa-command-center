import {NextRequest,NextResponse} from "next/server";
import {readFile} from "node:fs/promises";
import {join} from "node:path";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../lib/auth";
import {registryCoverageFromSnapshot} from "../../../lib/registry-benefit-coverage";

export const runtime="nodejs";
export const dynamic="force-dynamic";
export const maxDuration=15;
const headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"};

export async function GET(req:NextRequest){
  if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error:"Authentication required"},{status:401,headers});
  if(req.nextUrl.searchParams.size!==0)
    return NextResponse.json({error:"Unexpected parameters"},{status:422,headers});
  try{
    const snapshot=JSON.parse(await readFile(
      join(process.cwd(),"data","registry-benefit-research-snapshot.json"),"utf8"));
    return NextResponse.json(registryCoverageFromSnapshot(snapshot),{headers});
  }catch{
    return NextResponse.json({error:"Current source coverage is not available. Unverified research stays unassessed."},{status:503,headers});
  }
}
