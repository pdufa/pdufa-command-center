"use client";
import {useState} from "react";
import focus from "../../data/p3PostDataActive.json";
import {ADVANCED_LEVELS} from "../../lib/precision-monitor-levels";
type Entry={revision:number|null;recordedAt:string|null;status:string;sourceCount:number;gapCount:number;changed:boolean};
type History={nct:string;available:boolean;total:number;records:Entry[];reason?:string};
const muted={fontSize:13,color:"#50675a",lineHeight:1.5} as const;
export default function TrialEvidenceExplorer(){
 const [opened,setOpened]=useState("");
 const [hist,setHist]=useState<Record<string,History>>({});
 const [loading,setLoading]=useState<string|null>(null);
 const [errors,setErrors]=useState<Record<string,string>>({});
 async function view(nct:string){
  setLoading(nct);
  try{
   const r=await fetch("/api/main/installation-trial?nct="+encodeURIComponent(nct),{cache:"no-store"});
   const v:unknown=await r.json();
   if(!r.ok)throw Error(typeof (v as {error?:unknown})?.error==="string"?(v as {error:string}).error:"History lookup unavailable");
   if(!v||typeof v!=="object"||!("nct" in v)||(v as {nct:unknown}).nct!==nct)throw Error("Saved exact-NCT history mismatch");
   setHist(prev=>({...prev,[nct]:v as History}));
   setErrors(prev=>({...prev,[nct]:""}));
  }catch(cause){setErrors(prev=>({...prev,[nct]:cause instanceof Error?cause.message:"Saved history unavailable"}));}
  finally{setLoading(null);}
 }
 return <section style={{border:"1px solid #c5dacf",borderRadius:12,padding:16,background:"#fff",marginTop:16}} aria-label="Expandable trial-level monitoring details">
  <h3 style={{margin:"0 0 7px"}}>FOCUS · trial evidence and revision history</h3>
  <p style={muted}>Expand any current FOCUS trial. Source links are evidence leads rather than regulatory certification. Reading saved history never starts a scan.</p>
  <label style={muted}>Find trial{" "}
   <select value={opened} onChange={e=>{setOpened(e.target.value);}} style={{padding:7}}>
    <option value="">Choose an NCT</option>{focus.records.map(r=><option key={r.nct} value={r.nct}>{r.ticker} · {r.nct}</option>)}
   </select>
  </label>
  <div style={{maxHeight:700,overflowY:"auto",marginTop:12}}>
  {focus.records.filter(r=>!opened||r.nct===opened).map(r=>{
   const history=hist[r.nct];
   return <details key={r.nct} style={{borderTop:"1px solid #e3ede6",padding:"10px 2px"}}>
    <summary style={{cursor:"pointer",fontWeight:700}}>{r.ticker} · {r.nct} · {r.company}</summary>
    <div style={muted}>
     <p><strong>Recorded FDA pathway:</strong> {r.fdaStatus||"Unknown"} · <strong>Historic market cap:</strong> {typeof r.marketCap==="number"?"$"+(r.marketCap/1e9).toFixed(2)+"B":"Unverified"}</p>
     <p><strong>Evidence:</strong> <a href={"https://clinicaltrials.gov/study/"+r.nct} target="_blank" rel="noopener noreferrer">Registry</a>
       {r.resultsUrl?.startsWith("https://")&&<> · <a href={r.resultsUrl} target="_blank" rel="noopener noreferrer">Results source</a></>}
       {r.regulatoryUrl?.startsWith("https://")&&<> · <a href={r.regulatoryUrl} target="_blank" rel="noopener noreferrer">Regulatory source</a></>}
     </p>
     <p><strong>FDA prediction:</strong> ABSTAIN (approval / CRL / delay) · <strong>Certainty:</strong> NOT VALIDATED.</p>
     <details><summary style={{cursor:"pointer",fontWeight:650}}>12 medical levels · missing original evidence</summary>
      <ol>{ADVANCED_LEVELS.map(level=><li key={level.id} style={{margin:"7px 0"}}>
       <strong>{level.title} · not independently signed off</strong>
       <div>{level.failureQuestion}</div>
       <div>Required evidence: {level.requiredEvidence.join("; ")}</div>
      </li>)}</ol>
     </details>
     <button type="button" onClick={()=>void view(r.nct)} disabled={loading===r.nct} style={{padding:"8px 12px",marginTop:8,borderRadius:7,border:"1px solid #9abca7",background:"#f1f8f3"}}>
      {loading===r.nct?"Checking saved revision history…":"Check saved revision history"}
     </button>
     {errors[r.nct]&&<p role="status">{errors[r.nct]}</p>}
     {history&&<div role="status">
      <p>{history.available?history.total+" saved revisions":"Live history unavailable"} · {history.reason??"Source-only history, not a validated FDA forecast"}</p>
      {history.records.map((e,i)=><p key={i}>Revision {e.revision??"unrecorded"} · {e.status} · {e.recordedAt??"unknown date"} · {e.sourceCount} source pointers · {e.gapCount} evidence gaps{e.changed?" · source evidence changed":""}</p>)}
     </div>}
    </div>
   </details>;
  })}
  </div>
 </section>;
}