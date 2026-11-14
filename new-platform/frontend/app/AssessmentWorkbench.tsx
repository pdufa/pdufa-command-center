'use client';
import {useEffect,useRef,useState} from 'react';
type Check={id:string;state:string;explanation:string;locator:string};
type Report={runId:string;nct:string;level:number;name:string;mode:string;cutoffDate:string|null;executedAt:string;engineVersion:string;reportHash:string;scientificStatus:string;activationStatus:string;ownerReviewStatus:string;score:{value:number|null;available:number;applicable:number;kind:string;method:string};fdaPrediction:{outcome:string;confidence:string;calibration:string};context:{phases:string[];phaseVerification:string;registryStatus:string|null;regulatoryStatus:string;conditions:string[];indicationAnalysis:{domain:string;question:string}[]};checks:Check[];observations:unknown[];risks:string[];recommendations:string[];limitations:string[];evidence:{source_url:string;captured_at:string;published_at:string;input_sha256:string;raw_sha256:string;snapshot_id:string}};
type Choice={nct:string;ticker:string;title:string;population:string};
const endpoint='/api/assessments/runtime';
const names=['Source identity and provenance','Registry and phase verification','Clinical results evidence','Trial design and protocol investigation','Statistical analysis and multiplicity','Endpoint clinical relevance'];
const human=(v:string)=>v.replaceAll('_',' ');
function Result({report:r}:{report:Report}){
 return <article style={{border:'1px solid #abc9bd',padding:16,borderRadius:10,minWidth:280,flex:'1 1 380px'}} aria-label={`Level ${r.level} saved assessment`}>
  <h3>Level {r.level}: {r.name}</h3><p>{r.nct} · {r.executedAt} · {r.mode}{r.cutoffDate?' · Cutoff '+r.cutoffDate:''}</p>
  <p><strong>Evidence coverage: {r.score.value===null?'Not applicable':r.score.value+'%'}</strong> ({r.score.available}/{r.score.applicable} applicable checks). {r.score.method}</p>
  <p>FDA prediction: <strong>{r.fdaPrediction.outcome}</strong> · {r.fdaPrediction.confidence}. {r.fdaPrediction.calibration}</p>
  <p>Phase: {r.context.phases.join(', ')||'Unresolved'} ({r.context.phaseVerification}); trial status: {r.context.registryStatus||'Unresolved'}. Regulatory status: {r.context.regulatoryStatus}.</p>
  <p>Scientific status: {human(r.scientificStatus)}. {human(r.activationStatus)}. {human(r.ownerReviewStatus)}.</p>
  <ul>{r.checks.map(c=><li key={c.id}><strong>{human(c.id)}: {human(c.state)}</strong> — {c.explanation}<br/><small>{c.locator}</small></li>)}</ul>
  <h4>Indication-specific review</h4>{r.context.indicationAnalysis.map(i=><p key={i.domain}><strong>{i.domain}:</strong> {i.question}</p>)}
  <h4>Risks and missing evidence</h4><ul>{r.risks.map((v,i)=><li key={i}>{v}</li>)}</ul>
  <h4>Recommendations</h4><ul>{r.recommendations.map((v,i)=><li key={i}>{v}</li>)}</ul>
  <details><summary>Clinical observations and reported statistics</summary><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere',maxHeight:500,overflow:'auto'}}>{JSON.stringify(r.observations,null,2)}</pre></details>
  <details><summary>Limitations and source provenance</summary><ul>{r.limitations.map((v,i)=><li key={i}>{v}</li>)}</ul><p><a href={r.evidence.source_url} target="_blank" rel="noopener noreferrer">Original registry source</a> · Published revision {r.evidence.published_at} · Captured {r.evidence.captured_at}</p><p style={{overflowWrap:'anywhere'}}>Engine {r.engineVersion}<br/>Run {r.runId}<br/>Snapshot {r.evidence.snapshot_id}<br/>Input SHA-256 {r.evidence.input_sha256}<br/>Original response SHA-256 {r.evidence.raw_sha256}<br/>Saved report hash {r.reportHash}</p></details>
 </article>;
}
export default function AssessmentWorkbench({selectedNct}:{selectedNct?:string}){
 const [nct,setNct]=useState(selectedNct||''),[level,setLevel]=useState(1),[mode,setMode]=useState('CURRENT_EVIDENCE'),[cutoff,setCutoff]=useState(''),[population,setPopulation]=useState('FOCUS'),[query,setQuery]=useState(''),[choices,setChoices]=useState<Choice[]>([]),[runs,setRuns]=useState<Report[]>([]),[selected,setSelected]=useState<string[]>([]),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState('');
 const controller=useRef<AbortController|null>(null);
 useEffect(()=>()=>controller.current?.abort(),[]);
 async function read(url:string,init?:RequestInit){const response=await fetch(url,{cache:'no-store',...init});const data=await response.json();if(!response.ok)throw Error(data.error||'Assessment request failed');return data;}
 async function search(){setError('');setBusy(true);try{const data=await read(endpoint+'?'+new URLSearchParams({population,q:query}));setChoices(data.trials);setMessage(data.trials.length?'Choose an exact trial below.':'No records matched this source inventory. Exact NCT entry remains available.');}catch(e){setError(e instanceof Error?e.message:'Trial search failed');}finally{setBusy(false);}}
 async function history(){setError('');setBusy(true);try{const data=await read(endpoint+'?nct='+nct);setRuns(data.runs);setSelected(data.runs.slice(0,2).map((r:Report)=>r.runId));setMessage(data.runs.length?`${data.runs.length} persisted assessment version(s) loaded${data.hasMore?' (more older versions exist)':''}.`:'No saved assessments for this exact NCT.');}catch(e){setError(e instanceof Error?e.message:'History unavailable');}finally{setBusy(false);}}
 async function run(){
  if(busy)return;setBusy(true);setError('');setMessage('Submitting the selected level…');controller.current=new AbortController();const signal=controller.current.signal;
  try{
   const created=await read(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nct,level,mode,...(mode==='BLIND_HISTORICAL'?{cutoffDate:cutoff}:{})}),signal});
   const until=Date.now()+180000;
   while(Date.now()<until){
    const state=await read(endpoint+'?'+new URLSearchParams({nct,runId:created.runId}),{signal});
    setMessage(state.progress.map((p:{stage:string;at:string})=>human(p.stage)+' · '+p.at).join(' → '));
    if(state.status==='FAILED')throw Error(state.error||'Assessment failed; no completed result saved');
    if(state.status==='COMPLETED'&&state.report){const report=state.report as Report;setRuns(current=>[report,...current.filter(r=>r.nct===nct&&r.runId!==report.runId)]);setSelected(current=>[report.runId,...current.filter(id=>id!==report.runId)].slice(0,2));setMessage('Completed: immutable result saved and retrieved from the backend.');return;}
    await new Promise<void>((resolve,reject)=>{const abort=()=>{clearTimeout(timer);reject(Error('Assessment display closed'));};const timer=setTimeout(()=>{signal.removeEventListener('abort',abort);resolve();},1200);signal.addEventListener('abort',abort,{once:true});});
   }
   throw Error('Execution has not confirmed completion. Load saved history before retrying.');
  }catch(e){if(!signal.aborted)setError(e instanceof Error?e.message:'Assessment failed');}finally{if(!signal.aborted)setBusy(false);}
 }
 const valid=/^NCT\d{8}$/.test(nct);
 return <section aria-label="Assessment workbench" style={{padding:20,border:'2px solid #16856c',borderRadius:12,margin:'16px 0'}}>
  <h2>Run an individual trial assessment</h2>
  <p>Each level executes its own evidence engine. Coverage scores measure the available applicable evidence checks; they do not rate efficacy or predict FDA approval. Scientific gaps and unvalidated forecasts remain explicit.</p>
  <fieldset disabled={busy}><legend>Trial selection</legend><label>Trial population <select aria-label="Trial population" value={population} onChange={e=>setPopulation(e.target.value)}>{['POOL','FOCUS','HISTORICAL'].map(p=><option key={p}>{p}</option>)}</select></label>{' '}<label>Search NCT, company or ticker <input value={query} onChange={e=>setQuery(e.target.value)}/></label>{' '}<button type="button" onClick={()=>void search()}>Search trials</button>
   {choices.length>0&&<p><label>Matching exact trials <select aria-label="Matching exact trials" value="" onChange={e=>{setNct(e.target.value);setRuns([]);setSelected([]);}}><option value="">Choose a trial</option>{choices.map(c=><option key={c.nct} value={c.nct}>{c.nct} · {c.ticker} · {c.title}</option>)}</select></label></p>}
   <p><label>Exact NCT identifier <input value={nct} placeholder="NCT04576949" onChange={e=>{setNct(e.target.value.trim().toUpperCase());setRuns([]);setSelected([]);}}/></label></p>
  </fieldset>
  <fieldset disabled={busy}><legend>Assessment execution</legend><label>Assessment level <select aria-label="Assessment level" value={level} onChange={e=>setLevel(Number(e.target.value))}>{names.map((name,i)=><option key={i} value={i+1}>Level {i+1} — {name}</option>)}</select></label>{' '}<label>Evidence mode <select aria-label="Evidence mode" value={mode} onChange={e=>setMode(e.target.value)}><option value="CURRENT_EVIDENCE">Current Evidence</option><option value="BLIND_HISTORICAL">Blind Historical</option></select></label>
   {mode==='BLIND_HISTORICAL'&&<p><label>Historical evidence cutoff <input type="date" value={cutoff} onChange={e=>setCutoff(e.target.value)}/></label><br/>Only original snapshots captured and published by the cutoff can execute. Missing historical evidence causes a visible failure; no current-source fallback or outcome cache is used. Human outcome exposure is not certified.</p>}
   <p><button type="button" disabled={!valid||(mode==='BLIND_HISTORICAL'&&!cutoff)} onClick={()=>void run()}>Run Assessment</button>{' '}<button type="button" disabled={!valid} onClick={()=>void history()}>Load saved assessment history</button></p>
  </fieldset>
  {message&&<p role="status" aria-live="polite">{message}</p>}{error&&<p role="alert">{error}</p>}
  {runs.length>0&&<div><h3>Compare saved levels and versions</h3><p>Select up to two persisted results to compare side by side. Outcomes remain separate from assessment inputs.</p><ul>{runs.map(r=><li key={r.runId}><label><input type="checkbox" checked={selected.includes(r.runId)} disabled={!selected.includes(r.runId)&&selected.length>=2} onChange={e=>setSelected(current=>e.target.checked?[...current,r.runId]:current.filter(id=>id!==r.runId))}/> Level {r.level} · {r.executedAt} · {r.mode} · {r.engineVersion}</label></li>)}</ul><div style={{display:'flex',flexWrap:'wrap',gap:14}}>{runs.filter(r=>selected.includes(r.runId)).map(r=><Result key={r.runId} report={r}/>)}</div></div>}
 </section>;
}
