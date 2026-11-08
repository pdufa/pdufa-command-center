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
 const [trialFilter,setTrialFilter]=useState("");
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
 const visibleTrials=data?.trials.filter(t=>[t.nct,t.ticker,t.company].join(" ").toLowerCase().includes(trialFilter.trim().toLowerCase()))??[];
 return <section style={{...box,margin:"18px 0"}} aria-label="Automated installation progress and system health" id="installation-progress">
  <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",gap:10,flexWrap:"wrap"}}>
   <div>
    <h2 style={{margin:"0 0 5px",fontSize:22}}>PDUFA Precision Monitoring · installation &amp; system health</h2>
    <p style={{...muted,margin:0}}>Live checkpoints, source and deployment evidence · refreshes about every 45 seconds while this page is open</p>
   </div>
   <button type="button" onClick={()=>void refresh()} disabled={busy} style={{padding:"9px 13px",borderRadius:8,background:"#0b6c57",color:"white",fontWeight:700,border:0}}>
    {busy?"Checking…":"Check now"}
   </button>
  </div>
  {error&&<p role="alert" style={{color:"#912d31",fontSize:13}}>{error}</p>}
  {!data&&<p role="status" style={muted}>{busy?"Loading verified installation telemetry…":"Progress unavailable. No percentages are estimated when live evidence cannot be retrieved."}</p>}
  {data&&<>
   <p role="status" style={{...muted,marginTop:10}}><strong>System health:</strong> {data.health.level}. {data.health.issues.length?data.health.issues.slice(0,5).join("; "):"No observed blockers from current telemetry."}</p>
   <p style={muted}><strong>Prediction:</strong> FDA approval, CRL and review delay — ABSTAIN. <strong>Certainty:</strong> NOT VALIDATED. Source coverage or passing builds cannot unlock either.</p>
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
     <p><strong>Analyze Now:</strong> {data.signals.analysisNow?.pilotSaved===true?"Pilot saved":"Pilot not yet saved"} · {data.signals.analysisNow?.allTrialsEnabled===true?"Full rollout enabled":"Full rollout gated"} · {String(data.signals.analysisNow?.completedSavedRuns??"unknown")} saved invoked runs</p>
     <p><strong>Medical research:</strong> {String(data.signals.research?.finishedSourceRuns??"unknown")} complete source-collection runs · {String(data.signals.research?.immutableRevisions??"unknown")} saved revisions · {String(data.signals.research?.newSourceEvidenceRevisions??"unknown")} changed-evidence revisions · {String(data.signals.research?.failedSourceRuns??"unknown")} failures</p>
     <p><strong>Automatic registry source watch:</strong> {data.signals.scans?.registryWatch?.enabled===true?"Enabled":"Not confirmed enabled"} · Last checked: {String(data.signals.scans?.registryWatch?.lastCheckedAt??"not recorded")}</p>
     <p><strong>Telegram:</strong> {data.signals.alerts?.telegramConfigured===true?"Bot configured":"Not configured/unknown"} · Last delivery: {String((data.signals.alerts?.lastDelivery as {state?:string}|undefined)?.state??"not verified")}</p>
     <p><strong>Unmonitored inputs:</strong> {Array.isArray(data.signals.coverage?.missing)?data.signals.coverage.missing.join(", "):"Current external scan and non-registry source coverage not verified"}</p>
     <p style={muted}>Live backend records report observed events, not the separate external scheduled scanner's success. Telegram messages are deduplicated and require configured credentials plus a recorded successful send.</p>
    </div>
   </details>
   <details style={{...box,marginTop:14}} id="trial-details" aria-label="FOCUS trial-level source evidence and immutable revision history">
    <summary style={{cursor:"pointer",fontWeight:750,fontSize:17}}>FOCUS trial details · {data.trials.length} exact NCTs · evidence gaps and source revisions</summary>
    <p style={muted}>Every trial inherits the seven recorded FOCUS evidence gates. Source links do not certify the underlying science. A revision is shown only after the authenticated backend confirms that it was saved; unavailable history is marked Unknown.</p>
    <label style={{display:"grid",gap:5,maxWidth:410,fontSize:13,fontWeight:700}}>Search by ticker, company or NCT
      <input type="search" value={trialFilter} onChange={e=>setTrialFilter(e.target.value)}
        placeholder="e.g. NCT06081894 or CYTK"
        style={{padding:"10px",border:"1px solid #b8cfc2",borderRadius:7}}/>
    </label>
    <p style={{...muted,marginTop:8}}>Showing {visibleTrials.length} of {data.trials.length} FOCUS trials. Historical trial identities remain anchored to exact NCT; no retired worksheet is reactivated.</p>
    {visibleTrials.map(t=><details key={t.nct} data-nct={t.nct}
       style={{border:"1px solid #d0e1d5",borderRadius:9,padding:12,margin:"10px 0"}}>
      <summary style={{cursor:"pointer"}}>
        <strong>{t.ticker} · {t.nct}</strong> — {t.company}
        <span style={{display:"block",fontSize:12,color:"#596770",marginTop:3}}>
         {t.pointers} recorded pointers · {t.review} need independent review · {t.missing} missing ·
         saved history {t.sourceState==="OBSERVED"?"observed":"unknown"}
        </span>
      </summary>
      <p style={muted}>Source worker: {t.latestStatus.replaceAll("_"," ")} · Saved source stages: {t.sourceStages===null?"unknown":t.sourceStages+"/12"} · Failed runs: {t.failedRuns===null?"unknown":t.failedRuns}. No FDA approval/CRL/delay probability is validated: <strong>ABSTAIN</strong>. Certainty: <strong>NOT VALIDATED</strong>.</p>
      <details style={{margin:"10px 0"}}>
        <summary style={{cursor:"pointer",fontWeight:700}}>Recorded evidence and missing data · {t.gates.length} checks</summary>
        <div>{t.gates.map(g=><div key={g.id} style={{borderTop:"1px solid #e0e9e1",padding:"8px 0",fontSize:13}}>
         <strong>{g.title}</strong> — {g.state.replaceAll("_"," ")}
         <p style={{...muted,margin:"4px 0"}}>{g.note}</p>
         {g.sourceUrl&&<a href={g.sourceUrl} target="_blank" rel="noopener noreferrer">Recorded original source</a>}
        </div>)}</div>
      </details>
      <details style={{margin:"10px 0"}}>
        <summary style={{cursor:"pointer",fontWeight:700}}>Immutable source revision history · {t.sourceState==="OBSERVED"?t.revisions.length+" recent":"not verified"}</summary>
        {t.sourceState!=="OBSERVED"?<p style={muted}>Saved trial revisions cannot currently be checked against persistent PostgreSQL. No historic revisions were inferred.</p>:
        t.revisions.length===0?<p style={muted}>No saved revisions were reported for this NCT.</p>:
        <ol>{t.revisions.map(r=><li key={r.runId} style={{fontSize:13,margin:"7px 0"}}>
          Revision {r.ordinal} · {r.recordedAt} · evidence changed: {r.evidenceChanged?"Yes":"No"} · run {r.runId}
        </li>)}</ol>}
      </details>
      <p style={{fontSize:12,marginBottom:0}}><Link href={"/focus"}>FOCUS roster</Link> · <a href={"https://clinicaltrials.gov/study/"+t.nct} target="_blank" rel="noopener noreferrer">ClinicalTrials.gov record</a></p>
    </details>)}
   </details>
   <details style={{marginTop:14}} open id="levels">
    <summary style={{cursor:"pointer",fontWeight:750,fontSize:17}}>Expand installation stages — {data.stages.length} groups including all 12 advanced levels</summary>
    <div style={{marginTop:8}}>{data.stages.map(stage=><StagePanel key={stage.id} stage={stage}/>)}</div>
   </details>
   <p style={{...muted,marginTop:16}}>The seven original MAIN Core Platform/Pipeline acceptance gates and their historical evidence remain intact below. This is a new, separately scoped installation monitor, not a rewrite of the historical audit.</p>
   <div style={{display:"flex",flexWrap:"wrap",gap:14,fontSize:13}}>
    <Link href="/precision-monitoring#levels">12 advanced medical levels</Link>
    <Link href="/focus">FOCUS evidence</Link>
    <Link href="/pool">Master POOL</Link>
   </div>
  </>}
 </section>;
}
