"use client";

import {useCallback,useEffect,useState} from "react";

type Stage={
  id:string; label:string; workflow:string|null; integration:string; needs:string[];
  status?:string; attempts?:number; workflowRunId?:number|null;
  inputDigest?:string|null; outputDigest?:string|null; updatedAt?:string;
  errorCode?:string|null; leaseUntil?:string|null;
};
type Run={
  id:string; runKey:string; sourceSha:string; version:number; status:string;
  generation:number; updatedAt:string; createdAt:string; stages:Stage[];
  fullEndToEndCertified:false; tradingOrdersEnabled:false;
  events:{event:string;at:string;stage?:string}[];
};
type ResponseData={
  configured:boolean; writesEnabled:boolean; workflowExecutionEnabled:boolean;
  latest:Run|null; stages:Stage[]; fullEndToEndCertified:false; tradingOrdersEnabled:false;
};

const GH="https://github.com/pdufa/pdufa-command-center/actions/workflows/master-automation-manual.yml";
function clock(iso?:string|null){
  if(!iso)return "—";
  const time=Date.parse(iso);
  return Number.isFinite(time)?new Intl.DateTimeFormat("en-US",{
    timeZone:"America/Los_Angeles",dateStyle:"medium",timeStyle:"short"
  }).format(new Date(time)):"—";
}
function short(v?:string|null){
  return v?v.slice(0,12)+"…":"—";
}
const panel={border:"1px solid #b6c9c5",borderRadius:12,padding:16,background:"#fff"} as const;
const pill=(status:string)=>({
  display:"inline-block",border:"1px solid #b3c8c5",borderRadius:8,
  padding:"3px 8px",fontSize:12,fontWeight:700,
  color:status==="SUCCEEDED"?"#095a3b":status==="FAILED"?"#a12a21":"#3c5354",
  background:status==="SUCCEEDED"?"#e8f8f1":status==="FAILED"?"#fff1ed":"#eff5f4",
});

