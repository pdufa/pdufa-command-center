import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../../lib/auth";
import {buildInstallationProgress,type MonitorTelemetry,type ExternalVerification} from "../../../../lib/main-install-progress";

export const runtime="nodejs";
export const dynamic="force-dynamic";
export const maxDuration=30;
const noStore={"Cache-Control":"private, no-store"} as const;
const gitRepo="pdufa/pdufa-command-center";
const SHA=/^[a-f0-9]{40}$/;
const endpoint="/api/internal/installation-monitor";
const rec=(x:unknown):Record<string,unknown>=>
 x&&typeof x==="object"&&!Array.isArray(x)?x as Record<string,unknown>:{};
const array=(x:unknown)=>Array.isArray(x)?x:[];

/** Read-only GitHub Actions provenance, only for an exact Vercel build SHA.
 * A stale success for another commit MUST NOT turn a checkpoint green.
 */
async function readGithub(sha:string|null):Promise<Pick<ExternalVerification,"medicalQa"|"overallCi"|"scheduledScans">>{
 const fallback={
  medicalQa:"unknown" as const,overallCi:"unknown" as const,
  scheduledScans:{state:"unknown" as const,at:null,url:null}
 };
 const headers:Record<string,string>={Accept:"application/vnd.github+json",
    "X-GitHub-Api-Version":"2022-11-28","User-Agent":"PDUFA-installation-health"};
 const token=process.env.PDUFA_GITHUB_READ_TOKEN?.trim();
 if(token)headers.Authorization="Bearer "+token;
 const fetchRuns=async(q:string)=>{
  const response=await fetch("https://api.github.com/repos/"+gitRepo+"/actions/runs?"+q,{
    headers,next:{revalidate:120},signal:AbortSignal.timeout(6000)
  });
  if(!response.ok)throw Error("GitHub Actions not accessible");
  return array(rec(await response.json()).workflow_runs);
 };
 const [commit,scheduled]=await Promise.allSettled([
  sha?fetchRuns("head_sha="+sha+"&per_page=100"):Promise.resolve([]),
  fetchRuns("event=schedule&per_page=50")
 ]);
 const evaluation=(name:string)=>{
  if(!sha||commit.status!=="fulfilled")return "unknown" as const;
  const matched=commit.value.filter(x=>rec(x).head_sha===sha&&
    rec(x).name===name).sort((a,b)=>String(rec(b).created_at).localeCompare(String(rec(a).created_at)));
  if(!matched.length)return "unknown" as const;
  const selected=rec(matched[0]);
  return selected.status!=="completed"?"pending" as const:
    selected.conclusion==="success"?"success" as const:
    selected.conclusion==="failure"?"failure" as const:"unknown" as const;
 };
 const scheduledCandidates=scheduled.status==="fulfilled"?
  scheduled.value.filter(x=>/scan|ingestion|trial|nct|pipeline|medical|evidence/i.test(String(rec(x).name??""))&&
    rec(x).event==="schedule").sort((a,b)=>String(rec(b).created_at).localeCompare(String(rec(a).created_at))):[];
 const latest=scheduledCandidates.length?rec(scheduledCandidates[0]):null;
 const scanState:ExternalVerification["scheduledScans"]["state"]=latest?
  latest.status!=="completed"?"running":
  latest.conclusion==="success"?"success":
  latest.conclusion==="failure"?"failure":"unknown":"unknown";
 return {
  medicalQa:evaluation("Deep Medical Intelligence Preview QA"),
  overallCi:evaluation("PDUFA Command Center CI"),
  scheduledScans:{state:scanState,
   at:typeof latest?.created_at==="string"?latest.created_at:null,
   url:typeof latest?.html_url==="string"?latest.html_url:null}
 };
}
async function backendSnapshot():Promise<{live:MonitorTelemetry|null;apiReachable:boolean}>{
 const base=process.env.PDUFA_API_BASE_URL?.trim().replace(/\/$/,"");
 const key=process.env.PDUFA_INTERNAL_API_KEY?.trim();
 if(!base?.startsWith("https://")||!key)return {live:null,apiReachable:false};
 try{
  const response=await fetch(base+endpoint,{
    headers:{Accept:"application/json","X-Pdufa-Internal-Key":key},
    cache:"no-store",signal:AbortSignal.timeout(8500)
  });
  if(!response.ok||!response.headers.get("content-type")?.includes("json"))
    return {live:null,apiReachable:false};
  const data:unknown=await response.json();
  if(rec(data).schemaVersion!==1||typeof rec(data).observedAt!=="string")
    return {live:null,apiReachable:false};
  return {live:data as MonitorTelemetry,apiReachable:true};
 }catch{return {live:null,apiReachable:false};}
}

export async function GET(req:NextRequest){
 if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
  return NextResponse.json({error:"Sign in required"},{status:401,headers:noStore});
 const rawSha=process.env.VERCEL_GIT_COMMIT_SHA??"";
 const sha=SHA.test(rawSha)?rawSha:null;
 const frontendReady=Boolean(sha&&process.env.VERCEL_ENV&&process.env.VERCEL_URL);
 const url=frontendReady&&/^[a-z0-9.-]+$/i.test(process.env.VERCEL_URL??"")?
  "https://"+process.env.VERCEL_URL:null;
 const [backend,github]=await Promise.all([backendSnapshot(),readGithub(sha)]);
 const now=new Date().toISOString();
 const verification:ExternalVerification={
  observedAt:now,
  deployment:{state:frontendReady?"READY":"UNKNOWN",sha,url},
  apiReachable:backend.apiReachable,
  analyzeNowAllEnabled:process.env.PDUFA_ANALYZE_NOW_ALL_ENABLED==="true",
  ...github
 };
 const snapshot=buildInstallationProgress(backend.live,verification,now);
 return NextResponse.json(snapshot,{headers:noStore});
}
