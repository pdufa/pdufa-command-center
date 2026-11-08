"use client";
import {useState} from "react";
import Link from "next/link";

/** One action for each exact-NCT FOCUS trial; never starts an advanced install. */
export default function AnalyzeNowTrial({nct}:{nct:string}){
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState("");
 const [accepted,setAccepted]=useState(false);
 const destination="/medical-intelligence-preview?nct="+encodeURIComponent(nct)+"#continuous-medical-analysis";
 async function start(){
  if(busy)return;
  setBusy(true);setError("");
  try{
   const response=await fetch("/api/medical-intelligence-preview/continuous",{
     method:"POST",cache:"no-store",
     headers:{"Content-Type":"application/json"},
     body:JSON.stringify({action:"analyze",nct,requestKey:crypto.randomUUID()})
   });
   const obj:unknown=await response.json().catch(()=>null);
   if(!response.ok){
    const problem=obj&&typeof obj==="object"&&"error" in obj?
      (obj as {error?:unknown}).error:null;
    throw Error(typeof problem==="string"?problem:"Analyze Now could not start; no analysis was saved.");
   }
   const run=obj as {nct?:string;runId?:string;status?:string};
   if(run.nct!==nct||!run.runId||!["PENDING","RUNNING","COMPLETE"].includes(run.status??""))
    throw Error("Research backend did not confirm the exact trial identity.");
   setAccepted(true);
   window.location.assign(destination);
  }catch(cause){
   setError(cause instanceof Error?cause.message:"Analyze Now unavailable; no result claimed.");
  }finally{setBusy(false);}
 }
 return <div style={{display:"grid",gap:5,minWidth:145}}>
  <button type="button" disabled={busy||accepted} onClick={()=>void start()}
   aria-label={"Analyze Now for "+nct}
   style={{padding:"9px 12px",borderRadius:7,border:0,
    background:"#075f4f",color:"white",fontWeight:750,cursor:busy?"wait":"pointer"}}>
   {busy?"Starting…":accepted?"Analysis queued":"Analyze Now"}
  </button>
  <Link href={destination} style={{fontSize:12}}>Results &amp; saved history</Link>
  {error&&<p role="alert" style={{fontSize:12,color:"#9b342f",margin:0,maxWidth:240}}>{error}</p>}
 </div>;
}