export default function MasterAutomationDashboard(){
  const [data,setData]=useState<ResponseData|null>(null);
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(false);
  const refresh=useCallback(async()=>{
    setLoading(true);setError("");
    try{
      const response=await fetch("/api/master-automation",{cache:"no-store"});
      const body=await response.json();
      if(!response.ok)throw Error(typeof body.error==="string"?body.error:"Controller status HTTP "+response.status);
      if(!Array.isArray(body.stages))throw Error("Invalid controller response");
      setData(body as ResponseData);
    }catch(e){
      setError(e instanceof Error?e.message:"Status currently unavailable");
    }finally{setLoading(false);}
  },[]);
  useEffect(()=>{void refresh()},[refresh]);
  const run=data?.latest;
  const stages=run?.stages || data?.stages || [];
  const managed=stages.filter(s=>s.integration==="MANAGED");
  const succeeded=managed.filter(s=>s.status==="SUCCEEDED").length;
  const failed=stages.find(s=>s.status==="FAILED");

  return <main style={{maxWidth:1200,margin:"0 auto",padding:"20px 16px 48px",fontFamily:"inherit"}}>
    <nav style={{marginBottom:12}}>
      <a href="/">PDUFA home</a>{" · "}<a href="/wt">WT</a>{" · "}<a href={GH} target="_blank" rel="noopener noreferrer">GitHub controller</a>
    </nav>
    <h1>MASTER AUTOMATION CONTROLLER</h1>
    <p>Checkpointed execution status, exact failure point, and resume instructions. This page never submits a trade or starts a workflow.</p>
    <div style={{display:"flex",gap:10,flexWrap:"wrap",margin:"16px 0"}}>
      <button type="button" onClick={()=>void refresh()} disabled={loading}>
        {loading?"Checking status…":"Refresh live status"}
      </button>
      <a href={GH} target="_blank" rel="noopener noreferrer">Open manual Plan / Run / Resume workflow</a>
    </div>
    {error&&<p role="alert" style={{color:"#a12a21"}}><strong>Status unavailable:</strong> {error}. No previously saved checkpoints were deleted.</p>}
    {!data&&!error&&<p role="status">Checking authenticated controller status…</p>}
    {data&&<div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(210px,1fr))",gap:12,marginBottom:16}}>
      <section style={panel}>
        <small>Last managed run</small>
        <h2 style={{margin:"8px 0"}}>{run?.status.replaceAll("_"," ")||"NOT STARTED"}</h2>
        <small>{run?clock(run.updatedAt):"No controller run saved"}</small>
      </section>
      <section style={panel}>
        <small>Verified managed checkpoints</small>
        <h2 style={{margin:"8px 0"}}>{succeeded} / {managed.length}</h2>
        <small>POOL and FOCUS only in this installation</small>
      </section>
      <section style={panel}>
        <small>Runtime execution</small>
        <h2 style={{margin:"8px 0"}}>{data.writesEnabled?"OPT-IN ENABLED":"READ ONLY"}</h2>
        <small>Automatic production deploys and orders disabled</small>
      </section>
    </div>}
    {run&&<section style={{...panel,marginBottom:16}}>
      <h2>Run information</h2>
      <p><strong>Run key:</strong> {run.runKey} {" · "}<strong>Generation:</strong> {run.generation} {" · "}<strong>Revision:</strong> {run.version}</p>
      <p><strong>Run ID:</strong> <code style={{overflowWrap:"anywhere"}}>{run.id}</code></p>
      <p><strong>Pinned starting commit:</strong> <code>{short(run.sourceSha)}</code></p>
      {failed&&<div role="alert" style={{border:"1px solid #e2aca6",borderRadius:9,padding:12}}>
        <strong>Stopped at {failed.id} — {failed.errorCode||"unknown failure"}</strong>
        <p style={{marginBottom:6}}>Valid earlier checkpoints remain saved. A retry must use the existing Run ID and select <strong>{failed.id}</strong> as the failed stage in the manual controller workflow. Only that stage and its dependents will be reset.</p>
        <a href={GH} target="_blank" rel="noopener noreferrer">Open GitHub to resume failed stage</a>
      </div>}
    </section>}
    {data&&<section style={{...panel,marginBottom:16}}>
      <h2>Stage dependency and completion status</h2>
      <div style={{display:"grid",gap:10}}>
        {stages.map((s,i)=><article key={s.id} style={{borderBottom:i===stages.length-1?"none":"1px solid #e3eaea",paddingBottom:10}}>
          <div style={{display:"flex",justifyContent:"space-between",gap:12,flexWrap:"wrap"}}>
            <strong>{i+1}. {s.label}</strong>
            <span style={pill(s.status||s.integration)}>{(s.status||s.integration).replaceAll("_"," ")}</span>
          </div>
          <p style={{margin:"6px 0",fontSize:13}}>
            Depends on: {s.needs.length?s.needs.join(", "):"independent"} {" · "}
            {s.integration==="MANAGED"?"Checkpoint controlled":s.integration==="OBSERVE_ONLY"?"Separate existing workflow":s.integration==="NOT_WIRED"?"Not connected to controller":"Independent from main chain"}
          </p>
          {s.workflowRunId&&<p style={{margin:"4px 0",fontSize:13}}>
            <a href={"https://github.com/pdufa/pdufa-command-center/actions/runs/"+s.workflowRunId} target="_blank" rel="noopener noreferrer">GitHub evidence run #{s.workflowRunId}</a>
            {" · "}Attempts: {s.attempts||0} {" · "}Verified output: {short(s.outputDigest)}
          </p>}
          {s.errorCode&&<p style={{color:"#a12a21",margin:"4px 0"}}>{s.errorCode}</p>}
        </article>)}
      </div>
    </section>}
    <section style={panel}>
      <h2>Safety and integration scope</h2>
      <p><strong>Current controlled chain:</strong> POOL → FOCUS. Scientific assessments, predictions, CAL/company/news and alerts are shown as not yet wired, rather than falsely marked complete.</p>
      <p><strong>ATSMS and backups:</strong> Remain on their independent schedules. ATSMS cannot produce valid Alpaca readings until its HTTP 401 authentication issue is repaired.</p>
      <p><strong>Resume:</strong> Preserves successful upstream checkpoint evidence, requires a failed stage and an explicit GitHub workflow action. A crashed worker must first pass lease-expiry recovery; no silent restart or double-dispatch.</p>
      <p style={{marginBottom:0}}><strong>No brokerage orders, production merges or deployments are enabled by this controller.</strong></p>
    </section>
  </main>;
}
