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
type WorkflowEvidence={
 id:number;name:string;branch:string;status:string;conclusion:string|null;
 startedAt:string|null;updatedAt:string|null;url:string;
 job:string|null;step:string|null;jobStatus:string|null;
 stepCoverage:"OBSERVED"|"NOT_CHECKED"|"UNAVAILABLE";
};
type LiveGithubEvidence={
 state:"VERIFIED"|"PARTIAL"|"UNAVAILABLE"|"AUTH_REQUIRED";
 checkedAt:string;sourceUrl:string;running:WorkflowEvidence[];queued:WorkflowEvidence[];
 recent:WorkflowEvidence[];scope:string;note:string;
};
type TaskResponse={
 schemaVersion:number;checkedAt:string;registryUpdatedAt?:string;
 tasks:Record<string,TaskEvidence>;activeExecution?:ExecutionCursor|null;
 githubActions?:LiveGithubEvidence;checks?:Record<string,{status:string;checkedAt:string;note:string}>;
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
type JumpTarget={taskId:string|null;kind:"live"|"workflow"|"status";sequence:number};
function getRunningGithub(snapshot:TaskResponse|null):WorkflowEvidence|null{
 const source=snapshot?.githubActions;
 if(!source||!["VERIFIED","PARTIAL"].includes(source.state))return null;
 const stamp=Date.parse(source.checkedAt);
 if(!Number.isFinite(stamp)||Math.abs(Date.now()-stamp)>90000)return null;
 return source.running[0]??null;
}

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
 const [installationExpanded,setInstallationExpanded]=useState(false);
 const [following,setFollowing]=useState(true);
 const [chosenTask,setChosenTask]=useState<string|null>(null);
 const [chosenQuestion,setChosenQuestion]=useState("S01");
 const [chosenLevel,setChosenLevel]=useState(1);
 const [expandedBranch,setExpandedBranch]=useState(0);
 const [busy,setBusy]=useState(false);
 const [liveNotice,setLiveNotice]=useState("");
 const [liveJump,setLiveJump]=useState<JumpTarget|null>(null);
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
 const activeGithub=useMemo(()=>getRunningGithub(audit),[audit]);
 const locateSnapshot=useCallback((snapshot:TaskResponse|null)=>{
  // A GitHub workflow proves actual GitHub Actions execution only. Never
  // fabricate a Codex worker ID or a verified scientific grading task.
  const cursor=getActiveExecution(snapshot);
  const workflow=cursor?null:getRunningGithub(snapshot);
  const destination=cursor?.taskId??null;
  setFollowing(true);
  setInstallationExpanded(true);
  setSection("present");
  setChosenTask(destination);
  setLiveNotice(cursor
    ?"Located current LIVE installation task "+cursor.taskId+"."
    :workflow
     ?"Located an active GitHub Actions workflow: "+workflow.name+". Exact Codex / scientific task identity is not verified."
     :snapshot?.githubActions?.state==="VERIFIED"
      ?"No active GitHub Actions workflow or task-specific live heartbeat was observed at "+safeTime(snapshot.githubActions.checkedAt)+". Showing evidence status."
      :snapshot
       ?"Live location not verified. GitHub status: "+(snapshot.githubActions?.state??"not connected")+". Showing evidence status, not a historical checkpoint."
       :"No verified live location has loaded yet. Showing evidence status; refreshing task evidence.");
  setLiveJump(previous=>({
   taskId:destination,kind:cursor?"live":workflow?"workflow":"status",
   sequence:(previous?.sequence??0)+1
  }));
 },[]);
 const goToLive=useCallback(()=>{
  // First open and scroll from the latest known snapshot; never await the audit
  // endpoint before making the button visibly work on mobile Safari.
  locateSnapshot(audit);
  void fetchData().then(latest=>{
   if(latest)locateSnapshot(latest);
   else setLiveNotice(previous=>previous+" Refresh failed; showing last recorded information.");
  });
 },[audit,fetchData,locateSnapshot]);
 useEffect(()=>{
  if(!following||!installationExpanded)return;
  if(active?.taskId){
   setSection("present");
   setChosenTask(active.taskId);
   setLiveJump(previous=>previous?.taskId===active.taskId&&previous.kind==="live"?previous:
    {taskId:active.taskId,kind:"live",sequence:(previous?.sequence??0)+1});
  }else if(activeGithub){
   setSection("present");
   setLiveJump(previous=>previous?.kind==="workflow"&&previous.taskId===null?previous:
    {taskId:null,kind:"workflow",sequence:(previous?.sequence??0)+1});
  }
 },[active?.taskId,activeGithub?.id,following,installationExpanded]);
 useEffect(()=>{
  if(!liveJump||!installationExpanded)return;
  // Wait for the opened caret and selected row to exist. Safari can ignore
  // a same-frame scroll into newly mounted content, especially nested scrollers.
  let second=0;
  const first=window.requestAnimationFrame(()=>{
   second=window.requestAnimationFrame(()=>{
    const target=(liveJump.taskId&&document.getElementById(idOf(liveJump.taskId)))||
     (liveJump.kind==="workflow"&&document.getElementById("installation-github-execution"))||
     document.getElementById("installation-active-cursor");
    if(!target)return;
    const list=target.closest("[data-installation-task-list]");
    if(list instanceof HTMLElement){
     const row=target.getBoundingClientRect(),bounds=list.getBoundingClientRect();
     list.scrollTop+=row.top-bounds.top-Math.max(0,(bounds.height-row.height)/2);
    }
    target.scrollIntoView({behavior:"auto",block:"center"});
    target.focus({preventScroll:true});
   });
  });
  return()=>{window.cancelAnimationFrame(first);if(second)window.cancelAnimationFrame(second);};
 },[liveJump,section,installationExpanded]);
 const past=taskList.filter(t=>status(audit?.tasks[t.id])==="Verified");
 const progress=taskList.filter(t=>status(audit?.tasks[t.id])==="In Progress");
 const future=taskList.filter(t=>status(audit?.tasks[t.id])!=="Verified");
 const visible=section==="past"?past:section==="future"?future:active?taskList.filter(t=>t.id===active.taskId):progress;
 const question=catalog?.questions.find(q=>q.id===chosenQuestion);
 const grouped=catalog?Array.from({length:8},(_,i)=>catalog.questions.filter(q=>q.layer===i+1)):[];
 return <section id="live-installation-timeline" aria-label="Past present and future installation timeline"
   className={styles.navigator}
   style={{...panel,margin:"18px 0",background:"radial-gradient(circle at 100% 0,#175364,transparent 42%),linear-gradient(135deg,#071824,#0b3543)"}}>
  <h2 className={styles.sectionHeading}>
   <button type="button" className={styles.sectionCaret}
    aria-expanded={installationExpanded} aria-controls="installation-tracker-details"
    onClick={()=>setInstallationExpanded(open=>!open)}>
    <span className={styles.caret} aria-hidden="true">{installationExpanded?"⌄":"›"}</span>
    <span>INSTALLATION · past / present / future</span>
    <span className={styles.caretHint}>{installationExpanded?"Collapse":"Expand"}</span>
   </button>
  </h2>
  {installationExpanded&&<p style={info}>Read-only verified acceptance records and source-linked scientific planning catalog.
   Live checks refresh every 15 seconds while the page is visible. A green deployment or an “In Progress”
   registry label does not establish that Codex is executing that task.</p>}
  <div style={{display:"flex",gap:10,flexWrap:"wrap",margin:"12px 0"}}>
   <button type="button" onClick={()=>{setBusy(true);void fetchData();}} disabled={busy}
    style={{padding:"9px 12px",borderRadius:8,border:"1px solid #5aa9ae",background:"#0b625c",color:"#fff"}}>
    {busy?"Checking…":"Check installation now"}
   </button>
   <button type="button" className={styles.liveButton}
    onClick={()=>{void goToLive();}}
    aria-label="Locate verified current execution or show explicit no-live status">
    <svg className={styles.locateIcon} width="22" height="22" viewBox="0 0 24 24"
     fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
     aria-hidden="true">
     <circle cx="12" cy="12" r="5"/>
     <path d="M12 2v5M12 17v5M2 12h5M17 12h5"/>
    </svg>
    <span>LOCATE LIVE</span> <span className={styles.liveArrow} aria-hidden="true">→</span>
   </button>
   <label style={{display:"flex",gap:8,alignItems:"center",fontWeight:600,fontSize:13}}>
    <input type="checkbox" checked={following} onChange={event=>setFollowing(event.target.checked)}/>
    Follow live execution cursor
   </label>
  </div>
  {error&&<p role="alert" style={{color:"#ffd4bb"}}>{error}. Previous data may be stale.</p>}
  {liveNotice&&<p role="status" aria-live="polite" className={styles.liveNotice}>{liveNotice}</p>}
  {installationExpanded&&<div id="installation-tracker-details" className={styles.trackerDetails}>
  <div id="installation-active-cursor" tabIndex={-1} className={liveJump?.kind==="status"?styles.cursorTarget:undefined}
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
  <section id="installation-github-execution" tabIndex={-1}
   className={liveJump?.kind==="workflow"?styles.cursorTarget:undefined}
   style={{...panel,marginBottom:12,border:"2px solid #5aa9ae",scrollMarginTop:92}}>
   <h3 style={{margin:"0 0 8px"}}>LIVE WORKFLOW EXECUTION · GitHub Actions</h3>
   <p style={info}>Verified repository workflow activity only; not a Codex task-level heartbeat,
    scientific assessment completion, or FDA prediction. No master task is marked accepted by this feed.</p>
   <p style={info}>Source: <a href={audit?.githubActions?.sourceUrl??"https://github.com/pdufa/pdufa-command-center/actions"}
    target="_blank" rel="noopener noreferrer">GitHub Actions</a> · Checked:
    {" "}{safeTime(audit?.githubActions?.checkedAt)} ·
    Status: <strong>{audit?.githubActions?.state??"LOADING"}</strong></p>
   {audit?.githubActions?.state==="AUTH_REQUIRED"?<p role="status">Signed-in dashboard session required for live execution details.</p>:null}
   {audit?.githubActions?.state==="UNAVAILABLE"?<p role="status">GitHub execution status unavailable; running or stopped cannot be concluded.</p>:null}
   {audit?.githubActions?.state==="PARTIAL"?<p role="status">Some workflow observations are incomplete; absence of other runs cannot be confirmed.</p>:null}
   {audit?.githubActions?.state==="VERIFIED"&&audit.githubActions.running.length===0?
    <p role="status">No in-progress GitHub Actions workflows observed in this repository at the last check.
     Codex or other providers may still be working.</p>:null}
   {activeGithub?<p style={{fontWeight:700,color:"#6af8cf"}}>Observed active workflow:
    {" "}{activeGithub.name}</p>:null}
   {audit?.githubActions?.running.map(run=><div key={run.id}
     style={{border:"1px solid #39717b",borderRadius:8,padding:10,margin:"8px 0",background:"#0b3040"}}>
     <strong>RUNNING · {run.name}</strong>
     <p style={info}>Branch: {run.branch} · Run #{run.id} · Started: {safeTime(run.startedAt)}</p>
     <p style={info}>Current job: {run.job??"Not verified"} ·
      Current step: {run.step??"Not verified"} · Step readback: {run.stepCoverage}</p>
     <a href={run.url} target="_blank" rel="noopener noreferrer">Inspect verified workflow run</a>
    </div>)}
   {Boolean(audit?.githubActions?.queued.length)&&
     <details style={{margin:"10px 0"}}><summary>Queued workflows · {audit?.githubActions?.queued.length} (not running)</summary>
       {audit?.githubActions?.queued.map(run=><p key={run.id}><a href={run.url} target="_blank" rel="noopener noreferrer">
         {run.name} · {run.branch}</a> · {run.status}</p>)}
     </details>}
   {Boolean(audit?.githubActions?.recent.length)&&
     <details style={{margin:"10px 0"}}><summary>Recently completed workflows · {audit?.githubActions?.recent.length} (history only)</summary>
       {audit?.githubActions?.recent.map(run=><p key={run.id}><a href={run.url} target="_blank" rel="noopener noreferrer">
         {run.name} · {run.branch}</a> · {run.conclusion??"Result not reported"} · {safeTime(run.updatedAt)}</p>)}
     </details>}
   {audit?.githubActions?.note&&<p style={info}>{audit.githubActions.note}</p>}
   <p style={info}>Separate health probes: website route {audit?.checks?.dashboard?.status??"unavailable"};
    {" "}backend storage {audit?.checks?.backendDatabase?.status??"unavailable"}.
    These are reachability observations, not deployment progress.</p>
  </section>
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
   <div data-installation-task-list style={{maxHeight:390,overflowY:"auto",display:"grid",gap:5}}>
    {visible.length===0&&<p style={info}>No items with independently supported status in this category.</p>}
    {visible.map(task=>{
     const row=audit?.tasks[task.id];
     const located=task.id===liveJump?.taskId;
     return <div key={task.id} id={idOf(task.id)} tabIndex={-1}
      className={located||task.id===active?.taskId?styles.cursorTarget:undefined}
      aria-current={located?"location":undefined}
      style={{padding:"9px 10px",scrollMarginTop:92,border:"1px solid #39717b",borderRadius:8,
       background:located||task.id===active?.taskId?"#145751":"#0b3040"}}>
      <button type="button" onClick={()=>setChosenTask(chosenTask===task.id?null:task.id)}
       aria-expanded={chosenTask===task.id}
       style={{display:"flex",alignItems:"center",gap:8,textAlign:"left",width:"100%",background:"transparent",color:"#e7f9fc",border:0,cursor:"pointer"}}>
       <span style={{fontWeight:750,flexShrink:0,fontSize:12}}>{task.id}</span>
       <span style={{flex:1,fontSize:13}}>{task.label}</span>
       <span style={{fontSize:11,color:palette[status(row)]}}>{status(row)}</span>
       {located&&<span className={styles.checkpointMarker}>
        {liveJump?.kind==="live"?"⌖ LIVE":"⌖ CHECKPOINT"}</span>}
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
  <details id="scientific-assessment-register" className={styles.scienceDetails}
   style={{...panel,marginTop:18}}>
   <summary className={styles.scienceSummary}>Scientific assessments · 800-target drill-down</summary>
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
  </details>
  </div>}
 </section>;
}
