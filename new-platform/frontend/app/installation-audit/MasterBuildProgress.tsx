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
type LiveAudit={checkedAt:string;registryUpdatedAt?:string;tasks:Record<string,TaskEvidence>;checks?:Record<string,{status:string;httpStatus?:number;note:string}>;taskCount?:number};
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
 const verified=snap?.observations?.filter(o=>o.status==="Verified").length;
 const total=snap?.observations?.length;
 return <section aria-label="Master build progress" style={{border:"2px solid #334155",borderRadius:12,padding:18,margin:"22px 0",background:"#f8fafc"}}>
 <h2 style={{marginTop:0}}>BUILD PROGRESS · 15 segments</h2>
 <button type="button" onClick={()=>setRefreshToken(x=>x+1)} disabled={loading} style={{padding:"10px 16px",borderRadius:8,background:"#0f766e",color:"white",border:0,fontWeight:700,cursor:loading?"wait":"pointer"}}>{loading?"Checking saved evidence…":"🔄 Update Progress Now"}</button>
 <p><strong>Refresh check:</strong> every 30 minutes while this page is open. This reads the latest committed evidence snapshot and performs live connectivity observations; it does not certify task acceptance or automatically update GitHub. A new snapshot is visible only after it is committed. {checked?"Last checked: "+checked+". ":""}{error?"Latest fetch failed; previous results may be stale.":""}</p>
 <p><strong>Master task verification:</strong> {verifiedTasks} / {allTasks.length} verified ({(100*verifiedTasks/allTasks.length).toFixed(1)}%) · {progressTasks} in progress · {blockedTasks} blocked · {failedTasks} failed · {notStartedTasks} not started · {unverifiedTasks} unverified. Evidence registry: {registry?.updatedAt??"loading"}. Unverified does not mean unfinished.</p>
 <p><strong>Live scan-health endpoint:</strong> {liveHealth}. This is a connectivity check, not acceptance evidence or a completed scan.</p>
 <p><strong>MAIN Core Platform:</strong> {total?verified+" / "+total+" gates verified ("+(100*(verified||0)/total).toFixed(1)+"%)":"Loading verified snapshot…"} · Evidence date: {snap?.asOf||"unknown"}. SCIENCE and OUTCOME: <strong>not independently measured</strong>. Overall completion: <strong>not certified</strong>.</p>
 <p><a href="https://github.com/pdufa/pdufa-command-center/blob/main/docs/MASTER_BUILD_PROGRESS_2026-10-30.md" target="_blank" rel="noopener noreferrer">Full master task document and acceptance rules ↗</a></p>
 {segments.map(([name,detail],i)=><details key={name} style={{padding:"10px 0",borderTop:"1px solid #cbd5e1"}}><summary style={{cursor:"pointer",fontWeight:650}}>{String(i+1).padStart(2,"0")} · {name} — verification open</summary><p>{detail}.</p><p style={{fontSize:13}}><strong>{masterBuildTasks[i]?.length ?? 0} itemized tasks</strong> · {masterBuildTasks[i]?.filter((_,j)=>taskStatus(`${String(i+1).padStart(2,"0")}-${String(j+1).padStart(3,"0")}`).status==="Verified").length??0} verified. Each task requires dated acceptance evidence. The list is a work inventory, not a claim that every task is running.</p><ol style={{paddingLeft:24}}>{(masterBuildTasks[i] ?? []).map((task,j)=><li key={j} style={{padding:"5px 0"}}><span style={{color:taskStatus(`${String(i+1).padStart(2,"0")}-${String(j+1).padStart(3,"0")}`).status==="Verified"?"#047857":"#92400e",fontWeight:700}}> {taskStatus(`${String(i+1).padStart(2,"0")}-${String(j+1).padStart(3,"0")}`).status==="Verified"?"✓":"○"} </span><strong style={{fontSize:11}}>{`${String(i+1).padStart(2,"0")}-${String(j+1).padStart(3,"0")}`}</strong> {task} <small style={{color:"#64748b"}}>— {taskStatus(`${String(i+1).padStart(2,"0")}-${String(j+1).padStart(3,"0")}`).status}</small>{taskStatus(`${String(i+1).padStart(2,"0")}-${String(j+1).padStart(3,"0")}`).evidenceUrl?<a href={taskStatus(`${String(i+1).padStart(2,"0")}-${String(j+1).padStart(3,"0")}`).evidenceUrl} target="_blank" rel="noopener noreferrer"> Evidence ↗</a>:null}</li>)}</ol><p style={{fontSize:12}}>Completion requires code, production runtime, acceptance test and dated source evidence. Existing historical audits remain in the linked detailed document.</p></details>)}
 </section>
}