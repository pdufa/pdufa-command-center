"use client";

import {useEffect,useState} from "react";
import type {AssessmentRun,TrialResult,LevelResult} from "../lib/level16-assessment-runner";

type Options={evidenceCutoffDate:string;trials:{nct:string;ticker:string;company:string;indication:string}[]};
const endpoint="/api/assessments/levels1-6";
const names=["Source provenance","Trial identity and phase","Clinical efficacy and safety","Protocol and trial design","Statistics and analysis plan","Endpoint clinical relevance"];
const button={padding:"10px 14px",borderRadius:8,border:"1px solid #087760",background:"#087760",color:"white",fontWeight:750,cursor:"pointer"} as const;
const pretty=(text:string)=>text.replaceAll("_"," ");
function sourceLink(url:string){try{const u=new URL(url);return u.protocol==="https:"&&!u.username&&!u.password?u.href:null;}catch{return null;}}
function LevelAssessment({level}:{level:LevelResult}){
 const [open,setOpen]=useState(false);
 return <details open={open} onToggle={event=>setOpen(event.currentTarget.open)} style={{padding:"10px 0",borderTop:"1px solid #dbe7e1"}}>
  <summary style={{cursor:"pointer",fontWeight:750}}>Level {level.level} — {names[level.level-1]} · {pretty(level.researchStatus)}</summary>
  {open&&<div>
   <p>{level.interpretation}</p>
   <ul>{level.checks.map(c=><li key={c.id}><strong>{c.label}: {pretty(c.state)}</strong> — {c.reason}</li>)}</ul>
   <h4>Source observations</h4>
   {level.facts.map((fact,i)=><div key={i} style={{margin:"8px 0"}}><p>{fact.text}</p>
    {fact.value!==null&&<pre style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere",fontSize:12,maxHeight:280,overflow:"auto"}}>{JSON.stringify(fact.value,null,2)}</pre>}
    <small>{fact.locator} · {sourceLink(fact.sourceUrl)&&<a href={fact.sourceUrl} target="_blank" rel="noopener noreferrer">Original source</a>}</small></div>)}
   <p><strong>Reasons:</strong> {level.reasons.join("; ")}</p>
   <p><strong>Contradictions and reconciliation questions:</strong> {level.contradictions.join("; ")||"None identified in this package; not proof that no conflict exists."}</p>
   <p><strong>Limitations:</strong> {level.limitations.join("; ")}</p>
   <p><strong>Owner questions:</strong> {level.questions.join("; ")}</p>
   {level.notYetExpected.length>0&&<p><strong>Not yet expected:</strong> {level.notYetExpected.map(pretty).join("; ")}</p>}
   <p><strong>Owner review:</strong> {pretty(level.ownerReviewStatus)}. No outside signoff required.</p>
  </div>}
 </details>;
}
function TrialAssessment({trial}:{trial:TrialResult}){
 return <article style={{padding:"14px 0",borderTop:"1px solid #c5dad2"}}>
  <h3 style={{margin:"3px 0"}}>{trial.ticker} · {trial.nct}</h3>
  <p>{trial.company} · {trial.indications.join("; ")}</p>
  <p>Registry-listed phase: <strong>{trial.phases.join(", ")||"Unknown"}</strong> · Status: {trial.registryStatus||"Unknown"} · {pretty(trial.applicationMappingStatus)}</p>
  {trial.levels.map(level=><LevelAssessment key={level.level} level={level}/>)}
  {trial.statisticalChronology&&<details><summary>Statistical chronology</summary><pre style={{whiteSpace:"pre-wrap",fontSize:12}}>{JSON.stringify(trial.statisticalChronology,null,2)}</pre></details>}
  {trial.publishedSafety!==null&&<details><summary>Published safety observations</summary><pre style={{whiteSpace:"pre-wrap",fontSize:12}}>{JSON.stringify(trial.publishedSafety,null,2)}</pre></details>}
  <details><summary>Evidence provenance and dates</summary><ul>{trial.sources.map(s=><li key={s.url}>{sourceLink(s.url)&&<a href={s.url} target="_blank" rel="noopener noreferrer">{pretty(s.kind)}</a>} · {s.date||"Date unresolved"}<br/><small style={{overflowWrap:"anywhere"}}>Evidence record digest: {s.digest}</small></li>)}</ul></details>
 </article>;
}
export default function LevelSixAssessmentRunner({selectedNct}:{selectedNct?:string}){
 const [options,setOptions]=useState<Options|null>(null),[nct,setNct]=useState(selectedNct||""),[busy,setBusy]=useState(false),[loading,setLoading]=useState(true),[error,setError]=useState(""),[signIn,setSignIn]=useState(false),[run,setRun]=useState<AssessmentRun|null>(null);
 useEffect(()=>{const controller=new AbortController();
  void fetch(endpoint,{cache:"no-store",signal:controller.signal}).then(async response=>{
   if(response.status===401){setSignIn(true);throw Error("Sign in with your existing dashboard account to run assessments.");}
   const data=await response.json();if(!response.ok)throw Error(data.error||"Assessment evidence unavailable");
   setOptions(data);setNct(current=>data.trials.some((t:{nct:string})=>t.nct===current)?current:data.trials[0]?.nct||"");
  }).catch(cause=>{if(!controller.signal.aborted)setError(cause instanceof Error?cause.message:"Assessment evidence unavailable");}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
  return ()=>controller.abort();
 },[]);
 useEffect(()=>{if(selectedNct)setNct(selectedNct);},[selectedNct]);
 async function start(scope:"ONE"|"ALL"){
  if(busy)return;setBusy(true);setError("");setRun(null);
  try{
   const response=await fetch(endpoint,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(scope==="ONE"?{scope,nct}:{scope})});
   const data=await response.json();if(response.status===401)setSignIn(true);
   if(!response.ok)throw Error(data.error||"Assessment did not complete");setRun(data);
  }catch(cause){setError(cause instanceof Error?cause.message:"Assessment did not complete; try again.");}
  finally{setBusy(false);}
 }
 function download(){if(!run)return;const url=URL.createObjectURL(new Blob([JSON.stringify(run,null,2)],{type:"application/json"}));const a=document.createElement("a");a.href=url;a.download="levels1-6-"+run.runId+".json";a.click();URL.revokeObjectURL(url);}
 return <section aria-label="Run Levels 1–6 assessments" style={{padding:"clamp(14px,2vw,22px)",border:"2px solid #16856c",borderRadius:13,background:"#f4fcf8",margin:"16px 0 22px"}}>
  <h2 style={{margin:"0 0 8px"}}>Run Levels 1–6</h2>
  <p>Assess one FOCUS trial or all {options?.trials.length||32} trials using collected clinical evidence. Findings, reasons, contradictions and missing evidence stay separate for each level. No outside reviewer is required.</p>
  {options&&<p><strong>Evidence cutoff: {options.evidenceCutoffDate} UTC.</strong> This run uses saved sources; it does not retrieve newer documents or generate FDA approval probabilities.</p>}
  {loading&&<p role="status">Loading trial choices…</p>}
  {error&&<p role="alert" style={{color:"#95371d"}}>{error}</p>}
  {signIn&&<p><a href="/">Sign in to the dashboard</a>, then return to ASSESSMENTS.</p>}
  <label htmlFor="level16-trial">FOCUS trial</label>{" "}
  <select id="level16-trial" value={nct} disabled={busy||!options} onChange={e=>setNct(e.target.value)} style={{maxWidth:"100%",padding:9,margin:"8px 8px 8px 0"}}>
   {options?.trials.map(t=><option key={t.nct} value={t.nct}>{t.ticker} · {t.nct} · {t.indication}</option>)}
  </select>
  <div style={{display:"flex",flexWrap:"wrap",gap:10,margin:"8px 0"}}>
   <button type="button" style={button} disabled={busy||!options||!nct} onClick={()=>void start("ONE")}>Run selected trial · Levels 1–6</button>
   <button type="button" style={{...button,background:"white",color:"#086b55"}} disabled={busy||!options} onClick={()=>void start("ALL")}>Run all 32 FOCUS trials · Levels 1–6</button>
  </div>
  {busy&&<p role="status" aria-live="polite">Processing evidence across all six levels…</p>}
  {run&&<div aria-live="polite"><p><strong>{run.summary.trialsProcessed} trial(s) · {run.summary.levelsProcessed} levels processed.</strong> {run.summary.levelsWithEvidenceGaps} level(s) have evidence gaps; {run.summary.levelsWithConflicts} have conflicts to reconcile.</p>
   <p>Run {run.runId} · {run.completedAt} · OWNER NOT REVIEWED</p>
   <p>Results are available for this page session and are not saved to the database. Download the report to retain this run.</p>
   <button type="button" style={{...button,background:"white",color:"#086b55"}} onClick={download}>Download assessment run</button>
   {run.trials.map(t=><TrialAssessment key={t.nct} trial={t}/>)}</div>}
 </section>;
}
