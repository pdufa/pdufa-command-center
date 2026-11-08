"use client";
import {useEffect,useState} from "react";

type SavedAnalysis={
 schema:string;savedAt:string;nct:string;trigger:string;
 scientificAssessment:{status:string;stagesAttempted:number;sourceRecordedStages:number;
  sourceChecks:{stage:number;title:string;status:string;source:string|null}[];
  independentScientificSignoff:boolean;explanation:string};
 fdaPredictions:{outcome:string;status:string;probability:null;reason:string}[];
 certainty:{status:string;rating:null;reason:string};
 missingEvidence:{stage:number|null;missing:string}[];
 supportingSourceUrls:string[];
 componentReadiness:Record<string,string>;
 warning:string;
};
type Run={
 nct:string;runId:string;status:"PENDING"|"RUNNING"|"COMPLETE"|"FAILED"|"STOPPED";
 startedAt:string;updatedAt:string;completedStages:number;totalStages:number;
 analysis:SavedAnalysis|null;revision:number|null;savedAt:string|null;
};
type History={nct:string;historyKey:string;locationIndependent:boolean;total:number;
 records:{runId:string;revision:number|null;status?:string;savedAt:string;evidenceChanged:boolean;analysis:SavedAnalysis|null}[]};
const border="#cadae0",dim="#586e62",teal="#00695a";
const caption={fontSize:12,color:dim,lineHeight:1.45} as const;
function Report({a}:{a:SavedAnalysis}){
 return <div style={{fontSize:12,lineHeight:1.55,paddingTop:9}}>
  <p style={{margin:"4px 0"}}><strong>Saved:</strong> {a.savedAt} · {a.trigger.replaceAll("_"," ")}</p>
  <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(160px,1fr))",gap:9}}>
   <div><strong>Source checks attempted</strong><div>{a.scientificAssessment.stagesAttempted} / 12</div>
    <small>Available operational source-collection stages</small></div>
   <div><strong>Sources recorded</strong><div>{a.scientificAssessment.sourceRecordedStages} / {a.scientificAssessment.stagesAttempted}</div>
    <small>Not a medical effectiveness rating</small></div>
   <div><strong>Scientific review</strong><div>{a.scientificAssessment.status.replaceAll("_"," ")}</div>
    <small>Independent signoff: {a.scientificAssessment.independentScientificSignoff?"Yes":"Not completed"}</small></div>
   <div><strong>Prediction certainty</strong><div>{a.certainty.rating===null?"Not validated":a.certainty.rating}</div>
    <small>{a.certainty.status.replaceAll("_"," ")}</small></div>
  </div>
  <div style={{marginTop:9,borderTop:"1px solid "+border,paddingTop:9}}>
   <strong>Independent FDA outcomes</strong>
   <div style={{display:"flex",flexWrap:"wrap",gap:8,marginTop:5}}>
    {a.fdaPredictions.map(p=><span key={p.outcome} style={{padding:"5px 8px",border:"1px solid "+border,borderRadius:5}}>
      {p.outcome.replaceAll("_"," ")}: <strong>{p.status}</strong> · no validated probability
    </span>)}
   </div>
  </div>
  <details style={{marginTop:9}}><summary style={{cursor:"pointer",fontWeight:700}}>Scientific source checks ({a.scientificAssessment.sourceChecks.length})</summary>
   <ul style={{paddingLeft:18,margin:"5px 0"}}>{a.scientificAssessment.sourceChecks.map(x=><li key={x.stage}>
    Stage {x.stage}: {x.title} · {x.status.replaceAll("_"," ")}
    {x.source&&<> · <a href={x.source} target="_blank" rel="noopener noreferrer">Inspect source</a></>}
   </li>)}</ul>
  </details>
  <details style={{marginTop:9}}><summary style={{cursor:"pointer",fontWeight:700}}>Missing evidence / unavailable components ({a.missingEvidence.length})</summary>
   <ul style={{paddingLeft:18,margin:"5px 0"}}>{a.missingEvidence.map((x,i)=><li key={i}>{x.stage!==null?"Stage "+x.stage+": ":""}{x.missing}</li>)}</ul>
  </details>
  <details style={{marginTop:9}}><summary style={{cursor:"pointer",fontWeight:700}}>Supporting source pointers ({a.supportingSourceUrls.length})</summary>
   {a.supportingSourceUrls.length?<ul style={{paddingLeft:18}}>{a.supportingSourceUrls.slice(0,25).map((url,i)=>
    <li key={i} style={{overflowWrap:"anywhere"}}><a href={url} target="_blank" rel="noopener noreferrer">{url}</a></li>)}</ul>:<p>No source links yet.</p>}
  </details>
  <p style={{...caption,marginTop:10}}>{a.warning}</p>
 </div>;
}

