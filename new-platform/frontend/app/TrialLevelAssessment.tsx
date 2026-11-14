'use client';
import {useState} from 'react';
import type {SavedTrialAssessment} from '../lib/trial-level-assessment';
const endpoint='/api/assessments/trial';
export default function TrialLevelAssessment({selectedNct}:{selectedNct?:string}){
 const [nct,setNct]=useState(selectedNct||''),[level,setLevel]=useState(1),[mode,setMode]=useState('CURRENT_EVIDENCE'),[cutoff,setCutoff]=useState(''),[busy,setBusy]=useState(''),[error,setError]=useState(''),[runs,setRuns]=useState<SavedTrialAssessment[]>([]);
 async function perform(execute:boolean){
  if(busy)return;setBusy(execute?'Retrieving exact-NCT evidence, processing selected level and saving result…':'Loading saved assessment versions…');setError('');
  try{
   const response=await fetch(execute?endpoint:endpoint+'?nct='+encodeURIComponent(nct)+'&level='+level,{cache:'no-store',...(execute?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nct,level,mode,...(mode==='BLIND_HISTORICAL'?{cutoffDate:cutoff}:{})})}:{})});
   const data=await response.json();if(!response.ok)throw Error(data.error||'Assessment request failed');
   setRuns(execute?[data]:data.runs);
  }catch(e){setError(e instanceof Error?e.message:'Assessment unavailable');}finally{setBusy('');}
 }
 return <section aria-label="Persistent individual trial assessments" style={{padding:20,border:'2px solid #16856c',borderRadius:12,margin:'16px 0'}}>
  <h2>Individual trial assessment and saved history</h2>
  <p>Enter an exact NCT from POOL, FOCUS or historical records. Current Evidence retrieves the latest registry version; it does not establish a verified FDA filing status. All six engines are partial research checks. Numerical scores and calibrated FDA models are unavailable.</p>
  <label>Exact NCT identifier <input value={nct} placeholder="NCT04576949" onChange={e=>{setNct(e.target.value.trim().toUpperCase());setRuns([]);}} disabled={!!busy}/></label>{' '}
  <label>Assessment level <select value={level} onChange={e=>{setLevel(Number(e.target.value));setRuns([]);}} disabled={!!busy}>{[1,2,3,4,5,6].map(l=><option key={l} value={l}>Level {l} — partial research engine</option>)}</select></label>{' '}
  <label>Mode <select value={mode} disabled={!!busy} onChange={e=>{setMode(e.target.value);setRuns([]);setError('');}}><option value="CURRENT_EVIDENCE">Current Evidence</option><option value="BLIND_HISTORICAL">Blind Historical — unavailable</option></select></label>
  {mode==='BLIND_HISTORICAL'&&<div><label>Historical cutoff <input type="date" disabled={!!busy} value={cutoff} onChange={e=>setCutoff(e.target.value)}/></label><p role="status">Unavailable: an immutable, outcome-isolated evidence provider is missing. Current sources cannot be backdated. Historical execution is disabled.</p></div>}
  <p><button type="button" disabled={!!busy||!/^NCT\d{8}$/.test(nct)||mode==='BLIND_HISTORICAL'} onClick={()=>void perform(true)}>Run Assessment</button>{' '}<button type="button" disabled={!!busy||!/^NCT\d{8}$/.test(nct)} onClick={()=>void perform(false)}>Load saved versions</button></p>
  {busy&&<p role="status" aria-live="polite">{busy}</p>}{error&&<p role="alert">{error}</p>}
  {runs.map(run=><article key={run.runId} style={{borderTop:'1px solid #bcd4c9',padding:'12px 0'}}>
   <h3>{run.nct} · Level {run.level} · {run.engineVersion}</h3>
   <p>{run.executedAt} · {run.savedToDatabase?'Saved to backend history':'Persistence unconfirmed'} · {run.status}</p>
   <p>Score: unavailable ({run.scoreStatus}). FDA prediction: <strong>{run.fdaPrediction.outcome}</strong> · {run.fdaPrediction.calibration}. Confidence is uncalibrated.</p>
   <p>Phase: {run.result.phases.join(', ')||'Unresolved'} · Registry status: {run.result.registryStatus||'Unresolved'} · FDA application: unmapped.</p>
   {run.result.levels.map(l=><div key={l.level}><p>{l.interpretation}</p><ul>{l.checks.map(c=><li key={c.id}><strong>{c.label}: {c.state}</strong> — {c.reason}</li>)}</ul><p>Risks and limitations: {l.limitations.join(' ')}</p><p>Recommended next steps: {l.questions.join(' ')}</p></div>)}
   <p><a href={run.evidence.url} target="_blank" rel="noopener noreferrer">Registry source</a> · Version {run.evidence.versionDate} · Retrieved {run.evidence.retrievedAt}</p>
   <details><summary>Evidence version and complete saved report</summary><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{JSON.stringify(run,null,2)}</pre></details>
  </article>)}
 </section>;
}
