import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../../lib/auth";
import pilot from "../../../../data/acacia-pilot-prediction-workup-20261108.json";
import {ACACIA_NCT,pinnedSourceUrls,registryIdentityValid,publicationIdentityValid,
 evaluateSourceRefresh,type Probe} from "../../../../lib/acacia-live-evidence-refresh";

export const runtime="nodejs";
export const dynamic="force-dynamic";
const headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"};

async function readBoundedJson(response:Response):Promise<unknown>{
  if(!response.ok||!response.headers.get("content-type")?.toLowerCase().includes("json"))
    throw Error("SOURCE_NOT_JSON");
  const size=Number(response.headers.get("content-length")??0);
  if(size>350_000)throw Error("SOURCE_TOO_LARGE");
  const reader=response.body?.getReader();
  if(!reader)throw Error("MISSING_BODY");
  let total=0;
  const parts:Uint8Array[]=[];
  try{
    while(true){
      const {done,value}=await reader.read();
      if(done)break;
      total+=value.byteLength;
      if(total>350_000)throw Error("SOURCE_TOO_LARGE");
      parts.push(value);
    }
  }finally{await reader.cancel().catch(()=>undefined);}
  const bytes=new Uint8Array(total);
  let offset=0;
  for(const part of parts){bytes.set(part,offset);offset+=part.length;}
  return JSON.parse(new TextDecoder().decode(bytes)) as unknown;
}

async function probeSource(
  sourceId:"REGISTRY"|"NEJM_PIVOTAL",
  check:(input:unknown)=>boolean,
  force:boolean,observedAt:string
):Promise<Probe>{
  const sourceUrl=pinnedSourceUrls[sourceId];
  try{
    // Only hardcoded, official public API URLs. Never accept a URL from user
    // input, cached evidence, the backend or the response body.
    const resp=await fetch(sourceUrl,{
      headers:{"Accept":"application/json","User-Agent":"MAIN-Acacia-Research-Preview/1.0"},
      redirect:"error",signal:AbortSignal.timeout(10000),
      ...(force?{cache:"no-store" as const}:{next:{revalidate:900}}),
    });
    const body=await readBoundedJson(resp);
    return {sourceId,status:check(body)?"MATCH":"CHANGED",observedAt,sourceUrl,
      message:check(body)?"Exact public source identity matches the pinned pilot":"Public source identity differs; require evidence review"};
  }catch{
    return {sourceId,status:"UNAVAILABLE",observedAt,sourceUrl,
      message:"Public source could not be rechecked; original dated evidence unchanged"};
  }
}
export async function GET(req:NextRequest){
  if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error:"Authentication required"},{status:401,headers});
  const q=req.nextUrl.searchParams;
  if(q.get("nct")!==ACACIA_NCT||q.getAll("nct").length!==1||
     [...q.keys()].some(k=>!["nct","refresh"].includes(k))||
     (q.has("refresh")&&q.get("refresh")!=="1"))
    return NextResponse.json({error:"Exact pilot NCT required"},{status:422,headers});
  const observedAt=new Date().toISOString();
  const force=q.get("refresh")==="1";
  const probes=await Promise.all([
    probeSource("REGISTRY",registryIdentityValid,force,observedAt),
    probeSource("NEJM_PIVOTAL",publicationIdentityValid,force,observedAt)
  ]);
  const report=evaluateSourceRefresh(pilot,probes,observedAt);
  if(!report)return NextResponse.json({error:"Research evidence state is invalid; provisional update withheld"},
    {status:503,headers});
  return NextResponse.json(report,{headers});
}
