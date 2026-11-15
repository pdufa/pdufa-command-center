'use client';
import Link from 'next/link';
import {readSavedFocus} from '../lib/focus-saved-records';
import {useEffect,useState} from 'react';
type Saved={runId:string;nct:string;level:number;executedAt:string;engineVersion:string;executionStatus:string;score:{value:number|null;kind:string;method:string};fdaPrediction:{outcome:string;probability?:number|null;confidence:string};trialIdentity:{company:string;candidate:string;indication:string[]};context:{phases:string[]}};
type Slot={state:string;attempts:number;error:string|null;report:Saved|null;missingEvidence:{id:string;state:string;explanation:string}[]};
type Trial={nct:string;company:string;ticker:string;pdufaDate:string|null;levels:Record<string,Slot>};
type Summary={status:string;total:number|null;fullyProcessed?:number;batchId?:string;counts:Record<string,{processed:number;scored:number;incomplete:number;failed:number}>;trials:Trial[];source:{source_url:string;retrieved_at:string;authority_status:string}|null};
const endpoint='/api/assessments/runtime';
export default function FocusSavedAssessments(){
 const [data,setData]=useState<Summary|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[filter,setFilter]=useState(''),[level,setLevel]=useState('ALL'),[message,setMessage]=useState('');
 async function load(signal?:AbortSignal){const body=await readSavedFocus() as Summary;if(!signal?.aborted)setData(body);return body;}
 useEffect(()=>{const controller=new AbortController();const refresh=()=>{void load(controller.signal).catch(e=>{if(!controller.signal.aborted)setError(String(e.message));});};refresh();if(typeof window!=='undefined')window.addEventListener('pdufa:assessment-saved',refresh);return()=>{controller.abort();if(typeof window!=='undefined')window.removeEventListener('pdufa:assessment-saved',refresh);};},[]);
 async function batch(){setBusy(true);setError('');try{const response=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'FOCUS_BATCH'})});const body=await response.json();if(!response.ok)throw Error(body.error||'Batch rejected');setMessage('Bounded batch queued; completion is not confirmed.');await load();}catch(e){setError(e instanceof Error?e.message:'Batch failed');}finally{setBusy(false);}}
 const rows=(data?.trials||[]).filter(t=>(t.nct+' '+t.ticker+' '+t.company).toLowerCase().includes(filter.toLowerCase()));
 return <section aria-label="Saved FOCUS Level 1–3 assessments" style={{border:'1px solid #b9cebe',borderRadius:8,padding:14,margin:'16px 0',overflowWrap:'anywhere',minWidth:0}}>
  <h2>Saved FOCUS assessments · Levels 1–3</h2>
  <p>Both FOCUS and ASSESSMENTS read these same versioned database records. An executed assessment with evidence gaps is not a validated numerical score. Predictions without a validated model remain ABSTAIN.</p>
  {error&&<p role="alert">{error}</p>}{message&&<p role="status">{message}</p>}
  {!data&&!error&&<p role="status">Loading persisted assessments…</p>}
  {data&&<><p>Database roster: {data.total===null?'NOT RECONCILED':data.total+' exact trials'}. All three research executions saved: {data.fullyProcessed??0}. Roster status: {data.status.replaceAll('_',' ')}.</p>
   {data.source&&<p><a href={data.source.source_url} target="_blank" rel="noopener noreferrer">Owner roster source</a> · Retrieved {data.source.retrieved_at} · {data.source.authority_status.replaceAll('_',' ')}. PDUFA dates are owner-source reports until exact application linkage is verified.</p>}
   <ul>{[1,2,3].map(l=><li key={l}>Level {l}: {data.counts[String(l)]?.processed??0} executions saved; {data.counts[String(l)]?.scored??0} validated numerical scores; {data.counts[String(l)]?.incomplete??0} incomplete/unscorable; {data.counts[String(l)]?.failed??0} execution failures.</li>)}</ul>
   <label>Filter saved FOCUS trials <input value={filter} onChange={e=>setFilter(e.target.value)}/></label>{' '}
   <label>Saved assessment level <select value={level} onChange={e=>setLevel(e.target.value)}><option value="ALL">All three levels side by side</option>{[1,2,3].map(l=><option key={l} value={l}>Level {l}</option>)}<option disabled>Future levels — unavailable</option></select></label>{' '}
   <button type="button" disabled={busy} onClick={()=>{setError('');void load().then(()=>setMessage('Refreshed saved database results.')).catch(e=>setError(e.message));}}>Refresh saved results</button>{' '}
   <button type="button" disabled={busy||data.total===null} onClick={()=>void batch()}>Process next bounded batch</button>
   <div style={{overflowX:'auto',marginTop:12}}><table style={{borderCollapse:'collapse',minWidth:850,width:'100%'}}><thead><tr><th>Trial</th>{[1,2,3].filter(l=>level==='ALL'||level===String(l)).flatMap(l=>[<th key={l+'s'}>L{l} Score</th>,<th key={l+'p'}>L{l} Prediction</th>])}</tr></thead>
    <tbody>{rows.map(t=><tr key={t.nct} style={{borderTop:'1px solid #b9cebe'}}><td style={{padding:10}}><Link href={'/predictions/assessment?nct='+t.nct}>{t.nct}</Link><br/>{t.ticker} · {t.company}<br/>{t.levels['1']?.report?.trialIdentity.candidate||'Candidate not yet source-verified'}<br/>PDUFA: {t.pdufaDate||'Not assigned/verified'}<br/><Link href={'/company?ticker='+encodeURIComponent(t.ticker)}>COMPANY</Link> · <Link href="/focus">FOCUS</Link></td>
     {[1,2,3].filter(l=>level==='ALL'||level===String(l)).flatMap(l=>{const slot=t.levels[String(l)],r=slot?.report;return [<td key={l+'s'} style={{padding:10,verticalAlign:'top'}}>{r?<><Link href={'/predictions/assessment?nct='+t.nct}>{r.score.value===null?'NOT VALIDATED / UNSCORABLE':r.score.value}</Link><br/>{r.executionStatus}<br/>{r.context.phases.join(', ')}<br/>{r.executedAt}<br/><small>{r.engineVersion}</small><details><summary>{slot.missingEvidence.length} unresolved criteria · evidence details</summary><p>{r.score.method}</p><ul>{slot.missingEvidence.map(c=><li key={c.id}>{c.id} · {c.state}: {c.explanation}</li>)}</ul><Link href={'/predictions/assessment?nct='+t.nct}>Open source-linked findings and version history</Link></details></>:<><strong>{slot?.state||'NOT RUN'}</strong><br/>{slot?.error||'No completed assessment saved'}</>}</td>,<td key={l+'p'} style={{padding:10,verticalAlign:'top'}}>{r?<>{r.fdaPrediction.outcome}<br/>Confidence: {r.fdaPrediction.probability===null||r.fdaPrediction.probability===undefined?'NOT VALIDATED':r.fdaPrediction.probability+'%'}<br/>{r.fdaPrediction.confidence}</>:'ABSTAIN — no completed result'}</td>];})}
    </tr>)}</tbody></table></div>
  </>}
 </section>;
}
