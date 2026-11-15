'use client';
import {useEffect,useState} from 'react';

type SavedLevel={
 runId:string;executedAt:string;name:string;executionStatus:string;
 score:{value:number|null;kind:string;method:string};
 fdaPrediction:{outcome:string;confidence:string};
 scientificStatus:string;unresolved:number;sourceUrl:string
};
type HistoricalTrial={nct:string;cutoffDate:string;eventLinkage:string;levels:Record<string,SavedLevel>};
type HistoricalSummary={status:string;trials:HistoricalTrial[];truncated:boolean};

export default function PastSavedAssessments(){
 const [data,setData]=useState<HistoricalSummary|null>(null);
 const [error,setError]=useState('');
 const [busy,setBusy]=useState(false);
 const [filter,setFilter]=useState('');
 async function load(signal?:AbortSignal){
  setBusy(true);setError('');
  try{
   const response=await fetch('/api/assessments/runtime?past=true',{cache:'no-store',signal});
   const body=await response.json();
   if(!response.ok)throw Error(body.error||'Saved historical assessments unavailable');
   if(!signal?.aborted)setData(body as HistoricalSummary);
  }catch(e){if(!signal?.aborted)setError(e instanceof Error?e.message:'Cannot load saved history');}
  finally{if(!signal?.aborted)setBusy(false);}
 }
 useEffect(()=>{const controller=new AbortController();const refresh=()=>void load(controller.signal);refresh();if(typeof window!=='undefined')window.addEventListener('pdufa:assessment-saved',refresh);return()=>{controller.abort();if(typeof window!=='undefined')window.removeEventListener('pdufa:assessment-saved',refresh);};},[]);
 const trials=(data?.trials||[]).filter(t=>(t.nct+' '+t.cutoffDate).toLowerCase().includes(filter.toLowerCase()));
 return <section aria-label="PAST saved blind Level 1–3 assessments" style={{border:'1px solid #b9cebe',borderRadius:8,padding:14,margin:'16px 0'}}>
  <h2>PAST · Saved blind historical assessments · Levels 1–3</h2>
  <p>These are immutable source-bound blind runs grouped by exact NCT and historical evidence cutoff. They are <strong>not automatically matched to the 2026 PAST event queue</strong>; the trial, FDA application and decision-date relationship requires independent verification. No FDA outcomes are read for these results.</p>
  <p>Scientific scores without validated specifications remain <strong>NOT VALIDATED / UNSCORABLE</strong>. FDA predictions without a validated model remain <strong>ABSTAIN</strong>. Missing pre-cutoff evidence is never replaced with current evidence.</p>
  <label>Find saved historical trial <input aria-label="Find saved historical trial" value={filter} onChange={e=>setFilter(e.target.value)} placeholder="NCT or cutoff date"/></label>{' '}
  <button type="button" disabled={busy} onClick={()=>void load()}>{busy?'Loading…':'Refresh historical results'}</button>
  {error&&<p role="alert">{error}</p>}
  {!data&&!error&&<p role="status">Loading saved blind history…</p>}
  {data&&<><p role="status">{data.trials.length} saved exact trial/cutoff groups. {data.truncated?'More saved versions exist than the bounded index can show.':'No PAST 2026 event reconciliation is implied.'}</p>
   {data.trials.length===0&&<p>No completed blind Level 1–3 scientific assessments are saved in the persistent database. Verify historical application linkage and pre-decision source snapshots before running.</p>}
   <div style={{overflowX:'auto'}}>
    <table style={{borderCollapse:'collapse',width:'100%',minWidth:900,fontSize:13}}>
     <thead><tr><th style={{textAlign:'left'}}>Exact trial · historical cutoff</th>{[1,2,3].flatMap(l=>[<th key={l+'score'}>L0{l} scientific score</th>,<th key={l+'prediction'}>L0{l} FDA prediction</th>])}</tr></thead>
     <tbody>{trials.map(t=><tr key={t.nct+'|'+t.cutoffDate} style={{borderTop:'1px solid #d9e5dd'}}>
       <td style={{padding:10,verticalAlign:'top'}}><strong>{t.nct}</strong><br/>Evidence cutoff: {t.cutoffDate}<br/><small>PAST event linkage: not yet reconciled</small><br/><a href={'/assessments?nct='+encodeURIComponent(t.nct)}>See saved versions and evidence</a></td>
       {[1,2,3].flatMap(l=>{const r=t.levels[String(l)];return [
        <td key={l+'score'} style={{padding:10,verticalAlign:'top'}}>{r?<><strong>{r.score.value===null?'NOT VALIDATED / UNSCORABLE':r.score.value}</strong><br/>{r.executionStatus}<br/>{r.executedAt}<br/><small>{r.unresolved} unresolved checks</small><br/><a target="_blank" rel="noopener noreferrer" href={r.sourceUrl}>Original source</a></>:'NOT RUN'}</td>,
        <td key={l+'prediction'} style={{padding:10,verticalAlign:'top'}}>{r?<>{r.fdaPrediction.outcome}<br/><small>{r.fdaPrediction.confidence}</small></>:'ABSTAIN — no saved assessment'}</td>
       ];})}
      </tr>)}</tbody>
    </table>
   </div>
  </>}
 </section>;
}
