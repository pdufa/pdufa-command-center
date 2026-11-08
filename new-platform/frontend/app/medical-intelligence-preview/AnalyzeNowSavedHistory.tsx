"use client";
import {useCallback,useEffect,useState} from "react";

type Evidence={url:string;status:string};
type Grade={metricId:string;score:number|null;sourceUrl:string|null};
type Report={
 nct:string;runId:string;runStatus:string;recordedAt:string;trigger:string;version:string;
 stagesAttempted:number;stageCount:number;completedIndependentMedicalReviews:number;
 score:{raas:{value:number|null;status:string;lastEventId:string|null};
  clinicalFive:{value:number|null;status:string;recordedAt:string|null;gradedFactors:Grade[]}};
 scientificAssessment:{status:string;independentlyValidated:boolean;availableSourceStages:number};
 predictions:{outcome:string;status:string;probability:number|null;reason:string}[];
 certainty:{status:string;rating:number|null;reason:string};
 supportingEvidence:Evidence[];
 missing:({stage?:number;component?:string;requirement:string})[];
 legacyHistory:{raasEventIds:string[];clinicalFiveEventIds:string[];
  retainedAcrossSpreadsheetMoves:boolean};
 note:string;
};
type Entry={runId:string;trigger:string;status:string;capturedAt:string;finalizedAt:string|null;
 report:Report;initialReport:Report};
