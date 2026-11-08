"use client";
import {useCallback,useEffect,useState} from "react";
import Link from "next/link";
import type {MonitorSnapshot,Stage,CheckState} from "../../lib/main-install-progress";

const stateColor:Record<CheckState|string,string>={
 VERIFIED:"#00644d",COMPLETE:"#00644d",PENDING:"#8f661e",
 BLOCKED:"#8c392f",FAILED:"#a02529",UNKNOWN:"#596770"
};
const label:Record<string,string>={
 VERIFIED:"Verified",COMPLETE:"Complete",PENDING:"Pending",
 BLOCKED:"Blocked",FAILED:"Failed",UNKNOWN:"Unknown"
};
const box={border:"1px solid #c5dacf",borderRadius:12,padding:16,background:"#fff"} as const;
const muted={fontSize:13,color:"#50675a",lineHeight:1.5} as const;
const chip=(s:string)=>({fontSize:12,fontWeight:750,color:stateColor[s]??"#566",
  border:"1px solid "+(stateColor[s]??"#566"),borderRadius:20,padding:"3px 8px"} as const);
function Fill({done}:{done:number}){
 return <div aria-hidden="true" style={{height:10,background:"#e9f0eb",borderRadius:8,overflow:"hidden"}}>
  <div style={{width:Math.max(0,Math.min(100,done))+"%",height:"100%",background:"#087a61"}}/>
 </div>;
}
function StagePanel({stage}:{stage:Stage}){
 return <details style={{...box,marginTop:9}} data-stage={stage.id}>
  <summary style={{cursor:"pointer",listStyle:"auto"}}>
   <span style={{display:"flex",justifyContent:"space-between",alignItems:"center",flexWrap:"wrap",gap:8}}>
    <strong style={{fontSize:15}}>{stage.title}</strong>
    <span style={chip(stage.status)}>{label[stage.status]} · {stage.percent}% ({stage.verified}/{stage.total})</span>
   </span>
   <div style={{marginTop:9}}><Fill done={stage.percent}/></div>
  </summary>
  <div style={{marginTop:14}}>
   {stage.checks.map(c=><div key={c.id} style={{padding:"10px 0",borderTop:"1px solid #e3ede6"}}>
    <div style={{display:"flex",alignItems:"center",gap:10,flexWrap:"wrap"}}>
     <span style={chip(c.status)}>{label[c.status]}</span>
     <strong style={{fontSize:13}}>{c.title}</strong>
    </div>
    <p style={{...muted,margin:"5px 0"}}>{c.detail}</p>
    <p style={{...muted,margin:"3px 0",fontSize:12}}>Evidence: {c.source}{c.checkedAt?" · observed "+new Date(c.checkedAt).toLocaleString():""}</p>
   </div>)}
  </div>
 </details>;
}
export default function InstallationProgressDashboard(){
 const [data,setData]=useState<MonitorSnapshot|null>(null);
 const [error,setError]=useState("");
 const [busy,setBusy]=useState(true);
 const refresh=useCallback(async()=>{
  try{
   const response=await fetch("/api/main/installation-progress",{cache:"no-store"});
   if(!response.ok)throw Error(response.status===401?"Sign in on the PDUFA home page to view live installation status.":"Live installation evidence could not be retrieved.");
   const raw:MonitorSnapshot=await response.json();
   if(raw.schemaVersion!==1||!Array.isArray(raw.stages)||raw.overall?.total<1)
    throw Error("Installation telemetry format unavailable");
   setData(raw);setError("");
  }catch(cause){setError(cause instanceof Error?cause.message:"Installation telemetry unavailable");}
  finally{setBusy(false);}
 },[]);
 useEffect(()=>{
  void refresh();
  const tick=setInterval(()=>{if(document.visibilityState==="visible")void refresh();},45000);
  const active=()=>{if(document.visibilityState==="visible")void refresh();};
  document.addEventListener("visibilitychange",active);
  return ()=>{clearInterval(tick);document.removeEventListener("visibilitychange",active);};
 },[refresh]);
 return <section style={{...box,margin:"18px 0"}} aria-label="Automated installation progress and system health" id="installation-progress">
  <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",gap:10,flexWrap:"wrap"}}>
   <div>
    <h2 style={{margin:"0 0 5px",fontSize:22}}>Automated installation progress &amp; system health</h2>
    <p style={{...muted,margin:0}}>Live checkpoints, source and deployment evidence · refreshes about every 45 seconds while this page is open</p>
   </div>
   <button type="button" onClick={()=>void refresh()} disabled={busy} style={{padding:"9px 13px",borderRadius:8,background:"#0b6c57",color:"white",fontWeight:700,border:0}}>
    {busy?"Checking…":"Check now"}
   </button>
  </div>
  {error&&<p role="alert" style={{color:"#912d31",fontSize:13}}>{error}</p>}
  {!data&&<p role="status" style={muted}>{busy?"Loading verified installation telemetry…":"Progress unavailable. No percentages are estimated when live evidence cannot be retrieved."}</p>}
  {data&&<>
   <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(165px,1fr))",gap:11,marginTop:18}}>
    <div style={{padding:14,background:"#f3f8f4",borderRadius:9}}>
     <div style={muted}>Overall verified installation</div>
     <strong style={{fontSize:30}}>{data.overall.percent}%</strong>
     <div style={muted}>{data.overall.verified} / {data.overall.total} checkpoints</div>
    </div>
    <div style={{padding:14,background:"#f3f8f4",borderRadius:9}}>
     <div style={muted}>Pending</div>
     <strong style={{fontSize:27}}>{data.overall.pending}</strong>
    </div>
    <div style={{padding:14,background:"#f3f8f4",borderRadius:9}}>
     <div style={muted}>Blocked / failed</div>
     <strong style={{fontSize:27,color:"#8c392f"}}>{data.overall.blocked} / {data.overall.failed}</strong>
    </div>
    <div style={{padding:14,background:"#f3f8f4",borderRadius:9}}>
     <div style={muted}>Cannot verify</div>
     <strong style={{fontSize:27}}>{data.overall.unknown}</strong>
    </div>
   </div>
   <div style={{margin:"12px 0 6px"}}><Fill done={data.overall.percent}/></div>
   <p style={{...muted,marginTop:6}}>{data.methodology}</p>
   <p style={{...muted,fontSize:12}}>Last checked: {new Date(data.observedAt).toLocaleString()}. FOCUS snapshot: {data.facts.focusTrialCount} NCTs dated {data.facts.rosterAsOf}; {data.facts.fdaApplicationCycles} reconstructed FDA cycles. This is not a claim of current trial qualification or regulatory accuracy.</p>
   {data.nextUnfinished&&<div style={{padding:13,border:"1px solid #ddd2bf",borderRadius:9,margin:"14px 0"}}>
    <strong>Next unresolved work: {data.nextUnfinished.checkpoint}</strong>
    <p style={{...muted,margin:"5px 0 2px"}}>{data.nextUnfinished.stage} · {label[data.nextUnfinished.status]}</p>
    <p style={{...muted,margin:0}}>{data.nextUnfinished.detail}</p>
   </div>}
   <details style={{...box,background:"#f7faf7",marginTop:12}}>
    <summary style={{cursor:"pointer",fontWeight:700}}>Live operational signals · scans, evidence, failures and Telegram</summary>
    <div style={{fontSize:13,lineHeight:1.6,marginTop:10}}>
     <p><strong>Phase 3 ingestion:</strong> {String(data.signals.scans?.phase3Ingestion?.state??"unavailable")} · Last success: {String(data.signals.scans?.phase3Ingestion?.lastSuccessAt??"not recorded")}</p>
     <p><strong>NCT evidence collection:</strong> {String(data.signals.scans?.nctStream?.totalRuns??"unknown")} runs · failures: {String(data.signals.scans?.nctStream?.failedRuns??"unknown")}</p>
     <p><strong>Medical research:</strong> {String(data.signals.research?.finishedSourceRuns??"unknown")} complete source-collection runs · {String(data.signals.research?.immutableRevisions??"unknown")} saved revisions · {String(data.signals.research?.newSourceEvidenceRevisions??"unknown")} changed-evidence revisions · {String(data.signals.research?.failedSourceRuns??"unknown")} failures</p>
     <p><strong>Automatic registry source watch:</strong> {data.signals.scans?.registryWatch?.enabled===true?"Enabled":"Not confirmed enabled"} · Last checked: {String(data.signals.scans?.registryWatch?.lastCheckedAt??"not recorded")}</p>
     <p><strong>Telegram:</strong> {data.signals.alerts?.telegramConfigured===true?"Bot configured":"Not configured/unknown"} · Last delivery: {String((data.signals.alerts?.lastDelivery as {state?:string}|undefined)?.state??"not verified")}</p>
     <p><strong>Unmonitored inputs:</strong> {Array.isArray(data.signals.coverage?.missing)?data.signals.coverage.missing.join(", "):"Current external scan and non-registry source coverage not verified"}</p>
     <p style={muted}>Live backend records report observed events, not the separate external scheduled scanner's success. Telegram messages are deduplicated and require configured credentials plus a recorded successful send.</p>
    </div>
   </details>
   <details style={{marginTop:14}} open>
    <summary style={{cursor:"pointer",fontWeight:750,fontSize:17}}>Expand installation stages — {data.stages.length} groups including all 12 advanced levels</summary>
    <div style={{marginTop:8}}>{data.stages.map(stage=><StagePanel key={stage.id} stage={stage}/>)}</div>
   </details>
   <p style={{...muted,marginTop:16}}>The seven original MAIN Core Platform/Pipeline acceptance gates and their historical evidence remain intact below. This is a new, separately scoped installation monitor, not a rewrite of the historical audit.</p>
   <div style={{display:"flex",flexWrap:"wrap",gap:14,fontSize:13}}>
    <Link href="/medical-intelligence-preview/advanced">12 advanced medical levels</Link>
    <Link href="/focus">FOCUS evidence</Link>
    <Link href="/pool">Master POOL</Link>
   </div>
  </>}
 </section>;
}
