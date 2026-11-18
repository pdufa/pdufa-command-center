'use client';
import {useEffect,useState} from 'react';
import {validateLevel7CoverageReport,type Level7CoverageReport} from '../lib/level7-focus-coverage';

export default function FocusLevel7Evidence({selectedNct}:{selectedNct?:string}){
 const [report,setReport]=useState<Level7CoverageReport|null>(null);
 const [error,setError]=useState('No published Level 7 evidence report is configured.');
 useEffect(()=>{
  let active=true;
  async function load(){
   try{
    const response=await fetch('/api/focus-level7-coverage',{cache:'no-store'});
    if(!response.ok)throw Error('Level 7 evidence report unavailable');
    const value=validateLevel7CoverageReport(await response.json());
    if(active){setReport(value);setError('');}
   }catch(e){if(active){setReport(null);setError(e instanceof Error?e.message:'Level 7 unavailable');}}
  }
  void load();
  const timer=setInterval(()=>void load(),60000);
  return()=>{active=false;clearInterval(timer);};
 },[]);
 const rows=report?.trials.filter(row=>!selectedNct||row.nct===selectedNct)||[];
 return <section aria-label="Level 7 FOCUS evidence coverage" style={{border:'1px solid #b9cebe',borderRadius:8,padding:14,margin:'16px 0'}}>
  <h2>Level 7 · Source evidence coverage</h2>
  <p>This is an evidence inventory, not a scientific score or FDA approval prediction. Missing evidence is not evidence of failure.</p>
  {report?<><p role="status">{report.trialsWithEvidence} / 32 trials have at least one stored source observation. Roster snapshot: {report.rosterAsOf}. No Level 7 FDA predictions have been validated.</p>
   <div style={{overflowX:'auto'}}><table><thead><tr><th>Trial</th><th>Source versions</th><th>Distinct sources</th><th>Verified</th><th>Conflicts</th><th>Coverage</th><th>FDA prediction</th></tr></thead><tbody>
    {rows.map(row=><tr key={row.nct}><td>{row.nct}</td><td>{row.sourceVersions}</td><td>{row.distinctSources}</td><td>{row.statusCounts.verified}</td><td>{row.statusCounts.conflicting}</td><td>{row.readiness.replaceAll('_',' ')}</td><td>ABSTAIN — NOT SCORED</td></tr>)}
   </tbody></table></div></>:<p role="status">{error} No Level 7 scores or predictions are displayed.</p>}
 </section>;
}
