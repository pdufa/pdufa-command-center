'use client';

import {useEffect,useRef,useState} from 'react';
import Link from 'next/link';
import ScientificTrialFindings from './ScientificTrialFindings';

type Cohort='FOCUS'|'PAST'|'POOL'|'ASSESSMENTS';
type Mode='CURRENT_EVIDENCE'|'BLIND_HISTORICAL';
type Check={id:string;state:string;explanation:string;locator:string;citations?:unknown[]};
type Report={
 contract:string;runId:string;nct:string;level:number;name:string;mode:Mode;
 cutoffDate:string|null;executedAt:string;engineVersion:string;reportHash:string;
 executionStatus:string;scientificStatus:string;ownerReviewStatus:string;
 score:{value:number|null;kind:string;method:string};
 fdaPrediction:{outcome:string;probability:number|null;confidence:string};
 checks:Check[];risks:string[];recommendations:string[];limitations:string[];
 evidence:{source_url:string;captured_at:string;published_at:string;input_sha256:string};
};
const endpoint='/api/assessments/runtime';
const labels:{[level:number]:string}={
 4:'Safety and benefit-risk',
 5:'Indication-specific clinical assessment',
 6:'FDA regulatory readiness'
};
const validNct=(value:string)=>/^NCT[0-9]{8}$/.test(value);
const human=(value:string)=>value.replaceAll('_',' ');
const validRun=(value:unknown)=>typeof value==='string'&&/^[a-f0-9-]{36}$/.test(value);
function is456(value:unknown,nct:string):value is Report{
 if(!value||typeof value!=='object')return false;
 const r=value as Partial<Report>;
 return r.contract==='SCIENTIFIC_1_6'&&r.nct===nct&&
  [4,5,6].includes(r.level as number)&&validRun(r.runId)&&
  !!r.score&&r.score.kind==='NOT_VALIDATED'&&r.score.value===null&&
  !!r.fdaPrediction&&r.fdaPrediction.outcome==='ABSTAIN'&&r.fdaPrediction.probability===null&&
  Array.isArray(r.checks)&&Array.isArray(r.risks)&&Array.isArray(r.recommendations)&&
  typeof r.reportHash==='string'&&/^[a-f0-9]{64}$/.test(r.reportHash);
}
async function read(url:string,init?:RequestInit):Promise<Record<string,unknown>>{
 const response=await fetch(url,{cache:'no-store',...init});
 const body=await response.json();
 if(!response.ok)throw Error(typeof body.error==='string'?body.error:'Isolated scientific 456 backend unavailable');
 return body as Record<string,unknown>;
}
function viewUrl(nct:string,runId?:string){
 const q=new URLSearchParams({nct,contract:'SCIENTIFIC_1_6'});
 if(runId)q.set('runId',runId);
 return endpoint+'?'+q;
}
function ReportDetail({report:r}:{report:Report}){
 return <article aria-label={'Saved scientific Level '+r.level+' assessment'} style={{border:'1px solid #a7c2b4',borderRadius:8,padding:12,marginTop:12,overflowWrap:'anywhere'}}>
  <h4 style={{margin:'0 0 6px'}}>L0{r.level} · {r.name}</h4>
  <p>{r.nct} · {human(r.mode)}{r.cutoffDate?' · cutoff '+r.cutoffDate:''} · {r.executedAt}</p>
  <p><strong>Scientific score: NOT VALIDATED / UNSCORABLE</strong> · FDA prediction: <strong>ABSTAIN</strong> · Confidence: NOT VALIDATED. No calibrated approval probability.</p>
  <p>Execution: {human(r.executionStatus)} · {human(r.scientificStatus)} · {human(r.ownerReviewStatus)}</p>
  <h5>Source-backed checks and evidence gaps</h5>
  <ul>{r.checks.map((check,i)=><li key={check.id+'-'+i}><strong>{human(check.id)}: {human(check.state)}</strong> — {check.explanation} <small>({check.locator})</small></li>)}</ul>
  <h5>Unresolved risks</h5><ul>{r.risks.length?r.risks.map((x,i)=><li key={i}>{x}</li>):<li>No risks listed in this report; this is not evidence of safety or FDA readiness.</li>}</ul>
  <h5>Recommendations</h5><ul>{r.recommendations.map((x,i)=><li key={i}>{x}</li>)}</ul>
  <details><summary>Detailed scientific observations, prerequisites and citations</summary><ScientificTrialFindings value={r}/></details>
  <details><summary>Saved version and source provenance</summary>
   <p>Run: {r.runId} · Engine: {r.engineVersion}</p><p>Saved report SHA-256: {r.reportHash}</p>
   <p>Input SHA-256: {r.evidence?.input_sha256||'Not supplied'} · captured: {r.evidence?.captured_at||'Unresolved'}</p>
   {r.evidence?.source_url?.startsWith('https://clinicaltrials.gov/')&&<a href={r.evidence.source_url} target="_blank" rel="noopener noreferrer">Exact trial original registry source</a>}
   <ul>{(r.limitations||[]).map((x,i)=><li key={i}>{x}</li>)}</ul>
  </details>
 </article>;
}

