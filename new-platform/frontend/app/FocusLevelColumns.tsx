'use client';
import Link from 'next/link';
import {provisionalFocusScore} from '../lib/focus-provisional-scores';

type SavedFocusReport={
 runId:string;nct:string;level:number;executedAt:string;mode:string;
 executionStatus?:string;scientificStatus?:string;
 score?:{value:number|null;kind:string;method?:string};
 fdaPrediction?:{outcome:string;confidence:string};
 trialIdentity?:{company:string;candidate:string;indication:string[]};
 context?:{phases:string[]};
};
export type FocusTrialSlot={
 state:string;runId?:string|null;error?:string|null;
 report:SavedFocusReport|null;
 missingEvidence?:{id:string;state:string;explanation:string}[];
};
export type FocusTrialLevels=Record<string,FocusTrialSlot>;

const description=['','Trial verification','Clinical trial design','Efficacy and statistics'];
const scientific=(report:SavedFocusReport|null|undefined)=>
 report?.score?.kind==='NOT_VALIDATED'||report?.score?.kind==='LEVEL_SPECIFIC_EVIDENCE_COVERAGE'
  ?'NOT VALIDATED'
  :typeof report?.score?.value==='number'&&Number.isFinite(report.score.value)
   ?String(report.score.value):'NOT VALIDATED';
const link=(nct:string)=>'/predictions/assessment?nct='+encodeURIComponent(nct);
const exactReport=(slot:FocusTrialSlot|undefined,nct:string,level:number)=>slot?.report?.mode==='CURRENT_EVIDENCE'&&slot.report.nct===nct&&slot.report.level===level?slot.report:null;

export function FocusLevelHeaders(){
 return <>{[1,2,3].map(level=><th key={level} colSpan={2} scope="colgroup" style={{textAlign:'center',whiteSpace:'nowrap'}}>Survey Level {level}</th>)}</>;
}
export function FocusLevelSubheaders(){
 return <>{[1,2,3].flatMap(level=>[
  <th key={level+'p'}>FDA Forecast Status</th>,<th key={level+'s'}>Evidence Readiness / Saved Report</th>
 ])}</>;
}

/** The parent fetched one reconciled owner roster; each row never makes its own request. */
export function FocusLevelCells({nct,levels,loading=false,error=false}:{
 nct:string;levels?:FocusTrialLevels;loading?:boolean;error?:boolean;
}){
 return <>{[1,2,3].flatMap(level=>{
  const slot=levels?.[String(level)];
  const report=exactReport(slot,nct,level);
  const provisional=provisionalFocusScore(nct,level,report);
  const state=error?'Unavailable':loading?'Loading…':slot?.state||'NOT RUN';
  const prediction=report?.fdaPrediction?.outcome;
  return [
   <td key={level+'p'} title={report?'Saved '+report.runId:'No completed current-evidence scientific report'} style={{whiteSpace:'nowrap'}}>
    {report?(prediction&&prediction!=='ABSTAIN'?prediction:'ABSTAIN · not validated'):state}
   </td>,
   <td key={level+'s'} title={report?'Saved source-linked scientific research; numerical scientific validation is separate':'No completed current-evidence scientific report'} style={{whiteSpace:'nowrap'}}>
    {report?<Link href={link(nct)}>{provisional?
     'Provisional evidence '+provisional.evidenceReadinessScore+'/100 · scientific NOT VALIDATED':
     scientific(report)+' · saved'}</Link>:state}
   </td>
  ];
 })}</>;
}

export function FocusSurveyRowDetails({nct,levels,loading=false,error=false}:{
 nct:string;levels?:FocusTrialLevels;loading?:boolean;error?:boolean;
}){
 const done=[1,2,3].filter(level=>exactReport(levels?.[String(level)],nct,level)).length;
 return <td style={{padding:10,minWidth:205,verticalAlign:'top'}}>
  {error?<span role="alert">Saved results unavailable</span>:loading?<span>Loading saved surveys…</span>:<>
   <details>
    <summary style={{cursor:'pointer',fontWeight:700}}>{done}/3 surveys saved · view</summary>
    <ul style={{paddingLeft:18,margin:'8px 0'}}>
     {[1,2,3].map(level=>{
      const slot=levels?.[String(level)],report=exactReport(slot,nct,level);
      const provisional=provisionalFocusScore(nct,level,report);
      const gaps=slot?.missingEvidence||[];
      return <li key={level} style={{marginBottom:10}}>
       <strong>L{level} · {description[level]}</strong>
       {report?<><div>COMPLETED · Scientific score: {scientific(report)}</div>{provisional&&<div><strong>Provisional evidence readiness: {provisional.evidenceReadinessScore}/100</strong> · {provisional.sourceVerified}/{provisional.applicable} verified checks</div>}
        <div>FDA call: {report.fdaPrediction?.outcome||'ABSTAIN'}</div>
        <div>Unresolved criteria: {gaps.length}</div>
        {gaps.length>0&&<details><summary>View evidence gaps</summary><ul>{gaps.map(g=><li key={g.id}>{g.id} · {g.state}: {g.explanation}</li>)}</ul></details>}
       </>:<div>{slot?.state||'NOT RUN'}{slot?.error?' · '+slot.error:''}</div>}
      </li>;
     })}
    </ul>
    <Link href={link(nct)}>Open all 3 reports and original sources in ASSESSMENTS</Link>
   </details>
   <div style={{fontSize:12,marginTop:5}}>{done===3?'All levels completed; scores not validated.':done+' of 3 current-evidence levels saved.'}</div>
  </>}
  <div style={{marginTop:5,fontSize:12}}><Link href={link(nct)}>Detailed Level 1–3 findings</Link></div>
 </td>;
}
