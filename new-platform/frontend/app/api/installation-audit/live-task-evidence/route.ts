import { NextResponse } from "next/server";
import { masterBuildTasks } from "../../../installation-audit/master-build-tasks";
import { readFile } from "node:fs/promises";
import { join } from "node:path";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
type Status = "Verified"|"In Progress"|"Blocked"|"Failed"|"Not Started"|"Unverified";
type Evidence = {status:Status;checkedAt?:string;evidenceUrl?:string;note?:string};
const ids = masterBuildTasks.flatMap((section,i)=>section.map((_,j)=>
  String(i+1).padStart(2,"0")+"-"+String(j+1).padStart(3,"0")));
export async function GET(request: Request) {
 const checkedAt = new Date().toISOString();
 const origin = new URL(request.url).origin;
 let saved: {tasks?:Record<string,Evidence>;updatedAt?:string} = {};
 try {
  const raw=await readFile(join(process.cwd(),"public","installation-audit","task-evidence.json"),"utf8");
  saved=JSON.parse(raw);
 } catch {
  return NextResponse.json({error:"Evidence registry unavailable",checkedAt},{status:503,headers:{"Cache-Control":"no-store"}});
 }
 const tasks:Record<string,Evidence>={};
 for(const id of ids) tasks[id]=saved.tasks?.[id]??{status:"Unverified"};
 const checks:Record<string,{status:string;httpStatus?:number;checkedAt:string;note:string}>={};
 for(const [name,path] of [["dashboard","/installation-audit"],["scanHealth","/api/main-phase3-nightly-health"]]) {
  try {
   const response=await fetch(origin+path,{method:"GET",cache:"no-store",signal:AbortSignal.timeout(6000)});
   checks[name]={status:response.ok?"reachable":"http_error",httpStatus:response.status,checkedAt,note:response.status===401||response.status===403?"Endpoint is protected; anonymous health cannot be verified.":"Connectivity only; not acceptance or scan completion."};
  } catch {
   checks[name]={status:"unreachable",checkedAt,note:"Request failed or timed out; does not establish root cause."};
  }
 }
 // Runtime failures do not erase previously dated acceptance evidence. Live checks
 // are observations only; no requirement is auto-certified without a test contract.
 const counts=ids.reduce((acc,id)=>{const status=tasks[id].status;acc[status]=(acc[status]??0)+1;return acc;},{} as Record<string,number>);
 return NextResponse.json({schemaVersion:1,checkedAt,registryUpdatedAt:saved.updatedAt,taskCount:ids.length,counts,tasks,checks,automatedAcceptanceCoverage:0,unverifiedCount:counts.Unverified??0,verifiedCount:counts.Verified??0,liveChecksPassing:Object.values(checks).filter(check=>check.status==="reachable").length,liveChecksTotal:Object.keys(checks).length,notice:"Live observations are separate from task-specific acceptance evidence. Unverified does not mean incomplete."},{headers:{"Cache-Control":"no-store, max-age=0"}});
}
