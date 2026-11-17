'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {readSavedFocus} from '../lib/focus-saved-records';

type Report={runId:string;executedAt:string;score?:{value:number|null;kind:string};fdaPrediction?:{outcome:string;probability?:number|null;confidence:string}};
type Slot={state:string;report:Report|null;missingEvidence?:unknown[];error?:string|null};
type Trial={nct:string;ticker:string;company:string;levels:Record<string,Slot>};
type Summary={total:number|null;trials:Trial[];source?:{retrieved_at:string}|null};

const levels=[1,2,3,4,5,6] as const;
export default function SixIndependentFocusSurveys(){
 const [selected,setSelected]=useState<number>(1);
 const [data,setData]=useState<Summary|null>(null);
 const [error,setError]=useState('');
 const [batchStatus,setBatchStatus]=useState('');
 const [batchPending,setBatchPending]=useState(false);
 const [filter,setFilter]=useState('');
 const [trendNct,setTrendNct]=useState('');
 const [history,setHistory]=useState<Report[]>([]);
 const [historyError,setHistoryError]=useState('');
 useEffect(()=>{if(!trendNct){setHistory([]);setHistoryError('');return;}const controller=new AbortController();setHistory([]);setHistoryError('');fetch('/api/assessments/runtime?'+new URLSearchParams({nct:trendNct,level:String(selected)}),{cache:'no-store',signal:controller.signal}).then(async r=>{const body=await r.json();if(!r.ok)throw Error(body.error||'History unavailable');return body;}).then(body=>{if(!controller.signal.aborted)setHistory((Array.isArray(body.runs)?body.runs:[]).filter((r:Report&{nct?:string;level?:number})=>r.nct===trendNct&&r.level===selected).sort((a:Report,b:Report)=>a.executedAt.localeCompare(b.executedAt)));}).catch(e=>{if(!controller.signal.aborted)setHistoryError(e instanceof Error?e.message:'History unavailable');});return()=>controller.abort();},[trendNct,selected]);
 async function refresh(){
  const base=await readSavedFocus() as Summary;
  const response=await fetch('/api/assessments/runtime?focusLevels456=true',{cache:'no-store'});
  if(!response.ok)throw Error('L4–L6 saved results unavailable ('+response.status+')');
  const extra=await response.json() as Summary;
  const byNct=new Map(extra.trials.map(t=>[t.nct,t]));
  setData({...base,trials:base.trials.map(t=>({...t,levels:{...t.levels,...(byNct.get(t.nct)?.levels||{})}}))});
 }
 useEffect(()=>{let active=true;Promise.all([readSavedFocus() as Promise<Summary>,fetch('/api/assessments/runtime?focusLevels456=true',{cache:'no-store'}).then(async r=>{if(!r.ok)throw Error('L4–L6 saved results unavailable');return r.json() as Promise<Summary>;})]).then(([base,extra])=>{if(!active)return;const byNct=new Map(extra.trials.map(t=>[t.nct,t]));setData({...base,trials:base.trials.map(t=>({...t,levels:{...t.levels,...(byNct.get(t.nct)?.levels||{})}}))});}).catch(e=>{if(active)setError(e instanceof Error?e.message:'Survey data unavailable');});return()=>{active=false;};},[]);
 async function run456(){
  if(batchPending)return;
  setBatchPending(true);
  setBatchStatus('Submitting bounded L4–L6 evidence batch…');
  try{const r=await fetch('/api/assessments/runtime',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'FOCUS_LEVELS456_BATCH'})});const body=await r.json();if(!r.ok)throw Error(body.error||'Batch rejected');setBatchStatus('Up to six L4–L6 trial-level assessments queued. Refresh after execution; repeat to continue the 96 slots. No FDA probabilities are implied.');}
  catch(e){setBatchStatus(e instanceof Error?e.message:'Batch unavailable');}
  finally{setBatchPending(false);}
 }
 const trials=data?.trials||[];
 const rows=trials.filter(t=>(t.nct+' '+t.ticker+' '+t.company).toLowerCase().includes(filter.toLowerCase()));
 const completed=trials.filter(t=>!!t.levels[String(selected)]?.report).length;
 return <section aria-label="Six independent FOCUS surveys" style={{padding:16,border:'2px solid #7baf99',borderRadius:10,margin:'16px 0'}}>
  <h2>FOCUS · Six independent surveys (L1–L6)</h2>
  <p>Each level has its own trial results and evidence status. Missing or unvalidated results are never filled with invented scores or predictions.</p>
  <nav aria-label="Select independent survey" style={{display:'flex',gap:8,flexWrap:'wrap'}}>
   {levels.map(l=><button type="button" key={l} aria-pressed={selected===l} onClick={()=>{setSelected(l);setTrendNct('');}} style={{padding:'9px 14px',borderRadius:7,border:'1px solid #7baf99',background:selected===l?'#d8efe5':'transparent',fontWeight:selected===l?700:400}}>Survey L{l}</button>)}
  </nav>
  <h3>Survey L{selected} · FOCUS trials</h3>
  {selected>=4&&<button type="button" onClick={run456} disabled={batchPending}>Run next 6 L4–L6 evidence surveys</button>} <button type="button" onClick={()=>{setError('');refresh().catch(e=>setError(e instanceof Error?e.message:'Refresh failed'));}}>Refresh saved results</button>
  {batchStatus&&<p role="status">{batchStatus}</p>}
  {error&&<p role="alert">{error}</p>}
  {!data&&!error&&<p role="status">Loading saved FOCUS records…</p>}
  {data&&<><p role="status">Saved executions: {completed} / {data.total??'roster not reconciled'} · Level {selected} only. {data.source?.retrieved_at?'Source retrieved '+data.source.retrieved_at:''}</p>
   <label>Filter trials <input value={filter} onChange={e=>setFilter(e.target.value)}/></label>
   <div style={{overflowX:'auto'}}><table style={{width:'100%',minWidth:750}}><thead><tr><th>Trial</th><th>L{selected} survey status</th><th>L{selected} evidence coverage / score</th><th>L{selected} FDA prediction</th><th>L{selected} confidence</th><th>Trend over time</th></tr></thead><tbody>
   {rows.map(t=>{const slot=t.levels[String(selected)];const report=slot?.report;const score=report?.score;const validScore=score&&score.value!==null&&score.kind!=='NOT_VALIDATED';return <tr key={t.nct}><td><Link href={'/predictions/assessment?nct='+encodeURIComponent(t.nct)}>{t.nct}</Link><br/>{t.ticker} · {t.company}</td><td>{report?'Saved · '+report.executedAt:slot?.state||'NOT RUN'}{slot?.missingEvidence?.length?' · '+slot.missingEvidence.length+' unresolved criteria':''}</td><td>{validScore?(score.kind==='LEVEL_SPECIFIC_EVIDENCE_COVERAGE'?score.value+'% evidence coverage':score.value):'NOT VALIDATED'}</td><td>{report?.fdaPrediction?.outcome||'ABSTAIN'}</td><td>{report?.fdaPrediction?.probability==null?'NOT VALIDATED':report.fdaPrediction.probability+'%'}</td><td><button type="button" onClick={()=>setTrendNct(t.nct)}>View L{selected} history</button></td></tr>;})}
   </tbody></table></div>
  </>}
  {trendNct&&<div aria-label="Selected trial score history" style={{padding:12,marginTop:12,border:'1px solid #7baf99',borderRadius:8}}>
   <h3>{trendNct} · Survey L{selected} historical scores</h3>
   <button type="button" onClick={()=>setTrendNct('')}>Close history</button>
   {historyError&&<p role="alert">{historyError}</p>}
   {!historyError&&(()=>{const points=history.filter(r=>r.score?.value!=null&&Number.isFinite(r.score.value)&&r.score.kind!=='NOT_VALIDATED'&&Number.isFinite(Date.parse(r.executedAt)));if(points.length<2)return <p>Insufficient validated historical observations ({points.length} available; at least two required).</p>;const values=points.map(r=>r.score!.value as number);const min=Math.min(...values),max=Math.max(...values),range=max-min||1;return <><svg viewBox="0 0 600 180" role="img" aria-label={`Historical score trend for ${trendNct} at Level ${selected}`} style={{width:'100%',maxWidth:700,height:180}}><polyline fill="none" stroke="#23785c" strokeWidth="3" points={values.map((v,i)=>`${20+i*560/(values.length-1)},${160-(v-min)*140/range}`).join(' ')}/>{values.map((v,i)=><circle key={i} cx={20+i*560/(values.length-1)} cy={160-(v-min)*140/range} r="4" fill="#23785c"/> )}</svg><p>{points.length} saved observations · {points[0].executedAt} to {points[points.length-1].executedAt}</p></>;})()}
  </div>}
  <p><small>Historical trends require at least two independently saved, timestamped scores for the same trial and level. Historical observations are fetched separately from the saved per-trial, per-level history endpoint. Levels 4–6 remain explicitly pending where no executable survey report exists.</small></p>
 </section>;
}
