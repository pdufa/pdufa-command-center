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
 const [filter,setFilter]=useState('');
 const [trendNct,setTrendNct]=useState('');
 const [history,setHistory]=useState<Report[]>([]);
 const [historyError,setHistoryError]=useState('');
 useEffect(()=>{if(!trendNct){setHistory([]);setHistoryError('');return;}const controller=new AbortController();setHistory([]);setHistoryError('');fetch('/api/assessments/runtime?'+new URLSearchParams({nct:trendNct,level:String(selected)}),{cache:'no-store',signal:controller.signal}).then(async r=>{const body=await r.json();if(!r.ok)throw Error(body.error||'History unavailable');return body;}).then(body=>{if(!controller.signal.aborted)setHistory((Array.isArray(body.runs)?body.runs:[]).filter((r:Report&{nct?:string;level?:number})=>r.nct===trendNct&&r.level===selected).sort((a:Report,b:Report)=>a.executedAt.localeCompare(b.executedAt)));}).catch(e=>{if(!controller.signal.aborted)setHistoryError(e instanceof Error?e.message:'History unavailable');});return()=>controller.abort();},[trendNct,selected]);
 useEffect(()=>{let active=true;readSavedFocus().then(value=>{if(active)setData(value as Summary);}).catch(e=>{if(active)setError(e instanceof Error?e.message:'Survey data unavailable');});return()=>{active=false;};},[]);
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
  {error&&<p role="alert">{error}</p>}
  {!data&&!error&&<p role="status">Loading saved FOCUS records…</p>}
  {data&&<><p role="status">Saved executions: {completed} / {data.total??'roster not reconciled'} · Level {selected} only. {data.source?.retrieved_at?'Source retrieved '+data.source.retrieved_at:''}</p>
   <label>Filter trials <input value={filter} onChange={e=>setFilter(e.target.value)}/></label>
   <div style={{overflowX:'auto'}}><table style={{width:'100%',minWidth:750}}><thead><tr><th>Trial</th><th>L{selected} survey status</th><th>L{selected} score</th><th>L{selected} FDA prediction</th><th>L{selected} confidence</th><th>Trend over time</th></tr></thead><tbody>
   {rows.map(t=>{const slot=t.levels[String(selected)];const report=slot?.report;const score=report?.score;const validScore=score&&score.value!==null&&score.kind!=='NOT_VALIDATED';return <tr key={t.nct}><td><Link href={'/predictions/assessment?nct='+encodeURIComponent(t.nct)}>{t.nct}</Link><br/>{t.ticker} · {t.company}</td><td>{report?'Saved · '+report.executedAt:slot?.state||'NOT RUN'}{slot?.missingEvidence?.length?' · '+slot.missingEvidence.length+' unresolved criteria':''}</td><td>{validScore?score.value:'NOT VALIDATED'}</td><td>{report?.fdaPrediction?.outcome||'ABSTAIN'}</td><td>{report?.fdaPrediction?.probability==null?'NOT VALIDATED':report.fdaPrediction.probability+'%'}</td><td><button type="button" onClick={()=>setTrendNct(t.nct)}>View L{selected} history</button></td></tr>;})}
   </tbody></table></div>
  </>}
  <p><small>Historical trends require at least two independently saved, timestamped scores for the same trial and level. Historical observations are fetched separately from the saved per-trial, per-level history endpoint. Levels 4–6 remain explicitly pending where no executable survey report exists.</small></p>
 </section>;
}
