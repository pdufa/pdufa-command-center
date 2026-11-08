import {NextRequest,NextResponse} from "next/server";
import focus from "../../../data/p3PostDataActive.json";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../lib/auth";

export const runtime="nodejs";
export const dynamic="force-dynamic";
export const maxDuration=30;
const noStore={"Cache-Control":"private, no-store"} as const;
const NCT=/^NCT\d{8}$/;
const UUID=/^[a-f0-9]{8}-[a-f0-9]{4}-[1-8][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i;
const json=(data:unknown,status=200)=>NextResponse.json(data,{status,headers:noStore});
const authorized=(req:NextRequest)=>authConfigured()&&hasSession(req.cookies.get(COOKIE_NAME)?.value);
const eligible=(nct:unknown):nct is string=>
  typeof nct==="string"&&NCT.test(nct)&&focus.records.some(r=>r.nct===nct);
const pilotAllowed=(nct:string)=>process.env.PDUFA_ANALYZE_NOW_ALL_ENABLED==="true"||
  nct===(process.env.PDUFA_ANALYZE_NOW_CANARY_NCT||"NCT06081894");
async function upstream(path:string,method:"GET"|"POST",body?:object){
 const base=process.env.PDUFA_API_BASE_URL?.trim().replace(/\/$/,"");
 const key=process.env.PDUFA_INTERNAL_API_KEY?.trim();
 if(!base?.startsWith("https://")||!key)
   return json({error:"Isolated medical backend not connected"},503);
 try{
  const response=await fetch(base+path,{
   method,cache:"no-store",signal:AbortSignal.timeout(24000),
   headers:{"X-Pdufa-Internal-Key":key,Accept:"application/json",
     ...(body?{"Content-Type":"application/json"}:{})},
   ...(body?{body:JSON.stringify(body)}:{})
  });
  if(!response.headers.get("content-type")?.toLowerCase().includes("json"))
    return json({error:"Unexpected Analyze Now service response"},503);
  const data:unknown=await response.json();
  if(!response.ok){
   const detail=data&&typeof data==="object"&&"detail" in data
     ?(data as {detail?:unknown}).detail:null;
   const msg=typeof detail==="string"?detail:"Analyze Now backend unavailable";
   const database=msg.startsWith("Persistent PostgreSQL is not connected");
   return json({error:database?
     "Preview backend is live but PostgreSQL is not configured; no analysis was started.":msg},
     response.status===404?404:response.status===422?422:response.status===409?409:503);
  }
  return json(data);
 }catch{return json({error:"Analyze Now service is temporarily unavailable; no analysis was claimed complete."},503);}
}

/** Viewing history or the latest saved report never creates a new analysis. */
export async function GET(req:NextRequest){
 if(!authorized(req))return json({error:"Sign in required"},401);
 const nct=req.nextUrl.searchParams.get("nct");
 const history=req.nextUrl.searchParams.get("history");
 // Historical exact NCTs remain accessible after the trial leaves FOCUS.
 if(!nct||!NCT.test(nct)||(history!==null&&history!=="1"))
   return json({error:"Valid exact trial NCT required"},422);
 return upstream("/api/analyze-now/"+nct+"/"+(history==="1"?"history":"latest"),"GET");
}

/** Explicit same-origin operator click; strict canary until pilot passes live. */
export async function POST(req:NextRequest){
 if(!authorized(req))return json({error:"Sign in required"},401);
 if(req.headers.get("origin")!==req.nextUrl.origin)
   return json({error:"Same-origin operator action required"},403);
 if(!req.headers.get("content-type")?.toLowerCase().startsWith("application/json"))
   return json({error:"JSON body required"},415);
 if(Number(req.headers.get("content-length")||0)>1500)
   return json({error:"Analyze Now request exceeds size limit"},413);
 const body:unknown=await req.json().catch(()=>null);
 if(!body||typeof body!=="object"||Array.isArray(body))
   return json({error:"Invalid request"},422);
 const {nct,requestKey}=body as Record<string,unknown>;
 if(!eligible(nct)||typeof requestKey!=="string"||!UUID.test(requestKey))
   return json({error:"Exact eligible FOCUS NCT and UUID request key required"},422);
 if(!pilotAllowed(nct))
   return json({error:"Analyze Now is limited to the canary trial pending a verified database-backed pilot."},409);
 return upstream("/api/analyze-now/"+nct+"/runs","POST",{request_key:requestKey});
}
