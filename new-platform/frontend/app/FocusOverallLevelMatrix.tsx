'use client';
import Link from 'next/link';
import type {FocusTrialLevels} from './FocusLevelColumns';

export const FOCUS_TWENTY_LEVEL_LABELS=[
 'Trial identity','Current phase','Source evidence','Study protocol','Population',
 'Efficacy','Statistics','Safety','Clinical benefit','Comparator',
 'Subgroups','Data gaps','Regulatory history','FDA alignment','Manufacturing',
 'Benefit–risk','Exceptions','External evidence','Confidence','Integrated review'
] as const;
const reportFor=(levels:FocusTrialLevels|undefined,nct:string,level:number)=>{
 const r=levels?.[String(level)]?.report;
 return r&&r.nct===nct&&r.level===level&&r.mode==='CURRENT_EVIDENCE'?r:null;
};
export function ownerSurveyStatus(nct:string,levels?:FocusTrialLevels){
 const reports=[1,2,3].map(level=>reportFor(levels,nct,level));
 const completed=reports.filter(Boolean).length;
 // Research observations are NOT validated scientific numerical scores.
 // No overall approval forecast is inferred from these three unvalidated runs.
 return {completed,overall:'NOT VALIDATED',direction:
  completed===3&&reports.every(r=>r?.fdaPrediction?.outcome==='ABSTAIN')
    ?'ABSTAIN':'NOT AVAILABLE'};
}

export function FocusOverallHeaders(){
 return <>
  <th scope="col" style={{whiteSpace:'nowrap'}}>Overall prediction survey result</th>
  <th scope="col" style={{whiteSpace:'nowrap'}}>FDA direction</th>
 </>;
}
export function FocusTwentyHeaders({className}:{className?:string}={}){
 return <>{FOCUS_TWENTY_LEVEL_LABELS.map((name,i)=>
  <th scope="col" className={className} key={name}
    title={'L'+String(i+1).padStart(2,'0')+' — '+name}
    style={{whiteSpace:'nowrap'}}>L{String(i+1).padStart(2,'0')}-{name}</th>)}</>;
}
export function FocusOverviewCells({nct,levels,loading=false,error=false}:{
 nct:string;levels?:FocusTrialLevels;loading?:boolean;error?:boolean;
}){
 const status=ownerSurveyStatus(nct,levels);
 return <>
  <td data-testid="focus-overall-survey-result" style={{padding:10,whiteSpace:'nowrap'}}>
   {error?'Unavailable':loading?'Loading…':<><strong>{status.overall}</strong>
    <div style={{fontSize:12}}>{status.completed}/3 current research surveys saved</div>
    <Link href={'/predictions/assessment?nct='+encodeURIComponent(nct)}>See evidence</Link>
   </>}
  </td>
  <td data-testid="focus-overall-direction" style={{padding:10,whiteSpace:'nowrap'}}>
   {error?'Unavailable':loading?'Loading…':<><strong>{status.direction}</strong>
    <div style={{fontSize:12}}>No validated FDA forecast</div>
   </>}
  </td>
 </>;
}
export function FocusTwentyCells({nct,levels,loading=false,error=false,className}:{
 nct:string;levels?:FocusTrialLevels;loading?:boolean;error?:boolean;className?:string;
}){
 const href='/predictions/assessment?nct='+encodeURIComponent(nct);
 return <>{FOCUS_TWENTY_LEVEL_LABELS.map((name,i)=>{
  const level=i+1,report=level<=3?reportFor(levels,nct,level):null;
  // Saved scientific L1–3 reports do not automatically complete or score the
  // independent 20-dimension rubric. They may be inspected for future scoring.
  return <td key={name} data-assessment-level={'L'+String(level).padStart(2,'0')}
    className={className} title={'L'+level+' '+name+': independent 20-level rubric score pending. '+
       (report?'Current scientific research is saved separately.':'No mapped current research report.')}
    style={{padding:10,whiteSpace:'nowrap'}}>
    {error?'Unavailable':loading?'Loading…':
      <>{'Rubric pending'}{report&&<div style={{fontSize:12}}>
        <Link href={href}>Research saved · unscored</Link>
       </div>}</>}
   </td>;
 })}</>;
}
export default function FocusOverallLevelMatrix({trials,selectedNct}:{
 trials:{nct:string;ticker:string;company:string;levels:FocusTrialLevels}[];selectedNct?:string;
}){
 return <section id="focus-overall-level-matrix" aria-label="FOCUS overall prediction, direction and Levels 1–20"
  style={{margin:'16px 0',padding:12,border:'1px solid #abc9b6',borderRadius:10}}>
  <h3 style={{margin:'0 0 6px'}}>Trial result sheet · Overall → Direction → Levels 1–20</h3>
  <p style={{fontSize:13,margin:'0 0 10px'}}>
   The overall result is the scientifically validated prediction-survey finding,
   not an average of evidence counts. Levels 1–3 have saved research reports,
   but none is a validated numerical rubric score. Levels 4–20 of this rubric
   are pending. An FDA direction remains ABSTAIN until supported by an independently
   defined and validated forecast process; no approval percentage is implied.
  </p>
  <div style={{overflowX:'auto'}}>
   <table data-testid="focus-overall-direction-level20-table"
    style={{borderCollapse:'collapse',minWidth:1900,width:'100%',fontSize:13}}>
    <thead style={{background:'#e8f3ed'}}><tr>
      <th scope="col" style={{whiteSpace:'nowrap'}}>FOCUS trial</th>
      <FocusOverallHeaders/>
      <FocusTwentyHeaders/>
    </tr></thead>
    <tbody>{trials.map(t=><tr key={t.nct}
      style={{borderTop:'1px solid #dbe6df',background:t.nct===selectedNct?'#eff7ff':undefined}}>
      <th scope="row" style={{textAlign:'left',padding:9,whiteSpace:'nowrap'}}>
       <Link href={'/predictions/assessment?nct='+encodeURIComponent(t.nct)}>{t.ticker} · {t.nct}</Link>
       <div style={{fontWeight:400,fontSize:12}}>{t.company}</div>
      </th>
      <FocusOverviewCells nct={t.nct} levels={t.levels}/>
      <FocusTwentyCells nct={t.nct} levels={t.levels}/>
    </tr>)}</tbody>
   </table>
  </div>
 </section>;
}
