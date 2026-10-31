import { NextResponse } from "next/server";
import { masterBuildTasks } from "../../../installation-audit/master-build-tasks";
import evidenceRegistry from "../../../../public/installation-audit/task-evidence.json";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
type Status = "Verified"|"In Progress"|"Blocked"|"Failed"|"Not Started"|"Unverified";
type AcceptanceProof = {result:"PASS"|"FAIL";testId:string;passedAt:string;runtimeEvidenceUrl:string;deployedCommit:string};
type Evidence = {status:Status;checkedAt?:string;evidenceUrl?:string;note?:string;acceptance?:string;acceptanceMissing?:string[];acceptanceProof?:AcceptanceProof};
function hasTaskAcceptance(row:Evidence):boolean {
 const proof=row.acceptanceProof;
 if (!proof || proof.result!=="PASS" || !proof.testId?.trim()) return false;
 if (!Number.isFinite(Date.parse(proof.passedAt))) return false;
 if (!/^https:\/\//.test(proof.runtimeEvidenceUrl)) return false;
 if (!/^[a-f0-9]{40}$/.test(proof.deployedCommit)) return false;
 return true;
}
const ids = masterBuildTasks.flatMap((section,i)=>section.map((_,j)=>
  String(i+1).padStart(2,"0")+"-"+String(j+1).padStart(3,"0")));
export async function GET(request: Request) {
 const checkedAt = new Date().toISOString();
 const origin = new URL(request.url).origin;
 const saved = evidenceRegistry as {tasks?:Record<string,Evidence>;updatedAt?:string};
 const tasks:Record<string,Evidence>={};
 const rejectedVerified:string[]=[];
 for(const id of ids) {
  const candidate=saved.tasks?.[id];
  if (candidate?.status==="Verified" && !hasTaskAcceptance(candidate)) {
   // Historical implementation evidence remains visible but is not certification.
   rejectedVerified.push(id);
   tasks[id]={...candidate,status:"In Progress",acceptance:"NOT_ACCEPTED",
    acceptanceMissing:candidate.acceptanceMissing?.length?candidate.acceptanceMissing:["Provide dated, task-specific production acceptance proof"]};
  } else {
   tasks[id]=candidate??{status:"Unverified"};
  }
 }
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
 // Non-mutating, bounded sample checks for the protected PDUFA research API.
 // Never interpret HTTP 200 as a completed scientific assessment or a validated FDA forecast.
 const internalKey=process.env.PDUFA_INTERNAL_API_KEY;
 if (backendBase?.startsWith("https://") && internalKey) {
  const nct="NCT00116805";
  const sampleEndpoints=[
   {name:"predictionSafety",path:"/api/phase3-trials/"+nct+"/predictions"},
   {name:"scienceReadiness",path:"/api/phase3-trials/"+nct+"/readiness"},
   {name:"statisticalConsistency",path:"/api/phase3-trials/"+nct+"/statistical-consistency"}
  ];
  await Promise.all(sampleEndpoints.map(async probe=>{
   try {
    const response=await fetch(backendBase+probe.path,{headers:{"X-Pdufa-Internal-Key":internalKey,Accept:"application/json"},cache:"no-store",signal:AbortSignal.timeout(6500)});
    if(!response.ok){checks[probe.name]={status:"http_error",httpStatus:response.status,checkedAt,note:"Protected sample request failed; no acceptance implied."};return;}
    const body=await response.json() as Record<string,unknown>;
    const identity=body.nct_id===nct;
    const shape=probe.name==="predictionSafety"
     ? body.decision==="ABSTAIN"&&body.validated_decision_available===false
     : probe.name==="scienceReadiness"
     ? body.decision==="ABSTAIN"&&Array.isArray(body.decision_pipeline)&&typeof body.checks==="object"
     : body.decision==="ABSTAIN"&&body.adjudication_status==="NOT_ADJUDICATED"&&Array.isArray(body.readiness_blockers);
    checks[probe.name]={status:identity&&shape?"expected_safety_response":"unexpected_response",httpStatus:response.status,checkedAt,note:identity&&shape?"Sample API returned expected abstention/readiness shape; no scientific validation or full workflow acceptance.":"Unexpected response contract; investigate before acceptance."};
   } catch {
    checks[probe.name]={status:"unreachable",checkedAt,note:"Sample API request failed, returned non-JSON, or timed out; full workflow unverified."};
   }
  }));
 } else {
  for(const name of ["predictionSafety","scienceReadiness","statisticalConsistency"])
   checks[name]={status:"not_configured",checkedAt,note:"Protected API credentials unavailable for the audit; no acceptance established."};
 }
 // Map live probes to specific task identifiers as observations ONLY.
 // These do not alter the saved registry or claim that acceptance tests passed.
 const observations:{taskId:string;requirement:string;probe:string;result:string;checkedAt:string;limitation:string}[]=[
  {taskId:"01-003",requirement:"Verify Render backend services",probe:"backendDatabase",result:checks.backendDatabase?.status??"unknown",checkedAt,limitation:"Application and storage health only; deploy/rollback acceptance still unverified."},
  {taskId:"01-004",requirement:"Verify PostgreSQL connectivity",probe:"backendDatabase",result:checks.backendDatabase?.status??"unknown",checkedAt,limitation:"Backend-reported storage readiness; direct database write/restore not tested."},
  {taskId:"01-015",requirement:"Verify dashboard routes and authenticated access",probe:"dashboard",result:checks.dashboard?.status??"unknown",checkedAt,limitation:"One audit route checked; login/session workflow and other routes not exercised."},
  {taskId:"03-001",requirement:"Verify nightly scan schedule",probe:"scanHealth",result:checks.scanHealth?.status??"unknown",checkedAt,limitation:"Health endpoint connectivity only; 8 PM schedule execution not verified."},
  {taskId:"10-021",requirement:"Prevent unsupported definitive predictions",probe:"predictionSafety",result:checks.predictionSafety?.status??"unknown",checkedAt,limitation:"A single abstention sample; no historical model validation or production acceptance."},
  {taskId:"08-060",requirement:"Evaluate clinical trial design and protocol",probe:"scienceReadiness",result:checks.scienceReadiness?.status??"unknown",checkedAt,limitation:"Readiness response contract only; no full scientific investigation or evidence adjudication."},
  {taskId:"08-062",requirement:"Evaluate statistical analysis and multiplicity",probe:"statisticalConsistency",result:checks.statisticalConsistency?.status??"unknown",checkedAt,limitation:"Textual comparison endpoint only; mismatch logic and underlying statistical validity not independently tested."}
 ];
 // Validate every task link against the CURRENT master list. A renamed or moved
 // requirement must not inherit observations from a different task.
 const mappedObservations=observations.map(item=>{
  const [sectionNumber,taskNumber]=item.taskId.split("-").map(Number);
  const masterLabel=masterBuildTasks[sectionNumber-1]?.[taskNumber-1];
  return masterLabel===item.requirement ? {...item,mappingValid:true}
   : {...item,mappingValid:false,result:"mapping_error",limitation:"Task identifier does not match current master inventory; observation must be remapped and must not be accepted."};
 });
 const healthyStatuses=new Set(["reachable","ready","expected_safety_response"]);
 const observationSummary={
  taskLinksChecked:mappedObservations.length,
  taskLinksValid:mappedObservations.filter(item=>item.mappingValid).length,
  probesHealthy:Object.values(checks).filter(check=>healthyStatuses.has(check.status)).length,
  probesTotal:Object.keys(checks).length
 };
 // Runtime failures do not erase previously dated acceptance evidence. Live checks
 // are observations only; no requirement is auto-certified without a test contract.
 const counts=ids.reduce((acc,id)=>{const status=tasks[id].status;acc[status]=(acc[status]??0)+1;return acc;},{} as Record<string,number>);
 return NextResponse.json({schemaVersion:1,checkedAt,registryUpdatedAt:saved.updatedAt,taskCount:ids.length,rejectedVerified,counts,tasks,checks,observations:mappedObservations,observationSummary,automatedAcceptanceCoverage:0,unverifiedCount:counts.Unverified??0,verifiedCount:counts.Verified??0,liveChecksPassing:observationSummary.probesHealthy,liveChecksTotal:Object.keys(checks).length,notice:"Live observations are separate from task-specific acceptance evidence. Unverified does not mean incomplete."},{headers:{"Cache-Control":"no-store, max-age=0"}});
}
