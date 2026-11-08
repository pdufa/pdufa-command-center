"use client";

import {useCallback,useEffect,useMemo,useRef,useState} from "react";
import {masterBuildTasks} from "./master-build-tasks";
import {activeInstallationTasks} from "../../lib/installation-active-requirements";
import styles from "./InstallationLiveNavigator.module.css";

type TaskState="Verified"|"In Progress"|"Blocked"|"Failed"|"Not Started"|"Unverified";
type TaskEvidence={
 status:TaskState;checkedAt?:string;evidenceUrl?:string;note?:string;
 acceptance?:string;acceptanceMissing?:string[];
};
type ExecutionCursor={
 state:"RUNNING"|"STOPPED"|"UNKNOWN";taskId:string|null;
 observedAt:string|null;runId?:string|null;operation?:string|null;
};
type TaskResponse={
 schemaVersion:number;checkedAt:string;registryUpdatedAt?:string;
 tasks:Record<string,TaskEvidence>;activeExecution?:ExecutionCursor|null;
};
type ScienceQuestion={
 id:string;layer:number;layerName:string;question:string;requiredEvidence:string;
};
type ScienceCatalog={
 status:string;origin:string;layerCount:number;questionsPerLayer:number;
 questionCount:number;maximumInvestigationDepth:number;questions:ScienceQuestion[];
};
const taskList=activeInstallationTasks(masterBuildTasks);
const branchNames=[
 "Disease Biology & Medical Rationale",
 "Therapeutic Strategy & Mechanism",
 "Clinical Trial Design & Execution",
 "Clinical Efficacy & Statistical Evidence",
 "Safety & Benefit–Risk",
 "Regulatory & Manufacturing",
 "Historical FDA Comparisons",
 "Prediction, Uncertainty & Evidence Validation"
];
const branchOwner=["SCIENCE","SCIENCE","SCIENCE","SCIENCE","SCIENCE","SCIENCE","OUTCOME","MAIN"];
const palette:Record<string,string>={
 Verified:"#6af8cf","In Progress":"#ffdc97",Blocked:"#ffb4a6",Failed:"#ff9b9b",
 "Not Started":"#c1dfe2",Unverified:"#c1dfe2"
};
const panel={border:"1px solid #39717b",borderRadius:10,padding:14,background:"#0a2c3b",color:"#e7f9fc"} as const;
const info={fontSize:13,lineHeight:1.55,color:"#c1dfe2"} as const;
const idOf=(taskId:string)=>"install-task-"+taskId;
const safeTime=(value:string|undefined|null)=>value&&Number.isFinite(Date.parse(value))?
 new Date(value).toLocaleString():"Not recorded";
const status=(row:TaskEvidence|undefined):TaskState=>row?.status??"Unverified";

/** Only a fresh, specifically identified RUNNING worker event is a live position. */
function getActiveExecution(snapshot:TaskResponse|null):ExecutionCursor|null{
 const c=snapshot?.activeExecution;
 if(!c||c.state!=="RUNNING"||!c.taskId||!c.observedAt)return null;
 if(!taskList.some(t=>t.id===c.taskId))return null;
 const when=Date.parse(c.observedAt);
 if(!Number.isFinite(when)||Math.abs(Date.now()-when)>90000)return null;
 return c;
}

