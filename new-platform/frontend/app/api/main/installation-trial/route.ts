import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../../lib/auth";
export const runtime="nodejs";
export const dynamic="force-dynamic";
const headers={"Cache-Control":"private, no-store"} as const;
const reply=(data:unknown,status=200)=>NextResponse.json(data,{status,headers});
const nctRx=/^NCT[0-9]{8}$/;
const object=(v:unknown):Record<string,unknown>=>v&&typeof v==="object"&&!Array.isArray(v)?v as Record<string,unknown>:{};
export async function GET(req:NextRequest){
 if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))return reply({error:"Sign in required"},401);
 const nct=req.nextUrl.searchParams.get("nct");
 if(!nct||!nctRx.test(nct))return reply({error:"Valid exact NCT required"},422);
 const base=(process.env.PDUFA_MONITOR_API_BASE_URL||process.env.PDUFA_API_BASE_URL)?.trim().replace(/\/$/,"");
 const key=(process.env.PDUFA_MONITOR_INTERNAL_KEY||process.env.PDUFA_INTERNAL_API_KEY)?.trim();
 const unavailable=(reason:string)=>reply({nct,available:false,total:0,records:[],reason});
 if(!base?.startsWith("https://")||!key)return unavailable("Medical history service not configured; no history verified");
 try{
  const res=await fetch(base+"/api/analyze-now/"+nct+"/history",{headers:{"X-Pdufa-Internal-Key":key,Accept:"application/json"},cache:"no-store",signal:AbortSignal.timeout(8000)});
  if(!res.ok||!res.headers.get("content-type")?.includes("json"))return unavailable("Persistent research storage or history service unavailable");
  const raw=object(await res.json());
  if(raw.nct!==nct||!Array.isArray(raw.records))return unavailable("Exact-NCT history response not verified");
  const records=raw.records.slice(0,100).map(v=>{
   const row=object(v),report=object(row.analysis);
   const links=Array.isArray(report.supportingSourceUrls)?report.supportingSourceUrls:[];
   const gaps=Array.isArray(report.missingEvidence)?report.missingEvidence:[];
   return {revision:typeof row.revision==="number"?row.revision:null,
     recordedAt:typeof row.savedAt==="string"?row.savedAt:typeof row.recordedAt==="string"?row.recordedAt:null,
     status:typeof row.status==="string"?row.status:"SOURCE_ONLY",
     sourceCount:links.length,gapCount:gaps.length,changed:row.evidenceChanged===true};
  });
  return reply({nct,available:true,total:typeof raw.total==="number"?raw.total:records.length,records});
 }catch{return unavailable("Saved source history could not be retrieved");}
}