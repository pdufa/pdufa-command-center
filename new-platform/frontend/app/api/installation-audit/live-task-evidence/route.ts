import { NextResponse } from "next/server";
import { masterBuildTasks } from "../../../installation-audit/master-build-tasks";
import evidenceRegistry from "../../../../public/installation-audit/task-evidence.json";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
type Status = "Verified"|"In Progress"|"Blocked"|"Failed"|"Not Started"|"Unverified";
type Evidence = {status:Status;checkedAt?:string;evidenceUrl?:string;note?:string};
const ids = masterBuildTasks.flatMap((section,i)=>section.map((_,j)=>
  String(i+1).padStart(2,"0")+"-"+String(j+1).padStart(3,"0")));
export async function GET(request: Request) {
 const checkedAt = new Date().toISOString();
 const origin = new URL(request.url).origin;
 const saved = evidenceRegistry as {tasks?:Record<string,Evidence>;updatedAt?:string};
 const tasks:Record<string,Evidence>={};
 for(const id of ids) tasks[id]=saved.tasks?.[id]??{status:"Unverified"};
 const checks:Record<string,{status:string;httpStatus?:number;checkedAt:string;note:string}>={};
 for(const [name,path] of [["dashboard","/installation-audit"],["scanHealth","/api/main-phase3-nightly-health"]]) {
  try {
   const response=await fetch(origin+path,{method:"GET",cache:"no-store",signal:AbortSignal.timeout(6000)});
   checks[name]={status:response.status===401||response.status===403?"authentication_required":response.ok?"reachable":"http_error",httpStatus:response.status,checkedAt,note:response.status===401||response.status===403?"Endpoint is protected; anonymous health cannot be verified.":"Connectivity only; not acceptance or scan completion."};
  } catch {
   checks[name]={status:"unreachable",checkedAt,note:"Request failed or timed out; does not establish root cause."};
  }
 }
 // Check the configured backend directly from the server, without exposing its URL or keys.
 // A successful HTTP response alone is insufficient: require the expected service,
 // healthy application state and an affirmative persistent-storage check.
 const backendBase = process.env.PDUFA_API_BASE_URL?.replace(new RegExp("/$"), "");
 if (!backendBase || !backendBase.startsWith("https://")) {
  checks.backendDatabase={status:"not_configured",checkedAt,note:"Backend URL is not configured; database readiness cannot be established."};
 } else {
  try {
   const response=await fetch(backendBase+"/health",{cache:"no-store",signal:AbortSignal.timeout(8000)});
   if (!response.ok) {
    checks.backendDatabase={status:"http_error",httpStatus:response.status,checkedAt,note:"Backend health request failed; storage readiness is unverified."};
   } else {
    const body=await response.json() as {service?:string;status?:string;storage_ready?:boolean};
    const ready=body.service==="pdufa-new-backend"&&body.status==="ok"&&body.storage_ready===true;
    checks.backendDatabase={status:ready?"ready":"not_ready",httpStatus:response.status,checkedAt,note:ready?"Backend health confirms application and persistent storage ready. This is not a database restore or end-to-end acceptance test.":"Backend did not affirm expected service, healthy state and persistent storage readiness."};
   }
  } catch {
   checks.backendDatabase={status:"unreachable",checkedAt,note:"Backend health request failed or timed out; storage readiness unverified."};
  }
 }
 // Map live probes to specific task identifiers as observations ONLY.
 // These do not alter the saved registry or claim that acceptance tests passed.
 const observations:{taskId:string;requirement:string;probe:string;result:string;checkedAt:string;limitation:string}[]=[
  {taskId:"01-003",requirement:"Verify Render backend services",probe:"backendDatabase",result:checks.backendDatabase?.status??"unknown",checkedAt,limitation:"Application and storage health only; deploy/rollback acceptance still unverified."},
  {taskId:"01-004",requirement:"Verify PostgreSQL connectivity",probe:"backendDatabase",result:checks.backendDatabase?.status??"unknown",checkedAt,limitation:"Backend-reported storage readiness; direct database write/restore not tested."},
  {taskId:"01-015",requirement:"Verify dashboard routes and authenticated access",probe:"dashboard",result:checks.dashboard?.status??"unknown",checkedAt,limitation:"One audit route checked; login/session workflow and other routes not exercised."},
  {taskId:"03-001",requirement:"Verify nightly scan schedule",probe:"scanHealth",result:checks.scanHealth?.status??"unknown",checkedAt,limitation:"Health endpoint connectivity only; 8 PM schedule execution not verified."}
 ];
 // Runtime failures do not erase previously dated acceptance evidence. Live checks
 // are observations only; no requirement is auto-certified without a test contract.
 const counts=ids.reduce((acc,id)=>{const status=tasks[id].status;acc[status]=(acc[status]??0)+1;return acc;},{} as Record<string,number>);
 return NextResponse.json({schemaVersion:1,checkedAt,registryUpdatedAt:saved.updatedAt,taskCount:ids.length,counts,tasks,checks,observations,automatedAcceptanceCoverage:0,unverifiedCount:counts.Unverified??0,verifiedCount:counts.Verified??0,liveChecksPassing:Object.values(checks).filter(check=>check.status==="reachable").length,liveChecksTotal:Object.keys(checks).length,notice:"Live observations are separate from task-specific acceptance evidence. Unverified does not mean incomplete."},{headers:{"Cache-Control":"no-store, max-age=0"}});
}
