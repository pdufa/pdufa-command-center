import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../../lib/auth";

export const runtime="nodejs";
export const dynamic="force-dynamic";
export const maxDuration=15;
const headers={"Cache-Control":"private, no-store"};
const reply=(data:unknown,status=200)=>NextResponse.json(data,{status,headers});

type Preflight={enabled?:unknown;persistentStorageReady?:unknown;sourceWorkerReady?:unknown;canaryNct?:unknown};
export async function GET(req:NextRequest){
 if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
   return reply({ready:false,error:"Sign in required"},401);
 const base=process.env.PDUFA_API_BASE_URL?.trim().replace(/\/$/,"");
 const key=process.env.PDUFA_INTERNAL_API_KEY?.trim();
 if(!base?.startsWith("https://")||!key)
   return reply({ready:false,error:"Isolated medical backend not connected"},503);
 try{
   const response=await fetch(base+"/api/internal/medical-canary-preflight",{
     method:"GET",cache:"no-store",signal:AbortSignal.timeout(12000),
     headers:{"X-Pdufa-Internal-Key":key,"Accept":"application/json"}
   });
   if(!response.ok||!response.headers.get("content-type")?.includes("json"))
     return reply({ready:false,error:"Medical preflight unavailable"},503);
   const raw:unknown=await response.json();
   if(!raw||typeof raw!=="object"||Array.isArray(raw))
     return reply({ready:false,error:"Unexpected medical preflight response"},503);
   const data=raw as Preflight;
   const storageReady=data.persistentStorageReady===true;
   const workerReady=data.sourceWorkerReady===true;
   const enabled=data.enabled===true;
   const ready=enabled&&storageReady&&workerReady;
   return reply({
     ready,enabled,storageReady,workerReady,
     canaryNct:typeof data.canaryNct==="string"&&/^NCT\d{8}$/.test(data.canaryNct)
       ? data.canaryNct:null,
     status:ready?"CANARY_READY":"BLOCKED",
     prediction:"ABSTAIN",certainty:"NOT_VALIDATED"
   },ready?200:503);
 }catch{
   return reply({ready:false,error:"Medical preflight could not be reached"},503);
 }
}
