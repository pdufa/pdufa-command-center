'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {readSavedFocus} from '../lib/focus-saved-records';
type Report={runId:string;nct:string;level:number;executedAt:string;mode:string;score?:{value:number|null;kind:string};fdaPrediction?:{outcome:string;confidence:string}};

export function FocusLevelHeaders(){return <>{[1,2,3].map(level=><th key={level} colSpan={2} scope="colgroup" style={{textAlign:'center',whiteSpace:'nowrap'}}>Level {level}</th>)}</>;}
export function FocusLevelSubheaders(){return <>{[1,2,3].flatMap(level=>[<th key={level+'p'}>Prediction</th>,<th key={level+'s'}>Scientific score</th>])}</>;}
export function FocusLevelCells({nct}:{nct:string}){
 const [reports,setReports]=useState<Report[]|null>(null);
 const [error,setError]=useState(false);
 useEffect(()=>{
  let active=true;
  async function refresh(){
   try{
    const data=await readSavedFocus() as {trials:{nct:string;levels:Record<string,{report:Report|null}>}[]};
    const trial=data.trials.find(t=>t.nct===nct);
    if(active){setReports(trial?Object.values(trial.levels).flatMap(s=>s.report?[s.report]:[]):[]);setError(false);}
   }catch{if(active)setError(true);}
  }
  setReports(null);setError(false);void refresh();
  const interval=setInterval(()=>void refresh(),30000);
  const onFocus=()=>void refresh();
  window.addEventListener('focus',onFocus);
  window.addEventListener('pdufa:assessment-saved',onFocus);
  return()=>{active=false;clearInterval(interval);window.removeEventListener('focus',onFocus);window.removeEventListener('pdufa:assessment-saved',onFocus);};
 },[nct]);
 return <>{[1,2,3].flatMap(level=>{const report=reports?.filter(r=>r.level===level&&r.mode==='CURRENT_EVIDENCE').sort((a,b)=>b.executedAt.localeCompare(a.executedAt))[0];const prediction=report?.fdaPrediction?.outcome;return [
 <td key={level+'p'} title={report?'Saved assessment '+report.runId:'No saved current-evidence assessment; results must be executed and verified'}>{report?(prediction&&prediction!=='ABSTAIN'?prediction:'ABSTAIN · not predicted'):error?'Unavailable':'Not predicted'}</td>,
 <td key={level+'s'} title="Saved scientific result; unvalidated scores are withheld">{report?<Link href={'/assessments?nct='+encodeURIComponent(nct)}>{report.score?.value===null?'NOT VALIDATED / UNSCORABLE':typeof report.score?.value==='number'?String(report.score.value):'Not scored'}</Link>:error?'Unavailable':reports?'Not scored':'Loading…'}</td>
 ]})}</>;
}