/** Owner-only research display: never falls back to the Level 123 backend. */
export default function Scientific456Workspace({cohort,initialNct}:{cohort:Cohort;initialNct?:string}){
 const [nct,setNct]=useState(initialNct&&validNct(initialNct)?initialNct:'');
 const [level,setLevel]=useState(4);
 const [mode,setMode]=useState<Mode>(cohort==='PAST'?'BLIND_HISTORICAL':'CURRENT_EVIDENCE');
 const [cutoff,setCutoff]=useState('');
 const [runs,setRuns]=useState<Report[]>([]);
 const [status,setStatus]=useState('');
 const [error,setError]=useState('');
 const [busy,setBusy]=useState(false);
 const [ready,setReady]=useState(false);
 const [expanded,setExpanded]=useState<string[]>([]);
 const [hasMore,setHasMore]=useState(false);
 const revision=useRef(0);
 const controller=useRef<AbortController|null>(null);
 function changeNct(value:string){
  revision.current++;
  controller.current?.abort();
  setBusy(false);
  setNct(value.trim().toUpperCase());
  setRuns([]);setExpanded([]);setStatus('');setError('');setHasMore(false);
 }
 useEffect(()=>{setReady(true);return()=>{revision.current++;controller.current?.abort();};},[]);
 useEffect(()=>{if(initialNct&&validNct(initialNct)&&initialNct!==nct)changeNct(initialNct);},[initialNct]);
 async function history(id=nct){
  if(!validNct(id))return;
  const current=revision.current;
  controller.current?.abort();
  const abort=new AbortController();controller.current=abort;
  setBusy(true);setError('');setStatus('Loading saved 456 versions…');
  try{
   const response=await read(viewUrl(id),{signal:abort.signal});
   if(abort.signal.aborted||current!==revision.current)return;
   if(!Array.isArray(response.runs))throw Error('Invalid saved assessment history response');
   // Never mix original 123, legacy 456, other NCTs or unsupported predictions.
   const reports=response.runs.filter((r:unknown)=>is456(r,id)) as Report[];
   setRuns(reports);setExpanded(reports.slice(0,1).map(r=>r.runId));setHasMore(response.hasMore===true);
   setStatus(reports.length?reports.length+' saved 456 research version(s) loaded.':'No validated-identity scientific 456 reports saved for this NCT.');
  }catch(e){if(!abort.signal.aborted&&current===revision.current)setError(e instanceof Error?e.message:'Saved history unavailable');}
  finally{if(!abort.signal.aborted&&current===revision.current)setBusy(false);}
 }
 useEffect(()=>{if(initialNct&&validNct(initialNct))void history(initialNct);},[initialNct]);
 async function run(){
  if(busy||!validNct(nct))return;
  const id=nct,chosenLevel=level,chosenMode=mode,chosenCutoff=cutoff,current=revision.current;
  const abort=new AbortController();controller.current=abort;
  setBusy(true);setError('');setStatus('Submitting isolated scientific L0'+level+'…');
  try{
   const created=await read(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},signal:abort.signal,
    body:JSON.stringify({nct:id,level:chosenLevel,mode:chosenMode,contract:'SCIENTIFIC_1_6',
     ...(chosenMode==='BLIND_HISTORICAL'?{cutoffDate:chosenCutoff}:{})})});
   if(!validRun(created.runId))throw Error('Run identifier missing; no saved completion confirmed');
   for(let attempt=0;attempt<90;attempt++){
    if(abort.signal.aborted||current!==revision.current)return;
    const state=await read(viewUrl(id,String(created.runId)),{signal:abort.signal});
    if(abort.signal.aborted||current!==revision.current)return;
    if(state.status==='FAILED')throw Error(typeof state.error==='string'?state.error:'456 research execution failed');
    if(state.status==='COMPLETED'){
     const report=state.report;
     if(!is456(report,id)||report.runId!==created.runId||report.level!==chosenLevel||report.mode!==chosenMode||
       (chosenMode==='BLIND_HISTORICAL'&&report.cutoffDate!==chosenCutoff))
      throw Error('Saved 456 report identity, contract, cutoff, or evidence status mismatch; withheld');
     setRuns(existing=>[report,...existing.filter(r=>r.runId!==report.runId)]);
     setExpanded(old=>[report.runId,...old.filter(x=>x!==report.runId)].slice(0,3));
     setStatus('L0'+chosenLevel+' completed and saved; prediction ABSTAIN, scientific score NOT VALIDATED.');
     return;
    }
    setStatus('L0'+chosenLevel+' '+human(String(state.status||'QUEUED'))+' · waiting for backend persistence');
    await new Promise<void>(resolve=>setTimeout(resolve,1600));
   }
   throw Error('Completion not confirmed; load history before requesting another run');
  }catch(e){if(!abort.signal.aborted&&current===revision.current)setError(e instanceof Error?e.message:'Isolated assessment unavailable');}
  finally{if(!abort.signal.aborted&&current===revision.current)setBusy(false);}
 }
 const valid=validNct(nct);
 const pastValid=mode==='CURRENT_EVIDENCE'||(/^\d{4}-\d{2}-\d{2}$/.test(cutoff)&&cutoff<new Date().toISOString().slice(0,10));
 return <section id="scientific456" aria-label={cohort+' scientific Levels 4–6 research'} aria-busy={busy||!ready} data-scientific456-ready={ready?"true":"false"} style={{border:'1px solid #9cbca9',padding:16,borderRadius:10,margin:'14px 0',color:'#173d2b'}}>
  <h3 style={{marginTop:0}}>Scientific L04–L06 · Saved research and execution</h3>
  <p>Separate, opt-in scientific reviews for safety/benefit-risk, indication-specific clinical evidence and FDA application readiness. No validated scientific score, FDA forecast or confidence percentage is implied. Original Levels 123 remain separate.</p>
  <p><strong>{cohort}</strong> · Exact NCT selection only. Each level saves a separate version; source gaps remain visible. There is no all-trials batch in this workspace.</p>
  <label>Exact NCT <input aria-label="456 exact NCT" value={nct} placeholder="NCT04576949" onChange={e=>changeNct(e.target.value)} style={{minWidth:170}}/></label>{' '}
  <label>Scientific level <select aria-label="456 scientific level" value={level} onChange={e=>setLevel(Number(e.target.value))}>
   {[4,5,6].map(i=><option value={i} key={i}>L0{i} · {labels[i]}</option>)}
  </select></label>{' '}
  <label>Evidence mode <select aria-label="456 evidence mode" value={mode} onChange={e=>setMode(e.target.value as Mode)}>
   <option value="CURRENT_EVIDENCE">Current evidence</option><option value="BLIND_HISTORICAL">Blind historical cutoff</option>
  </select></label>
  {mode==='BLIND_HISTORICAL'&&<p><label>Pre-decision cutoff <input aria-label="456 historical cutoff" type="date" value={cutoff} onChange={e=>setCutoff(e.target.value)}/></label> Only eligible original snapshots captured before the cutoff are allowed. No current-data fallback and no certification of the owner's outcome unawareness.</p>}
  <p><button type="button" disabled={!ready||!valid||!pastValid||busy} onClick={()=>void run()}>Run selected scientific level</button>{' '}
   <button type="button" disabled={!ready||!valid||busy} onClick={()=>void history()}>Load saved 456 history</button>{' '}
   {valid&&<Link href={'/assessments?nct='+encodeURIComponent(nct)+'#scientific456'}>Open this trial in ASSESSMENTS</Link>}
  </p>
  {status&&<p role="status">{status}</p>}{error&&<p role="alert">{error}</p>}
  {runs.length>0&&<div><h4>Saved 456 assessment versions · {nct}</h4>
   <p>Only exact-NCT SCIENTIFIC_1_6 reports with unvalidated scientific scores and an abstaining FDA prediction are displayed. Choose versions to expand.</p>
   {hasMore&&<p>History has additional older results beyond the bounded response; not all versions were returned.</p>}
   <ul>{runs.map(r=><li key={r.runId}><label><input type="checkbox" checked={expanded.includes(r.runId)} onChange={e=>setExpanded(old=>e.target.checked?[...old,r.runId]:old.filter(x=>x!==r.runId))}/> L0{r.level} · {r.mode} · {r.executedAt} · {r.engineVersion} · NOT VALIDATED · ABSTAIN</label></li>)}</ul>
   {runs.filter(r=>expanded.includes(r.runId)).map(r=><ReportDetail key={r.runId} report={r}/>)}
  </div>}
 </section>;
}
