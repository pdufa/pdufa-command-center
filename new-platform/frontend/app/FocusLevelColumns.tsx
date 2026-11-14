'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
type Report={runId:string;nct:string;level:number;executedAt:string;mode:string;score?:{value:number|null;kind:string};fdaPrediction?:{outcome:string;confidence:string}};
const cache=new Map<string,Report[]>();
export function FocusLevelHeaders(){return <>{[1,2,3].map(level=><th key={level} colSpan={2} scope="colgroup" style={{textAlign:'center',whiteSpace:'nowrap'}}>Level {level}</th>)}</>;}
export function FocusLevelSubheaders(){return <>{[1,2,3].flatMap(level=>[<th key={level+'p'}>Prediction</th>,<th key={level+'s'}>Evidence score</th>])}</>;}
export function FocusLevelCells({nct}:{nct:string}){
 const [reports,setReports]=useState<Report[]|null>(cache.get(nct)||null);
 const [error,setError]=useState(false);
 useEffect(()=>{let active=true;if(cache.has(nct)){setReports(cache.get(nct)!);return;}fetch('/api/assessments/runtime?nct='+encodeURIComponent(nct),{cache:'no-store'}).then(async r=>{if(!r.ok)throw Error('History unavailable');return r.json()}).then(data=>{const list=(data.runs||[]) as Report[];cache.set(nct,list);if(active)setReports(list)}).catch(()=>{if(active)setError(true)});return()=>{active=false}},[nct]);
 return <>{[1,2,3].flatMap(level=>{const report=reports?.filter(r=>r.level===level&&r.mode==='CURRENT_EVIDENCE').sort((a,b)=>b.executedAt.localeCompare(a.executedAt))[0];const prediction=report?.fdaPrediction?.outcome;return [
 <td key={level+'p'} title={report?'Saved assessment '+report.runId:'No saved current-evidence assessment; results must be executed and verified'}>{report?(prediction&&prediction!=='ABSTAIN'?prediction:'ABSTAIN · not predicted'):error?'Unavailable':'Not predicted'}</td>,
 <td key={level+'s'} title="Scientific evidence coverage, not FDA probability">{report?<Link href={'/assessments?nct='+encodeURIComponent(nct)}>{report.score?.value===null?'N/A':typeof report.score?.value==='number'?report.score.value+'%':'Not scored'}</Link>:error?'Unavailable':reports?'Not scored':'Loading…'}</td>
 ]})}</>;
}
