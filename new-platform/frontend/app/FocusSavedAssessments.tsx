'use client';
import Link from 'next/link';
import FocusSurveyTrendChart from './FocusSurveyTrendChart';
import {FOCUS_CHART_SNAPSHOT_TRIALS,FOCUS_CHART_SNAPSHOT_DATE} from '../lib/focus-chart-snapshot';
import FocusOverallLevelMatrix from './FocusOverallLevelMatrix';
import {provisionalFocusScore,FOCUS_READINESS_METHOD} from '../lib/focus-provisional-scores';
import {readSavedFocus} from '../lib/focus-saved-records';
import {useEffect,useState} from 'react';
type Saved={runId:string;nct:string;level:number;mode:string;executedAt:string;engineVersion:string;executionStatus:string;score:{value:number|null;kind:string;method:string};fdaPrediction:{outcome:string;probability?:number|null;confidence:string};trialIdentity:{company:string;candidate:string;indication:string[]};context:{phases:string[]}};
type Slot={state:string;attempts:number;error:string|null;report:Saved|null;missingEvidence:{id:string;state:string;explanation:string}[];evidenceChecks?:{total:number;sourceVerified:number;unresolved:number}|null};
type Trial={nct:string;company:string;ticker:string;pdufaDate:string|null;levels:Record<string,Slot>};
type Summary={status:string;total:number|null;fullyProcessed?:number;batchId?:string;counts:Record<string,{processed:number;scored:number;incomplete:number;failed:number}>;trials:Trial[];source:{source_url:string;retrieved_at:string;authority_status:string}|null};
const endpoint='/api/assessments/runtime';
export default function FocusSavedAssessments({selectedNct}:{selectedNct?:string}={}){
 const [data,setData]=useState<Summary|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[filter,setFilter]=useState(selectedNct||''),[level,setLevel]=useState('ALL'),[message,setMessage]=useState('');
 async function load(signal?:AbortSignal){const body=await readSavedFocus() as Summary;if(!signal?.aborted){setData(body);setError('');}return body;}
 useEffect(()=>{setFilter(selectedNct||'');},[selectedNct]);
 useEffect(()=>{
  const controller=new AbortController();
  const refresh=()=>{void load(controller.signal).catch(e=>{if(!controller.signal.aborted)setError(e instanceof Error?e.message:'Saved results unavailable');});};
  refresh();
  const timer=setInterval(refresh,30000);
  window.addEventListener('focus',refresh);
  return()=>{controller.abort();clearInterval(timer);window.removeEventListener('focus',refresh);};
 },[]);
 async function batch(){setBusy(true);setError('');try{const response=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'FOCUS_BATCH'})});const body=await response.json();if(!response.ok)throw Error(body.error||'Batch rejected');setMessage('Bounded batch queued; completion is not confirmed.');await load();}catch(e){setError(e instanceof Error?e.message:'Batch failed');}finally{setBusy(false);}}
 const rows=(data?.trials||[]).filter(t=>(t.nct+' '+t.ticker+' '+t.company).toLowerCase().includes(filter.toLowerCase()));
 const provisionalScores=(data?.trials||[]).reduce((count,t)=>
  count+[1,2,3].filter(level=>!!provisionalFocusScore(t.nct,level,t.levels[String(level)]?.report)).length,0);
 // Never hide the chart while a protected API request is loading, unavailable
 // or signed out: render the fully reconciled source-checked dated snapshot
 // in the initial HTML. Upgrade to current data only with 32/32 exact NCTs
 // and all 96 identity-validated source-report scores.
 const sourceNcts=new Set(FOCUS_CHART_SNAPSHOT_TRIALS.map(t=>t.nct));
 const liveComplete=!!data&&data.total===FOCUS_CHART_SNAPSHOT_TRIALS.length&&
   data.total===32&&data.trials.length===32&&
   new Set(data.trials.map(t=>t.nct)).size===32&&
   data.trials.every(t=>sourceNcts.has(t.nct)&&[1,2,3].every(l=>
     !!provisionalFocusScore(t.nct,l,t.levels[String(l)]?.report)));
 const chartTrials=liveComplete?data!.trials:FOCUS_CHART_SNAPSHOT_TRIALS;
 const chartTotal=chartTrials.length;
 return <section aria-label="Saved FOCUS Level 1–3 assessments" style={{border:'1px solid #b9cebe',borderRadius:8,padding:14,margin:'16px 0',overflowWrap:'anywhere',minWidth:0}}>
  <h2>Saved FOCUS trial surveys · Levels 1–3</h2>
  <p>Both FOCUS and ASSESSMENTS read these same versioned database records. An executed assessment with evidence gaps is not a validated numerical score. Predictions without a validated model remain ABSTAIN.</p>
  <div id="focus-chart-quick-view" data-testid="focus-chart-immediate-panel"
    style={{margin:'12px 0 20px',padding:'10px 12px',border:'2px solid #7baf99',borderRadius:10}}>
   <h3 style={{margin:'0 0 5px'}}>FOCUS chart · Levels 1–3 + Overall + FDA direction</h3>
   <p role="status" style={{fontSize:13,margin:'4px 0 10px'}}>
    {liveComplete?'Latest authenticated reports: all 32 FOCUS trials reconciled.':
      'Visible source-checked snapshot dated '+FOCUS_CHART_SNAPSHOT_DATE+
      '. This snapshot remains visible when authenticated saved assessments are loading or unavailable; newer reports may differ.'}
    {' '}All numeric scores show provisional documentation readiness, not FDA approval likelihood.
   </p>
   <FocusSurveyTrendChart trials={chartTrials} total={chartTotal} selectedNct={selectedNct}/>
  </div>
  {error&&<p role="alert">{error}</p>}{message&&<p role="status">{message}</p>}
  {!data&&!error&&<p role="status">Loading persisted assessments…</p>}
  {data&&<><p>Database roster: {data.total===null?'NOT RECONCILED':data.total+' exact trials'}. All three research executions saved: <strong>{data.fullyProcessed??0} / {data.total??'?'}</strong> trials ({data.counts['1']?.processed??0}+{data.counts['2']?.processed??0}+{data.counts['3']?.processed??0} saved level reports). Roster status: {data.status.replaceAll('_',' ')}.</p>
   {data.source&&<p><a href={data.source.source_url} target="_blank" rel="noopener noreferrer">Owner roster source</a> · Retrieved {data.source.retrieved_at} · {data.source.authority_status.replaceAll('_',' ')}. PDUFA dates are owner-source reports until exact application linkage is verified.</p>}
   <ul>{[1,2,3].map(l=><li key={l}>Level {l}: {data.counts[String(l)]?.processed??0} executions saved; {data.counts[String(l)]?.scored??0} validated numerical scores; {data.counts[String(l)]?.incomplete??0} incomplete/unscorable; {data.counts[String(l)]?.failed??0} execution failures; {data.trials.reduce((count,t)=>count+(t.levels[String(l)]?.missingEvidence?.length||0),0)} unresolved source criteria.</li>)}</ul>
   <label>Filter saved FOCUS trials <input value={filter} onChange={e=>setFilter(e.target.value)}/></label>{' '}
   <label>Saved assessment level <select value={level} onChange={e=>setLevel(e.target.value)}><option value="ALL">All three levels side by side</option>{[1,2,3].map(l=><option key={l} value={l}>Level {l}</option>)}<option disabled>Future levels — unavailable</option></select></label>{' '}
   <button type="button" disabled={busy} onClick={()=>{setError('');void load().then(()=>setMessage('Refreshed saved database results.')).catch(e=>setError(e.message));}}>Refresh saved results</button>{' '}
   <button type="button" disabled={busy||data.total===null||data.fullyProcessed===data.total} onClick={()=>void batch()}>Process next bounded batch</button>
   {data.total!==null&&data.fullyProcessed===data.total&&<p role="status">Every reconciled FOCUS trial already has all three research reports saved. No rerun is necessary unless new evidence warrants a new immutable version.</p>}
   <p data-testid="focus-provisional-scores-progress">
     <strong>Provisional evidence-readiness scores: {provisionalScores} / {(data.total??0)*3}</strong>.
     {data.total!==null&&data.total>0&&provisionalScores===data.total*3?
       ' All three evidence-readiness values are present for every exact FOCUS NCT.':
       ' Unmatched or newer assessment runs are withheld until their evidence is rescored.'}
     {' '}{FOCUS_READINESS_METHOD}
   </p>
   <FocusOverallLevelMatrix trials={rows} selectedNct={selectedNct}/>
   <div style={{overflowX:'auto',marginTop:12}}><table style={{borderCollapse:'collapse',minWidth:850,width:'100%'}}><thead><tr><th>Trial</th>{[1,2,3].filter(l=>level==='ALL'||level===String(l)).flatMap(l=>[<th key={l+'s'}>L{l} Scientific result and evidence</th>,<th key={l+'p'}>L{l} FDA prediction status</th>])}</tr></thead>
    <tbody>{rows.map(t=><tr key={t.nct} style={{borderTop:'1px solid #b9cebe'}}><td style={{padding:10}}><Link href={'/predictions/assessment?nct='+encodeURIComponent(t.nct)}>{t.nct}</Link><br/>{t.ticker} · {t.company}<br/>{t.levels['1']?.report?.trialIdentity.candidate||'Candidate not yet source-verified'}<br/>PDUFA: {t.pdufaDate||'Not assigned/verified'}<br/><Link href={'/company?ticker='+encodeURIComponent(t.ticker)}>COMPANY</Link> · <Link href="/focus">FOCUS</Link></td>
     {[1,2,3].filter(l=>level==='ALL'||level===String(l)).flatMap(l=>{const slot=t.levels[String(l)],r=slot?.report;return [<td key={l+'s'} style={{padding:10,verticalAlign:'top'}}>{r?<><Link href={'/predictions/assessment?nct='+encodeURIComponent(t.nct)}>{r.score.kind==='NOT_VALIDATED'||r.score.kind==='LEVEL_SPECIFIC_EVIDENCE_COVERAGE'?'NOT VALIDATED / UNSCORABLE':r.score.value===null?'NOT VALIDATED / UNSCORABLE':r.score.value}</Link><br/>{(()=>{const v=provisionalFocusScore(t.nct,l,r);return v?
       <span><strong>Provisional evidence readiness: {v.evidenceReadinessScore}/100</strong>
       {' '}({v.sourceVerified}/{v.applicable} source verified)<br/></span>:null;})()}
       {r.executionStatus}<br/>{r.context.phases.join(', ')}<br/>{r.executedAt}<br/><small>{r.engineVersion}</small><details><summary>{slot.missingEvidence.length} unresolved criteria · evidence details</summary><p>{r.score.method}</p><ul>{slot.missingEvidence.map(c=><li key={c.id}>{c.id} · {c.state}: {c.explanation}</li>)}</ul><Link href={'/predictions/assessment?nct='+encodeURIComponent(t.nct)}>Open original-source findings and all saved versions</Link></details></>:<><strong>{slot?.state||'NOT RUN'}</strong><br/>{slot?.error||'No completed assessment saved'}</>}</td>,<td key={l+'p'} style={{padding:10,verticalAlign:'top'}}>{r?<>{r.fdaPrediction.outcome}<br/>Confidence: {r.fdaPrediction.probability===null||r.fdaPrediction.probability===undefined?'NOT VALIDATED':r.fdaPrediction.probability+'%'}<br/>{r.fdaPrediction.confidence}</>:'ABSTAIN — no completed result'}</td>];})}
    </tr>)}</tbody></table></div>
  </>}
 </section>;
}
