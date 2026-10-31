"use client";
import {useEffect,useState} from "react";
import {masterBuildTasks} from "./master-build-tasks";
const segments=[
["Infrastructure & deployment","Verify live production SHA, Vercel status, Render service, authentication, recovery"],
["Database & ingestion","Verify canonical trial identities, FDA/SEC/financial sources, freshness, backup/restore"],
["Automated scans","Verify 8 PM Pacific schedule, sequential runs, duplicate guard, RESULTS and retries"],
["Pipeline","Audit $300M–$10B, public, US FDA, Phase 3, active program, documented filters and counts"],
["GEM JR","Audit independent ranking, evidence and original FS/FA preset associations"],
["GEM","Audit independent stricter ranking, evidence and original FS/FA preset associations"],
["Special designations","Verify FDA designation types, original grant dates, citations and icons"],
["SCIENCE","Audit 8 layers, 40 assessments, uncertainty, readiness and complete trial evidence"],
["OUTCOME","Verify review-cycle labels, PASS/CRL/EXTENSION, dates and calibrated validation"],
["MAIN","Audit 31 Core Platform gates, 10 technical prerequisites and decision integration"],
["Predictions page","Build input flowchart, historical/current/future lanes, candidates and collapsed details"],
["Historical validation","Held-out FDA decisions, leakage prevention, accuracy and uncertainty"],
["Dashboard & charts","Verify mobile layout, source health, timeline, matrices and chart rendering"],
["Notifications","Verify scan start/end email and SMS delivery with failure handling"],
["Final acceptance","Authenticated end-to-end acceptance, backup restore and release signoff"]
];
type TaskStatus="Verified"|"In Progress"|"Blocked"|"Failed"|"Not Started"|"Unverified";
type TaskEvidence={status:TaskStatus;checkedAt?:string;evidenceUrl?:string;note?:string};
type TaskRegistry={updatedAt:string;tasks:Record<string,TaskEvidence>};
type LiveObservation={taskId:string;requirement:string;probe:string;result:string;checkedAt:string;limitation:string;mappingValid?:boolean};
type LiveAudit={checkedAt:string;registryUpdatedAt?:string;tasks:Record<string,TaskEvidence>;checks?:Record<string,{status:string;httpStatus?:number;note:string}>;observations?:LiveObservation[];observationSummary?:{taskLinksChecked:number;taskLinksValid:number;probesHealthy:number;probesTotal:number};taskCount?:number};
type Observation={status:string};
type Snapshot={asOf:string;recordedAt?:string;observations?:Observation[]};
const source="https://raw.githubusercontent.com/pdufa/pdufa-command-center/main/new-platform/frontend/data/mainDailyEvidenceSnapshots.json";
export default function MasterBuildProgress(){
 const [snap,setSnap]=useState<Snapshot|null>(null);
 const [registry,setRegistry]=useState<TaskRegistry|null>(null);
 const [checked,setChecked]=useState("");
 const [error,setError]=useState(false);
 const [refreshToken,setRefreshToken]=useState(0);
 const [loading,setLoading]=useState(false);
 const [liveHealth,setLiveHealth]=useState<string>("Not checked");
 const [liveChecks,setLiveChecks]=useState<Record<string,{status:string;httpStatus?:number;note:string}>>({});
 const [operationalObservations,setOperationalObservations]=useState<LiveObservation[]>([]);
 const [observationSummary,setObservationSummary]=useState<{taskLinksChecked:number;taskLinksValid:number;probesHealthy:number;probesTotal:number}|null>(null);
 useEffect(()=>{let active=true;async function refresh(){if(active)setLoading(true);try{
 const [snapshotResult,auditResult]=await Promise.allSettled([
  fetch(source+"?t="+Date.now(),{cache:"no-store"}).then(async res=>{if(!res.ok)throw Error("snapshot unavailable");const data=await res.json() as Snapshot[];const latest=data.at(-1);if(!latest||!Array.isArray(latest.observations))throw Error("invalid snapshot");return latest;}),
  fetch("/api/installation-audit/live-task-evidence?t="+Date.now(),{cache:"no-store"}).then(async res=>{if(!res.ok)throw Error("task evidence unavailable");return await res.json() as LiveAudit;})
 ]);
 if(active){
  if(snapshotResult.status==="fulfilled")setSnap(snapshotResult.value);
  if(auditResult.status==="fulfilled"&&auditResult.value.tasks&&typeof auditResult.value.tasks==="object"){
   const audit=auditResult.value;
   setRegistry({updatedAt:audit.registryUpdatedAt??audit.checkedAt,tasks:audit.tasks});
   setLiveHealth(audit.checks?.scanHealth?.status??"Not checked");
   setLiveChecks(audit.checks??{});
   setOperationalObservations(Array.isArray(audit.observations)?audit.observations:[]);
   setObservationSummary(audit.observationSummary??null);
  }
  setError(snapshotResult.status==="rejected"||auditResult.status==="rejected");
  setChecked(new Date().toLocaleString());setLoading(false);
 }
 }catch{if(active){setError(true);setChecked(new Date().toLocaleString());setLoading(false);}}}refresh();const timer=setInterval(refresh,30*60*1000);return()=>{active=false;clearInterval(timer)}},[refreshToken]);
 const allTasks=masterBuildTasks.flatMap((items,i)=>items.map((task,j)=>({id:`${String(i+1).padStart(2,"0")}-${String(j+1).padStart(3,"0")}`,task})));
 const taskStatus=(id:string):TaskEvidence=>registry?.tasks[id]??{status:"Unverified"};
 const verifiedTasks=allTasks.filter(t=>taskStatus(t.id).status==="Verified").length;
 const blockedTasks=allTasks.filter(t=>taskStatus(t.id).status==="Blocked").length;
 const progressTasks=allTasks.filter(t=>taskStatus(t.id).status==="In Progress").length;
 const failedTasks=allTasks.filter(t=>taskStatus(t.id).status==="Failed").length;
 const unverifiedTasks=allTasks.filter(t=>taskStatus(t.id).status==="Unverified").length;
 const notStartedTasks=allTasks.filter(t=>taskStatus(t.id).status==="Not Started").length;
 const nextAuditQueue=segments.map(([section],i)=>{
  const taskIndex=masterBuildTasks[i]?.findIndex((_,j)=>taskStatus(`${String(i+1).padStart(2,"0")}-${String(j+1).padStart(3,"0")}`).status!=="Verified")??-1;
  if(taskIndex<0)return null;
  const id=`${String(i+1).padStart(2,"0")}-${String(taskIndex+1).padStart(3,"0")}`;
  return {section,id,task:masterBuildTasks[i][taskIndex],status:taskStatus(id).status,sectionId:"audit-segment-"+String(i+1).padStart(2,"0")};
 }).filter((item):item is {section:string;id:string;task:string;status:TaskStatus;sectionId:string}=>item!==null);
 const verifiedWithEvidence=allTasks.filter(t=>taskStatus(t.id).status==="Verified"&&Boolean(taskStatus(t.id).evidenceUrl)&&Boolean(taskStatus(t.id).checkedAt)).length;
 const verified=snap?.observations?.filter(o=>o.status==="Verified").length;
 const total=snap?.observations?.length;
 return <section aria-label="Master build progress" style={{border:"2px solid #334155",borderRadius:12,padding:18,margin:"22px 0",background:"#f8fafc"}}>
 <h2 style={{marginTop:0}}>BUILD PROGRESS · 15 segments</h2>
 <button type="button" onClick={()=>setRefreshToken(x=>x+1)} disabled={loading} style={{padding:"10px 16px",borderRadius:8,background:"#0f766e",color:"white",border:0,fontWeight:700,cursor:loading?"wait":"pointer"}}>{loading?"Checking saved evidence…":"🔄 Update Progress Now"}</button>
 <p><strong>Refresh check:</strong> every 30 minutes while this page is open. This reads the latest committed evidence snapshot and performs live connectivity observations; it does not certify task acceptance or automatically update GitHub. A new snapshot is visible only after it is committed. {checked?"Last checked: "+checked+". ":""}{error?"Latest fetch failed; previous results may be stale.":""}</p>
 <p><strong>Master task verification:</strong> {verifiedTasks} / {allTasks.length} verified ({(100*verifiedTasks/allTasks.length).toFixed(1)}%) · {progressTasks} in progress · {blockedTasks} blocked · {failedTasks} failed · {notStartedTasks} not started · {unverifiedTasks} unverified. Evidence registry: {registry?.updatedAt??"loading"}. Unverified does not mean unfinished.</p>
 <p><strong>Recorded acceptance evidence:</strong> {verifiedWithEvidence} of {verifiedTasks} verified tasks have both a dated check and evidence link. Unverified tasks are not automatically failed or completed.</p>
 <details style={{margin:"12px 0",padding:12,border:"1px solid #94a3b8",borderRadius:8}}><summary style={{fontWeight:700,cursor:"pointer"}}>NEXT VERIFICATION QUEUE — one outstanding task per segment ({nextAuditQueue.length})</summary>
 <p>These are inventory priorities, not evidence that the work is unimplemented. Verify code, operation, acceptance test and dated proof before marking a task complete.</p>
 <ol>{nextAuditQueue.map(item=><li key={item.id}><a href={"#"+item.sectionId}><strong>{item.id} · {item.section}</strong></a>: {item.task} — {item.status}</li>)}</ol>
 </details>
 <p><strong>Live scan-health endpoint:</strong> {liveHealth}. This is a connectivity check, not acceptance evidence or a completed scan.</p>
 <div aria-label="Live operational connectivity checks" style={{border:"1px solid #94a3b8",padding:12,borderRadius:8,margin:"12px 0"}}><strong>LIVE / NOT LIVE — runtime checks</strong><p>These results show endpoint reachability only. Authentication required means access is protected, not that a scan failed.</p>{Object.keys(liveChecks).length===0?<p>Checks not available yet.</p>:Object.entries(liveChecks).map(([name,check])=><p key={name}><strong>{name}:</strong> {check.status==="reachable"?"LIVE (reachable)":check.status==="authentication_required"?"AUTHENTICATION REQUIRED":check.status==="unreachable"?"NOT REACHABLE":check.status==="http_error"?"HTTP ERROR":check.status==="expected_safety_response"?"EXPECTED SAFETY RESPONSE":check.status==="unexpected_response"?"UNEXPECTED RESPONSE":check.status==="ready"?"BACKEND/STORAGE HEALTHY":check.status==="not_ready"?"BACKEND/STORAGE NOT READY":check.status==="not_configured"?"NOT CONFIGURED":"UNKNOWN"} {check.httpStatus?"("+check.httpStatus+")":""} — {check.note}</p>)}</div>
 <details style={{margin:"12px 0",padding:12,border:"1px solid #94a3b8",borderRadius:8}}><summary style={{cursor:"pointer",fontWeight:700}}>TASK-LINKED LIVE OBSERVATIONS ({operationalObservations.length}) — not acceptance</summary>
 <p>Current connectivity signals are linked to specific task IDs. They may help prioritize verification, but never increase the completed count or replace an acceptance test.</p>
 {observationSummary && <p><strong>Probe responses:</strong> {observationSummary.probesHealthy}/{observationSummary.probesTotal} returned an expected operational result. <strong>Task mappings:</strong> {observationSummary.taskLinksValid}/{observationSummary.taskLinksChecked} matched the current master inventory. Neither number certifies installation completion.</p>}
 {operationalObservations.length===0?<p>No task-linked operational probes available.</p>:<ul>{operationalObservations.map(item=><li key={item.taskId} style={{marginBottom:10}}><strong>{item.taskId}: {item.requirement}</strong> · {item.mappingValid===false?"TASK MAPPING ERROR":item.result.replaceAll("_"," ")} · checked {item.checkedAt}<p style={{margin:"3px 0"}}>{item.limitation}</p></li>)}</ul>}
 </details>
 <p><strong>MAIN Core Platform:</strong> {total?verified+" / "+total+" gates verified ("+(100*(verified||0)/total).toFixed(1)+"%)":"Loading verified snapshot…"} · Evidence date: {snap?.asOf||"unknown"}. SCIENCE and OUTCOME: <strong>not independently measured</strong>. Overall completion: <strong>not certified</strong>.</p>
 <p><a href="https://github.com/pdufa/pdufa-command-center/blob/main/docs/MASTER_BUILD_PROGRESS_2026-10-30.md" target="_blank" rel="noopener noreferrer">Full master task document and acceptance rules ↗</a></p>
 {segments.map(([name,detail],i)=><details id={"audit-segment-"+String(i+1).padStart(2,"0")} key={name} style={{padding:"10px 0",borderTop:"1px solid #cbd5e1"}}><summary style={{cursor:"pointer",fontWeight:650}}>{String(i+1).padStart(2,"0")} · {name} — verification open</summary><p>{detail}.</p><p style={{fontSize:13}}><strong>{masterBuildTasks[i]?.length ?? 0} itemized tasks</strong> · {masterBuildTasks[i]?.filter((_,j)=>taskStatus(`${String(i+1).padStart(2,"0")}-${String(j+1).padStart(3,"0")}`).status==="Verified").length??0} verified. Each task requires dated acceptance evidence. The list is a work inventory, not a claim that every task is running.</p><ol style={{paddingLeft:24}}>{(masterBuildTasks[i] ?? []).map((task,j)=><li key={j} style={{padding:"5px 0"}}><span style={{color:taskStatus(`${String(i+1).padStart(2,"0")}-${String(j+1).padStart(3,"0")}`).status==="Verified"?"#047857":"#92400e",fontWeight:700}}> {taskStatus(`${String(i+1).padStart(2,"0")}-${String(j+1).padStart(3,"0")}`).status==="Verified"?"✓":"○"} </span><strong style={{fontSize:11}}>{`${String(i+1).padStart(2,"0")}-${String(j+1).padStart(3,"0")}`}</strong> {task} <small style={{color:"#64748b"}}>— {taskStatus(`${String(i+1).padStart(2,"0")}-${String(j+1).padStart(3,"0")}`).status}</small>{taskStatus(`${String(i+1).padStart(2,"0")}-${String(j+1).padStart(3,"0")}`).evidenceUrl?<a href={taskStatus(`${String(i+1).padStart(2,"0")}-${String(j+1).padStart(3,"0")}`).evidenceUrl} target="_blank" rel="noopener noreferrer"> Evidence ↗</a>:null}</li>)}</ol><p style={{fontSize:12}}>Completion requires code, production runtime, acceptance test and dated source evidence. Existing historical audits remain in the linked detailed document.</p></details>)}
 </section>
}