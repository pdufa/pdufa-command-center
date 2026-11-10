"use client";
import {useEffect,useRef,useState} from "react";
import type {PilotMethodAuditObservation} from "../../../lib/medical-method-audit";

const box={border:"1px solid #9dbbb4",background:"#fff",borderRadius:10,padding:12,marginTop:12} as const;
export default function PilotMethodAuditMonitor({nct}:{nct:string}){
  const [observation,setObservation]=useState<PilotMethodAuditObservation|null>(null);
  const [error,setError]=useState("");
  const [lastChecked,setLastChecked]=useState<string|null>(null);
  const [starting,setStarting]=useState(false);
  const [loading,setLoading]=useState(true);
  const pollRef=useRef<(()=>void)|null>(null);
  useEffect(()=>{
    if(nct!=="NCT06081894")return;
    let disposed=false,fetching=false;
    const controller=new AbortController();
    setObservation(null);setError("");setLoading(true);setLastChecked(null);
    async function getStatus(){
      if(disposed||fetching||controller.signal.aborted)return;
      fetching=true;
      try{
        const response=await fetch("/api/predictions/medical-method-audit?nct="+encodeURIComponent(nct),
          {cache:"no-store",signal:controller.signal});
        const body=await response.json() as PilotMethodAuditObservation & {error?:string};
        if(!response.ok||body.nct!==nct||!["RUN","NO_RUN"].includes(body.kind))
          throw Error(body.error||"Isolated audit status could not be verified");
        if(!disposed&&!controller.signal.aborted){
          setObservation(body);setError("");setLastChecked(new Date().toISOString());
        }
      }catch(e){
        if(!disposed&&!controller.signal.aborted)
          setError(e instanceof Error?e.message:"Source-audit worker unavailable");
      }finally{fetching=false;if(!disposed&&!controller.signal.aborted)setLoading(false);}
    }
    pollRef.current=()=>{void getStatus();};
    void getStatus();
    const interval=window.setInterval(()=>{if(document.visibilityState==="visible")void getStatus();},15000);
    const onVisible=()=>{if(document.visibilityState==="visible")void getStatus();};
    document.addEventListener("visibilitychange",onVisible);
    return()=>{
      disposed=true;controller.abort();window.clearInterval(interval);
      document.removeEventListener("visibilitychange",onVisible);pollRef.current=null;
    };
  },[nct]);
  if(nct!=="NCT06081894")return null;
  const run=observation?.kind==="RUN"?observation:null;
  const live=run&&!error?run:null;
  async function startAudit(){
    if(starting)return;
    setStarting(true);setError("");
    try{
      const response=await fetch("/api/predictions/medical-method-audit?nct="+encodeURIComponent(nct),{
        method:"POST",headers:{"Content-Type":"application/json"},body:"{}",cache:"no-store"
      });
      const body=await response.json() as PilotMethodAuditObservation & {error?:string};
      if(!response.ok||body.kind!=="RUN"||body.nct!==nct)
        throw Error(body.error||"No verified new audit run was started");
      setObservation(body);setLastChecked(new Date().toISOString());
      pollRef.current?.();
    }catch(e){setError(e instanceof Error?e.message:"Cannot start verified pilot source audit");}
    finally{setStarting(false);}
  }
  const formatted=lastChecked?new Date(lastChecked).toLocaleTimeString(undefined,{hour:"numeric",minute:"2-digit",second:"2-digit"}):"Not available";
  const status=error?"UNAVAILABLE":live?.status??(observation?.kind==="NO_RUN"?"NOT STARTED":"CHECKING");
  return <section style={box} aria-label="Live ACACIA 800-position source audit">
    <div style={{display:"flex",justifyContent:"space-between",flexWrap:"wrap",gap:8}}>
      <strong>800-method source-evidence audit · ACACIA-HCM</strong>
      <span role="status" style={{fontWeight:800,color:status==="COMPLETE"?"#22664d":"#7a4d19"}}>{status}</span>
    </div>
    <p style={{fontSize:13,margin:"7px 0"}}>A real, durable audit of the existing 40 × 20 source classifications. It verifies which source-research category is saved at each method position; it <strong>does not assign clinical grades or calculate FDA probabilities</strong>.</p>
    <progress aria-label="Audited source-classification method positions, not clinical grades"
      max={800} value={live?live.completedPositions:0} style={{width:"100%",height:12}}/>
    <p style={{fontSize:13,margin:"5px 0"}}>
      {live?live.completedPositions+"/800 source positions checked · "+live.completedAssessmentGroups+"/40 assessment groups checked":
        error?"Current progress withheld: backend status cannot be verified.":"No verified pilot source-audit progress yet."}
    </p>
    {live?.status==="RUNNING"&&live.currentAssessmentIndex&&live.currentMethodIndex?
      <p style={{fontSize:13}}>Current source check: <strong>Assessment {live.currentAssessmentIndex}, Method {live.currentMethodIndex}</strong>. This identifies the next position to check, not a currently assigned scientific grade.</p>:null}
    {live?.status==="COMPLETE"?<p style={{fontSize:13}}><strong>All 800 source classifications checked.</strong> Independent clinical method grades remain a different review requirement.</p>:null}
    {live?.status==="FAILED"?<p style={{fontSize:13}}>The recorded run failed ({live.failureKind??"cause not provided"}). A resume can be attempted using the same saved source snapshot.</p>:null}
    {live?<p style={{fontSize:12,overflowWrap:"anywhere"}}>Audit run: {live.runId} · Source snapshot: {live.sourceSnapshotId} · Last update: {new Date(live.updatedAt).toLocaleString()}</p>:null}
    {error?<p role="alert" style={{fontSize:13,color:"#a33225"}}>{error} No completion or grading is inferred.</p>:null}
    {loading?<p role="status" style={{fontSize:12}}>Checking isolated audit run…</p>:null}
    <div style={{display:"flex",gap:8,flexWrap:"wrap",alignItems:"center",marginTop:9}}>
      <button type="button" onClick={()=>void startAudit()}
        disabled={starting||loading||run?.status==="RUNNING"||run?.status==="PENDING"||run?.status==="COMPLETE"}
        style={{border:"1px solid #37735e",borderRadius:8,background:"#e0f5e9",padding:"9px 12px",fontWeight:750,color:"#245a43"}}>
        {starting?"Starting verified audit…":run?.status==="FAILED"?"Resume source audit":"Start 800-position source audit"}
      </button>
      <button type="button" onClick={()=>pollRef.current?.()} style={{border:"1px solid #9fbdb1",borderRadius:8,background:"#fff",padding:"9px 12px",color:"#245a43"}}>
        Refresh audit status
      </button>
      <span style={{fontSize:12}}>Last checked: {formatted}</span>
    </div>
    {live&&live.recentEvents.length>0?<details style={{marginTop:10}}>
      <summary style={{cursor:"pointer",fontWeight:750}}>Latest actual method-position receipts</summary>
      <ol>{live.recentEvents.map(row=><li key={row.position_index}>
        Position {row.position_index} · Assessment {row.assessment_index} / Method {row.method_index} · {row.source_class} ({row.source_count} source lead records)
      </li>)}</ol>
    </details>:null}
    <p style={{fontSize:12,color:"#587267",marginBottom:0}}>The run is launched only by an explicit click. A previously completed source snapshot is reused instead of generating fake new work. Accurate FDA outcomes and provisional clinical scores remain unavailable until independent grading and validation are performed.</p>
  </section>;
}