/** Per-trial control. Nothing runs until the operator clicks. No duplicate worker. */
export default function AnalyzeNowTrial({nct,enabled,historyOnly=false}:{nct:string;enabled:boolean;historyOnly?:boolean}){
 const [run,setRun]=useState<Run|null>(null);
 const [history,setHistory]=useState<History|null>(null);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState("");
 const [note,setNote]=useState("");
 const endpoint="/api/analyze-now";
 async function refresh(){
  try{
   const r=await fetch(endpoint+"?"+new URLSearchParams({nct}),{cache:"no-store"});
   if(r.status===404)return;
   const data:unknown=await r.json();
   if(!r.ok)throw Error((data as {error?:string})?.error||"Cannot load analysis");
   const saved=data as Run;
   if(saved.nct!==nct||saved.totalStages!==12)throw Error("Trial identity or analysis stage mismatch");
   setRun(saved);
  }catch(e){setError(e instanceof Error?e.message:"Analysis status unavailable");}
 }
 useEffect(()=>{
  if(run?.status!=="PENDING"&&run?.status!=="RUNNING")return;
  const interval=setInterval(()=>{void refresh();},3500);
  return ()=>clearInterval(interval);
 // Only the active run status determines polling, not the expanded details.
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[run?.runId,run?.status,nct]);
 async function analyze(){
  if(!enabled||busy)return;
  setBusy(true);setError("");setNote("");
  try{
   const res=await fetch(endpoint,{method:"POST",cache:"no-store",
     headers:{"Content-Type":"application/json"},
     body:JSON.stringify({nct,requestKey:crypto.randomUUID()})});
   const data:unknown=await res.json();
   if(!res.ok)throw Error((data as {error?:string})?.error||"Analyze Now could not start");
   const saved=data as Run;
   if(saved.nct!==nct||saved.totalStages!==12)throw Error("Returned analysis does not match trial");
   setRun(saved);
   setNote("Analysis request recorded. Progress is persisted by the existing medical worker.");
  }catch(e){setError(e instanceof Error?e.message:"Analyze Now failed to start");}
  finally{setBusy(false);}
 }
 async function loadHistory(){
  setBusy(true);setError("");
  try{
   const q=new URLSearchParams({nct,history:"1"});
   const response=await fetch(endpoint+"?"+q,{cache:"no-store"});
   const raw:unknown=await response.json();
   if(!response.ok)throw Error((raw as {error?:string})?.error||"Saved history unavailable");
   const data=raw as History;
   if(data.nct!==nct||data.historyKey!=="EXACT_NCT"||!Array.isArray(data.records))
     throw Error("Exact NCT history mismatch");
   setHistory(data);
  }catch(e){setError(e instanceof Error?e.message:"Cannot inspect trial history");}
  finally{setBusy(false);}
 }
 return <div style={{minWidth:145}}>
  <div style={{display:"flex",flexWrap:"wrap",gap:5}}>
   {!historyOnly&&<button type="button" onClick={()=>void analyze()} disabled={!enabled||busy||run?.status==="PENDING"||run?.status==="RUNNING"}
    style={{padding:"8px 10px",background:enabled?teal:"#d6e0da",color:enabled?"white":"#50685d",border:0,borderRadius:7,fontWeight:750,fontSize:12,cursor:enabled?"pointer":"not-allowed"}}>
    Analyze Now
   </button>}
   <button type="button" onClick={()=>void loadHistory()} disabled={busy}
    style={{padding:"8px 10px",border:"1px solid "+border,borderRadius:7,fontSize:12}}>History</button>
  </div>
  {!enabled&&!historyOnly&&<p style={{...caption,marginTop:5}}>Pilot verification first; full rollout is gated.</p>}
  {run&&<p role="status" style={{...caption,margin:"5px 0"}}>{run.status} · {run.completedStages}/12 stages{run.revision?" · revision "+run.revision:""}</p>}
  {note&&<p style={caption}>{note}</p>}
  {error&&<p role="alert" style={{...caption,color:"#9b3934"}}>{error}</p>}
  {run?.analysis&&<details style={{marginTop:8}}><summary style={{cursor:"pointer",fontWeight:750,fontSize:12}}>View saved analysis</summary>
   <Report a={run.analysis}/>
  </details>}
  {history&&<details open style={{marginTop:8}}><summary style={{fontWeight:700,cursor:"pointer",fontSize:12}}>
    {history.total} archived research report{history.total===1?"":"s"} · exact NCT
   </summary>
   {history.records.length===0&&<p style={caption}>No completed saved reports. A pending run is not yet a historical analysis.</p>}
   {history.records.map(h=><details key={h.runId} style={{borderTop:"1px solid "+border,padding:"6px 0"}}>
    <summary style={{cursor:"pointer",fontSize:12}}>{h.revision===null?(h.status??"PENDING")+" · initial report":"#"+h.revision} · {h.savedAt} · {h.revision===null?"awaiting final source revision":h.evidenceChanged?"evidence changed":"evidence unchanged"}</summary>
    {h.analysis?<Report a={h.analysis}/>:<p style={caption}>Older source-only revision retained; optional Analyze Now report did not exist for this run.</p>}
   </details>)}
  </details>}
 </div>;
}