type History={nct:string;identityKey:"EXACT_NCT";history:Entry[];note:string};
const small={fontSize:13,color:"#4b6156",lineHeight:1.5} as const;
function renderScore(value:number|null,unit:string){return value===null?"Not available":value.toFixed(1)+" "+unit;}
function RenderReport({report}:{report:Report}){
 return <div style={{marginTop:10}}>
  <p style={small}>Recorded {report.recordedAt} · {report.stagesAttempted}/{report.stageCount} source stages attempted · {report.completedIndependentMedicalReviews} independently completed medical reviews</p>
  <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(175px,1fr))",gap:9}}>
   <div style={{padding:12,background:"#f2f8f3",borderRadius:8}}>
    <div style={small}>Full 30-metric RAAS rating</div>
    <strong>{renderScore(report.score.raas.value,"/ 100")}</strong>
    <p style={small}>Archived-only. No new RAAS rating is calculated.</p>
   </div>
   <div style={{padding:12,background:"#f2f8f3",borderRadius:8}}>
    <div style={small}>Existing five-factor clinical research grade</div>
    <strong>{renderScore(report.score.clinicalFive.value,"/ 100")}</strong>
    <p style={small}>{report.score.clinicalFive.status.replaceAll("_"," ")}</p>
   </div>
   <div style={{padding:12,background:"#f2f8f3",borderRadius:8}}>
    <div style={small}>Independent scientific assessment</div>
    <strong>{report.scientificAssessment.status.replaceAll("_"," ")}</strong>
    <p style={small}>Source leads: {report.scientificAssessment.availableSourceStages}; not an FDA determination</p>
   </div>
   <div style={{padding:12,background:"#f2f8f3",borderRadius:8}}>
    <div style={small}>Prediction certainty</div>
    <strong>{report.certainty.rating===null?"Not validated":String(report.certainty.rating)}</strong>
    <p style={small}>{report.certainty.reason}</p>
   </div>
  </div>
  <h4 style={{marginBottom:5}}>FDA decisions (separate outcomes)</h4>
  <div style={{display:"flex",gap:9,flexWrap:"wrap"}}>
   {report.predictions.map(p=><div key={p.outcome} style={{padding:10,border:"1px solid #cedbd1",borderRadius:7,flex:"1 1 160px"}}>
    <strong>{p.outcome.replaceAll("_"," ")}: {p.status}</strong>
    <div style={small}>Probability: {p.probability===null?"Not issued":String(p.probability)}</div>
   </div>)}
  </div>
  <details style={{marginTop:11}}>
   <summary style={{cursor:"pointer",fontWeight:700}}>Archived clinical factor grades ({report.score.clinicalFive.gradedFactors.length})</summary>
   <ul style={{fontSize:13}}>
    {report.score.clinicalFive.gradedFactors.map(g=><li key={g.metricId}>{g.metricId}: {g.score===null?"Unscored":String(g.score)+"/100"}
      {g.sourceUrl&&<> · <a href={g.sourceUrl} target="_blank" rel="noopener noreferrer">Original source</a></>}
    </li>)}
   </ul>
  </details>
  <details style={{marginTop:11}}>
   <summary style={{cursor:"pointer",fontWeight:700}}>Supporting source pointers ({report.supportingEvidence.length})</summary>
   <p style={small}>Recorded URLs and historical research evidence are leads, not independent confirmation.</p>
   <ul style={{fontSize:12,overflowWrap:"anywhere"}}>{report.supportingEvidence.map(s=><li key={s.url}><a href={s.url} target="_blank" rel="noopener noreferrer">{s.url}</a></li>)}</ul>
  </details>
  <details style={{marginTop:11}}>
   <summary style={{cursor:"pointer",fontWeight:700}}>Missing evidence and unavailable components ({report.missing.length})</summary>
   <ul style={{fontSize:13,lineHeight:1.5}}>{report.missing.map((m,i)=><li key={i}><strong>{m.component??(m.stage?"Stage "+m.stage:"Other")}:</strong> {m.requirement}</li>)}</ul>
  </details>
  <p style={{...small,marginTop:12}}>Prior archived event references: {report.legacyHistory.raasEventIds.length} RAAS, {report.legacyHistory.clinicalFiveEventIds.length} clinical-five. Saved history is keyed to the exact NCT and does not reset when a trial changes spreadsheet.</p>
 </div>;
}
export default function AnalyzeNowSavedHistory({nct}:{nct:string}){
 const [history,setHistory]=useState<History|null>(null);
 const [loading,setLoading]=useState(true);
 const [error,setError]=useState("");
 const fetchHistory=useCallback(async()=>{
  try{
   const q=new URLSearchParams({nct,analysis:"1"});
   const response=await fetch("/api/medical-intelligence-preview/continuous?"+q,{cache:"no-store"});
   const value:unknown=await response.json().catch(()=>null);
   if(!response.ok){
    const failure=value&&typeof value==="object"&&"error" in value?
       (value as {error?:unknown}).error:null;
    throw Error(typeof failure==="string"?failure:"Saved Analyze Now history is not accessible.");
   }
   const obj=value as History;
   if(obj?.nct!==nct||obj.identityKey!=="EXACT_NCT"||!Array.isArray(obj.history))
     throw Error("Analyze Now response did not match this NCT.");
   setHistory(obj);setError("");
  }catch(e){setError(e instanceof Error?e.message:"Unable to read saved analysis history.");}
  finally{setLoading(false);}
 },[nct]);
 useEffect(()=>{void fetchHistory();},[fetchHistory]);
 useEffect(()=>{
  if(!history?.history.some(x=>x.status==="PENDING"||x.status==="RUNNING"))return;
  const timer=setInterval(()=>void fetchHistory(),6500);
  return ()=>clearInterval(timer);
 },[history,fetchHistory]);
 return <section aria-label="Analyze Now saved results and trial history" style={{padding:16,marginTop:16,background:"#fff",border:"1px solid #bad5c2",borderRadius:11}}>
  <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",gap:10,flexWrap:"wrap"}}>
   <h2 style={{margin:0,fontSize:20}}>Analyze Now · saved scores, evidence and history</h2>
   <button type="button" disabled={loading} onClick={()=>void fetchHistory()} style={{borderRadius:7,padding:"9px 12px"}}>Refresh saved analysis</button>
  </div>
  <p style={small}>Uses the operational evidence worker and existing archived clinical research. It does not require future advanced installations. A full RAAS score, FDA probability, or certainty number is never guessed.</p>
  {error&&<p role="alert" style={{color:"#a0362d"}}>{error}</p>}
  {loading&&!history&&<p role="status">Checking saved analysis history…</p>}
  {history&&history.history.length===0&&<p style={small}>No analysis has been started for this exact trial. Use Analyze Now from FOCUS to create the first saved result.</p>}
  {history?.history.map((e,i)=><details key={e.runId} open={i===0} style={{marginTop:9,padding:12,borderRadius:9,border:"1px solid #dae5db"}}>
   <summary style={{cursor:"pointer",fontWeight:700}}>{e.capturedAt} · {e.trigger.replaceAll("_"," ")} · {e.status}</summary>
   <RenderReport report={e.report}/>
  </details>)}
 </section>;
}
