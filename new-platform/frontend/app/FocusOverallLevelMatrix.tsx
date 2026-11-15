'use client';
import Link from 'next/link';
import {useState} from 'react';
import type {FocusTrialLevels} from './FocusLevelColumns';
import {provisionalFocusScore,FOCUS_READINESS_METHOD} from '../lib/focus-provisional-scores';

export const FOCUS_TWENTY_LEVEL_LABELS=[
 'Trial identity','Clinical design','Efficacy / statistics evidence','Study protocol','Population',
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

export function FocusOverallHeaders({expanded=false,onToggle}:{
 expanded?:boolean;onToggle?:()=>void;
}={}){
 return <>
  <th scope="col" style={{whiteSpace:'nowrap'}}>
   Overall prediction survey result
   {onToggle&&<button type="button" onClick={onToggle} aria-expanded={expanded}
    aria-label={(expanded?'Collapse':'Expand')+' survey Levels 1–20 horizontally'}
    title={(expanded?'Collapse':'Expand')+' the 20 survey columns horizontally'}
    data-testid="survey-horizontal-collapse"
    style={{display:'inline-block',marginLeft:8,padding:'4px 9px',border:'1px solid #7e9f8b',
      borderRadius:5,cursor:'pointer',background:'#fff',color:'#173d2b',fontWeight:800}}>
    {expanded?'− 20 Levels':'+ 20 Levels'}
   </button>}
  </th>
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
  const provisional=level<=3?provisionalFocusScore(nct,level,report):null;
  // Provisional numerical documentary evidence coverage is NOT a validated
  // trial scientific-strength rating, an FDA approval probability or forecast.
  return <td key={name} data-assessment-level={'L'+String(level).padStart(2,'0')}
    className={className} title={provisional?
       'L'+level+' · '+FOCUS_READINESS_METHOD+' '+provisional.sourceVerified+' of '+
        provisional.applicable+' applicable criteria strictly SOURCE_VERIFIED. Run '+provisional.runId:
       'L'+level+' '+name+': provisional evidence score unavailable or rubric pending.'}
    style={{padding:10,whiteSpace:'nowrap'}}>
    {error?'Unavailable':loading?'Loading…':provisional?
      <><strong data-testid={'provisional-L'+String(level).padStart(2,'0')+'-score'}>{provisional.evidenceReadinessScore}/100</strong>
       <div style={{fontSize:12}}>Evidence readiness · provisional</div>
       <div style={{fontSize:12}}>{provisional.sourceVerified}/{provisional.applicable} verified checks</div>
       <Link href={href}>Source survey · L{level}</Link>
      </>:<>
       <span>{report&&level<=3?'Reassessment: score pending':'Rubric pending'}</span>
       {report&&<div style={{fontSize:12}}><Link href={href}>Research saved · scientific score not validated</Link></div>}
      </>}
   </td>;
 })}</>;
}
export default function FocusOverallLevelMatrix({trials,selectedNct,initiallyExpanded=false}:{
 trials:{nct:string;ticker:string;company:string;levels:FocusTrialLevels}[];
 selectedNct?:string;initiallyExpanded?:boolean;
}){
 const [surveyLevelsExpanded,setSurveyLevelsExpanded]=useState(initiallyExpanded);
 return <section id="focus-overall-level-matrix" aria-label="FOCUS overall prediction, direction and Levels 1–20"
  style={{margin:'16px 0',padding:12,border:'1px solid #abc9b6',borderRadius:10}}>
  <h3 style={{margin:'0 0 6px'}}>Trial result sheet · Overall → Direction → Levels 1–20</h3>
  <p style={{fontSize:13,margin:'0 0 10px'}}>
   Overall result and FDA direction are not inferred by averaging source checks.
   L01–L03 show provisional documentation evidence-readiness scores out of 100,
   independently calculated from exact saved reports; these are not validated
   scientific-strength scores, efficacy ratings or FDA probabilities.
   L04–L20 remain pending. Actual FDA direction remains ABSTAIN.
  </p>
  <div style={{overflowX:'auto'}}>
   <table data-testid="focus-overall-direction-level20-table"
    style={{borderCollapse:'collapse',minWidth:surveyLevelsExpanded?1900:650,width:'100%',fontSize:13}}>
    <thead style={{background:'#e8f3ed'}}><tr>
      <th scope="col" style={{whiteSpace:'nowrap'}}>FOCUS trial</th>
      <FocusOverallHeaders expanded={surveyLevelsExpanded}
        onToggle={()=>setSurveyLevelsExpanded(v=>!v)}/>
      {surveyLevelsExpanded&&<FocusTwentyHeaders/>}
    </tr></thead>
    <tbody>{trials.map(t=><tr key={t.nct}
      style={{borderTop:'1px solid #dbe6df',background:t.nct===selectedNct?'#eff7ff':undefined}}>
      <th scope="row" style={{textAlign:'left',padding:9,whiteSpace:'nowrap'}}>
       <Link href={'/predictions/assessment?nct='+encodeURIComponent(t.nct)}>{t.ticker} · {t.nct}</Link>
       <div style={{fontWeight:400,fontSize:12}}>{t.company}</div>
      </th>
      <FocusOverviewCells nct={t.nct} levels={t.levels}/>
      {surveyLevelsExpanded&&<FocusTwentyCells nct={t.nct} levels={t.levels}/>}
    </tr>)}</tbody>
   </table>
  </div>
 </section>;
}