export default function InstallationLiveNavigator(){
 const [audit,setAudit]=useState<TaskResponse|null>(null);
 const [catalog,setCatalog]=useState<ScienceCatalog|null>(null);
 const [error,setError]=useState("");
 const [section,setSection]=useState<"past"|"present"|"future">("present");
 const [following,setFollowing]=useState(true);
 const [chosenTask,setChosenTask]=useState<string|null>(null);
 const [chosenQuestion,setChosenQuestion]=useState("S01");
 const [chosenLevel,setChosenLevel]=useState(1);
 const [expandedBranch,setExpandedBranch]=useState(0);
 const [busy,setBusy]=useState(false);
 const [liveNotice,setLiveNotice]=useState("");
 const [liveJump,setLiveJump]=useState<{taskId:string|null;sequence:number}|null>(null);
 const mounted=useRef(true);
 const fetchData=useCallback(async()=>{
  try{
   const response=await fetch("/api/installation-audit/live-task-evidence",{cache:"no-store"});
   if(!response.ok)throw Error("Installation task evidence endpoint returned HTTP "+response.status);
   const next:TaskResponse=await response.json();
   if(next.schemaVersion!==1||typeof next.tasks!=="object"||!next.tasks)
    throw Error("Installation task evidence format is unavailable");
   if(mounted.current){setAudit(next);setError("");}
   return next;
  }catch(cause){
   if(mounted.current)setError(cause instanceof Error?cause.message:"Installation telemetry unavailable");
   return null;
  }finally{if(mounted.current)setBusy(false);}
 },[]);
 useEffect(()=>{
  mounted.current=true;
  void fetchData();
  void fetch("/installation-audit/science-40-catalog.json",{cache:"no-store"})
   .then(async response=>{if(!response.ok)throw Error("catalog unavailable");return response.json() as Promise<ScienceCatalog>;})
   .then(value=>{if(mounted.current&&value.questionCount===40&&value.questions.length===40)setCatalog(value);})
   .catch(()=>{});
  const interval=window.setInterval(()=>{if(document.visibilityState==="visible")void fetchData();},15000);
  const visible=()=>{if(document.visibilityState==="visible")void fetchData();};
  document.addEventListener("visibilitychange",visible);
  return()=>{mounted.current=false;window.clearInterval(interval);document.removeEventListener("visibilitychange",visible);};
 },[fetchData]);
 const active=useMemo(()=>getActiveExecution(audit),[audit]);
 const goToLive=useCallback(async()=>{
  // The button refreshes first; a stale saved registry never becomes a live cursor.
  setBusy(true);
  const latest=await fetchData();
  const cursor=getActiveExecution(latest);
  setFollowing(true);
  setSection("present");
  setChosenTask(cursor?.taskId??null);
  setLiveNotice(cursor
    ?"Jumped to the confirmed running installation task "+cursor.taskId+"."
    :"Live location unavailable: no fresh, verified running task is reported. Showing active cursor status instead.");
  setLiveJump(previous=>({taskId:cursor?.taskId??null,sequence:(previous?.sequence??0)+1}));
 },[fetchData]);
 useEffect(()=>{
  if(!following||!active?.taskId)return;
  setSection("present");
  setChosenTask(active.taskId);
  setLiveJump(previous=>previous?.taskId===active.taskId?previous:
   {taskId:active.taskId,sequence:(previous?.sequence??0)+1});
 },[active?.taskId,following]);
 useEffect(()=>{
  if(!liveJump)return;
  // React must render the PRESENT list before scrolling to a newly selected task.
  const frame=window.requestAnimationFrame(()=>{
   const target=liveJump.taskId?
    document.getElementById(idOf(liveJump.taskId)):
    document.getElementById("installation-active-cursor");
   target?.scrollIntoView({
    behavior:window.matchMedia("(prefers-reduced-motion: reduce)").matches?"auto":"smooth",
    block:"center"
   });
  });
  return()=>window.cancelAnimationFrame(frame);
 },[liveJump,section]);
 const past=taskList.filter(t=>status(audit?.tasks[t.id])==="Verified");
 const progress=taskList.filter(t=>status(audit?.tasks[t.id])==="In Progress");
 const future=taskList.filter(t=>status(audit?.tasks[t.id])!=="Verified");
 const visible=section==="past"?past:section==="future"?future:active?taskList.filter(t=>t.id===active.taskId):progress;
 const question=catalog?.questions.find(q=>q.id===chosenQuestion);
 const grouped=catalog?Array.from({length:8},(_,i)=>catalog.questions.filter(q=>q.layer===i+1)):[];
 return <section id="live-installation-timeline" aria-label="Past present and future installation timeline"
   className={styles.navigator}
   style={{...panel,margin:"18px 0",background:"radial-gradient(circle at 100% 0,#175364,transparent 42%),linear-gradient(135deg,#071824,#0b3543)"}}>
  <h2 style={{margin:"0 0 8px"}}>INSTALLATION · past / present / future</h2>
  <p style={info}>Read-only verified acceptance records and source-linked scientific planning catalog.
   Live checks refresh every 15 seconds while the page is visible. A green deployment or an “In Progress”
   registry label does not establish that Codex is executing that task.</p>
  <div style={{display:"flex",gap:10,flexWrap:"wrap",margin:"12px 0"}}>
   <button type="button" onClick={()=>{setBusy(true);void fetchData();}} disabled={busy}
    style={{padding:"9px 12px",borderRadius:8,border:"1px solid #5aa9ae",background:"#0b625c",color:"#fff"}}>
    {busy?"Checking…":"Check installation now"}
   </button>
   <button type="button" className={styles.liveButton}
    onClick={()=>{void goToLive();}} disabled={busy}
    aria-label="LIVE: jump to the current verified installation task">
    <span className={styles.liveIndicator} aria-hidden="true"/>
    LIVE <span className={styles.liveArrow} aria-hidden="true">→</span>
   </button>
   <label style={{display:"flex",gap:8,alignItems:"center",fontWeight:600,fontSize:13}}>
    <input type="checkbox" checked={following} onChange={event=>setFollowing(event.target.checked)}/>
    Follow live execution cursor
   </label>
  </div>
  {error&&<p role="alert" style={{color:"#ffd4bb"}}>{error}. Previous data may be stale.</p>}
  {liveNotice&&<p role="status" aria-live="polite" className={styles.liveNotice}>{liveNotice}</p>}
  <div id="installation-active-cursor" className={!active&&liveJump?.taskId===null?styles.cursorTarget:undefined}
   style={{...panel,border:"2px solid #5aa9ae",marginBottom:12,scrollMarginTop:92}}>
   <strong>ACTIVE CURSOR</strong>
   {active?<>
    <p role="status"><strong>RUNNING: {active.taskId}</strong> · {taskList.find(t=>t.id===active.taskId)?.label}</p>
    <p style={info}>Run {active.runId??"not recorded"} · {active.operation??"Operation not identified"} ·
     heartbeat {safeTime(active.observedAt)}</p>
   </>:<>
    <p role="status"><strong>No verified active installation task is currently reported.</strong></p>
    <p style={info}>This source does not yet provide an authenticated, fresh, task-ID-level Codex execution
     heartbeat. The cursor will not jump to a guess or a merely queued task. Last evidence registry:
     {" "}{safeTime(audit?.registryUpdatedAt)}.</p>
   </>}
  </div>
  <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(155px,1fr))",gap:8,marginBottom:12}}>
   <button type="button" onClick={()=>setSection("past")}
    aria-pressed={section==="past"} style={{...panel,textAlign:"left",borderColor:section==="past"?"#45ebba":"#39717b"}}>
    <strong>PAST</strong><div style={{fontSize:25,fontWeight:750}}>{audit?past.length:"—"}</div>
    <small>Accepted with proof</small>
   </button>
   <button type="button" onClick={()=>setSection("present")}
    aria-pressed={section==="present"} style={{...panel,textAlign:"left",borderColor:section==="present"?"#45ebba":"#39717b"}}>
    <strong>PRESENT</strong><div style={{fontSize:25,fontWeight:750}}>{active?"1":"—"}</div>
    <small>{active?"Running task":"No confirmed active task"}</small>
   </button>
   <button type="button" onClick={()=>setSection("future")}
    aria-pressed={section==="future"} style={{...panel,textAlign:"left",borderColor:section==="future"?"#45ebba":"#39717b"}}>
    <strong>FUTURE / OPEN</strong><div style={{fontSize:25,fontWeight:750}}>{audit?future.length:"—"}</div>
    <small>Awaiting acceptance review; not all unbuilt</small>
   </button>
  </div>
  <p style={info}>Current accepted: {audit?past.length+"/"+taskList.length:"Not loaded"} ·
   tasks with implementation evidence only: {audit?progress.length:"unknown"} ·
   refreshed: {safeTime(audit?.checkedAt)}. Original 15-section historical audit remains below.</p>
  <details open>
   <summary style={{cursor:"pointer",fontWeight:750,marginBottom:9}}>
    {section==="past"?"Completed / accepted history":section==="present"?"Current execution and implementation evidence":"Open / future verification work"}
    {" "}({visible.length})
   </summary>
   {section==="present"&&!active&&<p style={info}>There is no verified executing task.
    Below are tasks labeled In Progress in the saved registry; these are <strong>not</strong> real-time worker positions.</p>}
   <div style={{maxHeight:390,overflowY:"auto",display:"grid",gap:5}}>
    {visible.length===0&&<p style={info}>No items with independently supported status in this category.</p>}
    {visible.map(task=>{
     const row=audit?.tasks[task.id];
     return <div key={task.id} id={idOf(task.id)}
      className={task.id===active?.taskId?styles.cursorTarget:undefined}
      style={{padding:"9px 10px",scrollMarginTop:92,border:"1px solid #39717b",borderRadius:8,
       background:task.id===active?.taskId?"#145751":"#0b3040"}}>
      <button type="button" onClick={()=>setChosenTask(chosenTask===task.id?null:task.id)}
       aria-expanded={chosenTask===task.id}
       style={{display:"flex",alignItems:"center",gap:8,textAlign:"left",width:"100%",background:"transparent",color:"#e7f9fc",border:0,cursor:"pointer"}}>
       <span style={{fontWeight:750,flexShrink:0,fontSize:12}}>{task.id}</span>
       <span style={{flex:1,fontSize:13}}>{task.label}</span>
       <span style={{fontSize:11,color:palette[status(row)]}}>{status(row)}</span>
       <span aria-hidden="true">ⓘ</span>
      </button>
      {chosenTask===task.id&&<div style={{...info,padding:"10px 3px 3px",borderTop:"1px solid #39717b",marginTop:8}}>
       <p><strong>Stage:</strong> {String(task.section+1).padStart(2,"0")} ·
        <strong> Last verified:</strong> {safeTime(row?.checkedAt)}</p>
       <p><strong>Explanation:</strong> {row?.note??"No accepted execution proof recorded for this requirement."}</p>
       <p><strong>Acceptance gaps:</strong> {row?.acceptanceMissing?.length?
        row.acceptanceMissing.join("; "):status(row)==="Verified"?"No gaps reported in accepted record.":"Task-specific runtime and dated proof not established."}</p>
       <p><strong>Revalidation:</strong> Repeat the applicable acceptance checks after relevant code,
        infrastructure, source or requirement changes. No automatic expiry date is inferred.</p>
       {row?.evidenceUrl&&<a href={row.evidenceUrl} target="_blank" rel="noopener noreferrer">Open evidence record</a>}
      </div>}
     </div>;
    })}
   </div>
  </details>
  <div id="scientific-assessment-register" style={{...panel,marginTop:18}}>
   <h3 style={{margin:"0 0 8px"}}>Scientific assessments · 800-target drill-down</h3>
   <p style={info}>The original source catalog has 40 research questions with a 20-level maximum
    ({catalog?"40 × 20 = 800 planned drill-down positions":"catalog loading"}). These are
    <strong> not 800 installed tests</strong>. The newer directive permits up to 50 depth levels
    per branch; a migration audit must reconcile the two models.</p>
   <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(155px,1fr))",gap:8,marginBottom:11}}>
    <div style={panel}><strong style={{fontSize:23}}>800</strong><br/><small>Planning slots only</small></div>
    <div style={panel}><strong style={{fontSize:23}}>{catalog?.questionCount??"—"}</strong><br/><small>Catalog questions</small></div>
    <div style={panel}><strong style={{fontSize:23}}>Unknown</strong><br/><small>Executed / passed</small></div>
   </div>
   <details style={{margin:"12px 0"}}>
    <summary style={{cursor:"pointer",fontWeight:700}}>Current approved eight scientific branches ⓘ</summary>
    <p style={info}>Approved research ownership; question-to-branch remapping is not certified.</p>
    <ol>{branchNames.map((name,i)=><li key={name}><strong>{name}</strong> · {branchOwner[i]}</li>)}</ol>
   </details>
   <p style={{fontWeight:700,margin:"10px 0"}}>Original source-defined eight question groups</p>
   {catalog?grouped.map((questions,i)=><details key={i} open={expandedBranch===i}
    onToggle={event=>{if(event.currentTarget.open)setExpandedBranch(i);}}
    style={{border:"1px solid #39717b",background:"#0b3040",borderRadius:8,padding:"8px 12px",marginBottom:7}}>
    <summary style={{cursor:"pointer",fontWeight:650}}>
     {i+1}. {questions[0]?.layerName??"Unknown"} · {questions.length} original questions
    </summary>
    {questions.map(q=><button type="button" key={q.id}
     onClick={()=>{setChosenQuestion(q.id);setChosenLevel(1);}}
     style={{display:"block",width:"100%",textAlign:"left",padding:"9px",margin:"4px 0",borderRadius:6,
      border:q.id===chosenQuestion?"2px solid #45ebba":"1px solid #39717b",background:q.id===chosenQuestion?"#145751":"#0a2c3b",color:"#e7f9fc"}}>
     <strong>{q.id}:</strong> {q.question}
    </button>)}
   </details>):<p role="status" style={info}>Original scientific question catalog unavailable; no fabricated definitions displayed.</p>}
   {question&&<div style={{...panel,marginTop:12}} aria-label="Individual assessment evidence and levels">
    <h4 style={{margin:"0 0 7px"}}>{question.id} · {question.question}</h4>
    <p style={info}><strong>Expected evidence:</strong> {question.requiredEvidence}</p>
    <p style={info}><strong>Actual linked evidence:</strong> Not audited ·
     <strong> scientific result:</strong> Not verified · <strong>execution history:</strong> Not connected.</p>
    <p style={info}>ⓘ Revalidate after new study results, a modified rubric or a changed
     application/regulatory record. No evidence-specific expiration can be asserted yet.</p>
    <p style={{fontWeight:700}}>Choose investigation level (illustrative; not executable test)</p>
    <div style={{display:"flex",flexWrap:"wrap",gap:5}}>
     {Array.from({length:20},(_,n)=><button type="button" key={n} onClick={()=>setChosenLevel(n+1)}
      aria-pressed={chosenLevel===n+1}
      style={{padding:"7px 10px",borderRadius:6,border:"1px solid #5aa9ae",
       background:chosenLevel===n+1?"#0b625c":"#0a2c3b",color:chosenLevel===n+1?"#fff":"#e7f9fc"}}>
      {String(n+1).padStart(2,"0")}
     </button>)}
    </div>
    <p role="status" style={{...info,marginTop:10}}>
     Selected planning position {question.id}–L{String(chosenLevel).padStart(2,"0")}.
     There is no verified level-specific result, score or worker checkpoint for this position.
    </p>
   </div>}
  </div>
 </section>;
}
