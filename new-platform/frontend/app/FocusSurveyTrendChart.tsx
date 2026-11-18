'use client';
import {useMemo,useState} from 'react';
import {provisionalFocusScore,provisionalFocusOverall,focusSavedDirection} from '../lib/focus-provisional-scores';

/**
 * Cross-sectional research evidence chart for the reconciled FOCUS roster.
 * It must never be described as a scientific score, FDA probability, clinical
 * outcome, prospective accuracy, or chronological performance trend.
 */
type EvidenceCounts={total:number;sourceVerified:number;unresolved:number};
type SourceReport={nct:string;level:number;mode:string;executedAt:string;runId:string;engineVersion?:string;score?:{kind:string;value:number|null};fdaPrediction?:{outcome:string}};
type SourceSlot={state:string;report:SourceReport|null;missingEvidence?:{id:string;state:string;explanation:string}[];evidenceChecks?:EvidenceCounts|null};
export type SurveyChartTrial={nct:string;ticker:string;company:string;levels:Record<string,SourceSlot>};
type Metric='UNRESOLVED'|'VERIFIED_PERCENT';
type Datum={trial:SurveyChartTrial;value:number|null;at:string|null};

const LEVELS=[{number:1,name:'L1 · Trial identity',color:'#186c9b'},
 {number:2,name:'L2 · Study design',color:'#9651a6'},
 {number:3,name:'L3 · Efficacy & statistics',color:'#b46122'},
 {number:4,name:'L4 · Evidence coverage',color:'#257d54'},
 {number:5,name:'L5 · Evidence coverage',color:'#c23c68'},
 {number:6,name:'L6 · Evidence coverage',color:'#6b6e17'}] as const;
const unresolvedStates=new Set(['MISSING','UNVERIFIED','CONCERNS','NOT_ASSESSED','BLOCKED_UNVERIFIED_PHASE']);
const maxTrialCount=500;
const validNct=(nct:string)=>/^NCT[0-9]{8}$/.test(nct);

export function focusSurveyDatum(trial:SurveyChartTrial,level:number,metric:Metric):Datum{
 const slot=trial.levels?.[String(level)];
 const report=slot?.report;
 if(!report||report.nct!==trial.nct||report.level!==level||report.mode!=='CURRENT_EVIDENCE')
  return {trial,value:null,at:null};
 const checkCounts=slot.evidenceChecks;
 if(metric==='UNRESOLVED'){
  // A pinned source report contains a checked unresolved count even when
  // the protected API has not supplied the individual missing-evidence list.
  const snap=provisionalFocusScore(trial.nct,level,report);
  if(snap)return {trial,value:snap.unresolved,at:report.executedAt};
  const gaps=slot.missingEvidence;
  // Raw, unscored evidence gaps were present in the saved summaries before
  // the newer descriptive check-count API. Do not infer a missing array as 0.
  if(!Array.isArray(gaps)||gaps.some(item=>!item||!unresolvedStates.has(item.state)))
   return {trial,value:null,at:report.executedAt};
  return {trial,value:gaps.length,at:report.executedAt};
 }
 const snap=provisionalFocusScore(trial.nct,level,report);
 if(snap)return {trial,value:snap.evidenceReadinessScore,at:report.executedAt};
 // L4–L6 only expose their own saved, numeric evidence-coverage results.
 // Never synthesize missing scores from L1–L3 or treat them as FDA probabilities.
 if(level>=4&&level<=6&&report.score?.kind==='LEVEL_SPECIFIC_EVIDENCE_COVERAGE'&&
    typeof report.score.value==='number'&&Number.isFinite(report.score.value)&&
    report.score.value>=0&&report.score.value<=100)
  return {trial,value:report.score.value,at:report.executedAt};
 // Older or mismatched report versions cannot borrow scores from the snapshot.
 // When the backend supplies raw checks but no matching run, leave the score
 // absent rather than silently substituting a different percentage method.
 return {trial,value:null,at:report.executedAt};
}

export function focusSurveyOverallDatum(trial:SurveyChartTrial,metric:Metric):Datum{
 const overall=provisionalFocusOverall(trial.nct,trial.levels);
 if(!overall)return {trial,value:null,at:null};
 return {trial,value:metric==='UNRESOLVED'?overall.unresolved:overall.evidenceReadinessScore,
  at:trial.levels['3']?.report?.executedAt||null};
}

/** FDA predictions are categorical. ABSTAIN is never converted to an invented zero. */
export function focusSurveyDirection(trial:SurveyChartTrial):'ABSTAIN'|'NOT AVAILABLE'{
 return focusSavedDirection(trial.nct,trial.levels);
}

export function leastSquaresFit(points:{x:number;y:number}[]){
 if(points.length<2||points.some(p=>!Number.isFinite(p.x)||!Number.isFinite(p.y)))return null;
 const n=points.length,meanX=points.reduce((v,p)=>v+p.x,0)/n;
 const meanY=points.reduce((v,p)=>v+p.y,0)/n;
 const denom=points.reduce((v,p)=>v+(p.x-meanX)**2,0);
 if(denom<=0)return null;
 const slope=points.reduce((v,p)=>v+(p.x-meanX)*(p.y-meanY),0)/denom;
 return {slope,intercept:meanY-slope*meanX};
}

export default function FocusSurveyTrendChart({trials,total,selectedNct}:{
 trials:SurveyChartTrial[];total:number|null;selectedNct?:string;
}){
 const [metric,setMetric]=useState<Metric>('VERIFIED_PERCENT');
 const [visible,setVisible]=useState<Record<number,boolean>>({1:true,2:true,3:true,4:true,5:true,6:true});
 const [showDirection,setShowDirection]=useState(true);
 const [showTrend,setShowTrend]=useState(true);
 const ordered=useMemo(()=>[...trials].sort((a,b)=>a.ticker.localeCompare(b.ticker)||a.nct.localeCompare(b.nct)),[trials]);
 const ids=new Set(ordered.map(t=>t.nct));
 const reconciled=total!==null&&total>0&&total<=maxTrialCount&&ordered.length===total&&
   ids.size===total&&ordered.every(t=>validNct(t.nct)&&t.ticker&&t.levels&&[1,2,3].every(level=>!!t.levels[String(level)]));
 const allSeries=LEVELS.map(level=>({level,values:reconciled?ordered.map(t=>focusSurveyDatum(t,level.number,metric)):[]}));
 const validSeries=allSeries.map(s=>({...s,points:s.values.flatMap((d,i)=>d.value===null?[]:[{x:i,y:d.value}])}));
 const sourceMetricAvailable=ordered.some(t=>[1,2,3,4,5,6].some(l=>focusSurveyDatum(t,l,'VERIFIED_PERCENT').value!==null));
 const observed=validSeries.flatMap(s=>s.points.map(p=>p.y));
 const ceiling=metric==='VERIFIED_PERCENT'?100:Math.max(4,Math.ceil(Math.max(0,...observed)/4)*4);
 const left=74,right=1540,top=42,bottom=354,width=1610,height=598;
 const xAt=(i:number)=>left+(ordered.length===1?0:(right-left)*i/(ordered.length-1));
 const yAt=(value:number)=>bottom-(Math.min(ceiling,Math.max(0,value))/ceiling)*(bottom-top);
 const textValue=(n:number)=>metric==='VERIFIED_PERCENT'?n.toFixed(1)+'%':String(n);
 const activeSeries=validSeries.filter(s=>visible[s.level.number]);
 return <section id="focus-survey-trend-chart" aria-label="FOCUS L1–L6 independent evidence surveys and FDA direction on one chart"
   style={{border:'1px solid #c1d5cc',borderRadius:10,padding:'14px 12px',margin:'18px 0'}}>
  <h3 style={{margin:'0 0 6px'}}>FOCUS · L1–L6 independent evidence scores and FDA direction</h3>
  <p style={{margin:'0 0 12px',fontSize:13}}>
   Six individually selectable solid lines show L1–L6 source evidence coverage when saved reports exist; dashed lines are independent
   least-squares cross-trial fits, not time trends. The separate lane is the categorical
   FDA direction (ABSTAIN when no validated prediction exists), shown below the numeric
   graph without mapping it to zero or an approval percentage. These are not validated efficacy scores
   or FDA forecast probabilities.
  </p>
  <div style={{display:'flex',gap:16,flexWrap:'wrap',alignItems:'center',marginBottom:12}}>
   <label>Evidence metric{' '}
    <select aria-label="Survey chart metric" value={metric}
      onChange={e=>setMetric(e.target.value as Metric)}>
     <option value="UNRESOLVED">Unresolved source criteria · count</option>
     <option value="VERIFIED_PERCENT" disabled={!sourceMetricAvailable}>L1–L6 saved evidence-coverage scores · %</option>
    </select>
   </label>
   {LEVELS.map(l=><label key={l.number} style={{fontWeight:650,display:'inline-flex',alignItems:'center',gap:5}}>
    <input aria-label={'Show Level '+l.number+' survey line'} type="checkbox"
      checked={visible[l.number]} onChange={e=>setVisible(v=>({...v,[l.number]:e.target.checked}))}/>
    <span style={{color:l.color}}>●</span>{l.name}
   </label>)}
   <label style={{display:'inline-flex',gap:6,alignItems:'center'}}>
    <input type="checkbox" checked={showTrend} onChange={e=>setShowTrend(e.target.checked)}/>
    Show individual numeric best-fit lines
   </label>
   <label style={{display:'inline-flex',gap:6,alignItems:'center'}}>
    <input type="checkbox" checked={showDirection} onChange={e=>setShowDirection(e.target.checked)}
      aria-label="Show FDA direction categorical series"/>
    Show FDA direction (categorical)
   </label>
  </div>
  {!reconciled?<p role="alert">Verified full FOCUS source roster unavailable or mismatched. No trend or partial-trial chart is shown.</p>:
   observed.length===0?<p role="status">No suitable saved research check counts yet. Missing data are not plotted as zero.</p>:
   <>
    <p style={{fontSize:12,margin:'0 0 6px'}}>
     {ordered.length} distinct FOCUS trials · X axis: ticker / exact NCT, alphabetical (not dates) ·
     Y axis: {metric==='UNRESOLVED'?'number of unresolved evidence criteria':'provisional source-verified / applicable criterion percentage'}.
    </p>
    <div style={{overflowX:'auto',maxWidth:'100%'}}>
     <svg role="img" aria-label="Six independent evidence numeric series with individual best-fit lines, plus a separate categorical FDA prediction direction lane"
      viewBox={'0 0 '+width+' '+height} width={width} height={height} style={{display:'block',background:'#fbfdfc',borderRadius:8}}>
      <title>L1–L6 saved evidence scores, with categorical FDA direction</title>
      <desc>Six independent evidence series and fits where reports exist, plus categorical FDA direction. The latter is ABSTAIN rather than a numeric approval probability. Trial order is alphabetical, not time.</desc>
      {[0,1,2,3,4].map(i=>{
       const value=ceiling*i/4;
       return <g key={i}>
        <line x1={left} y1={yAt(value)} x2={right} y2={yAt(value)} stroke="#d7e0df" strokeWidth={1}/>
        <text x={left-10} y={yAt(value)+4} textAnchor="end" fill="#40565b" fontSize={12}>
         {metric==='UNRESOLVED'?Number.isInteger(value)?value:value.toFixed(1):value+'%'}
        </text>
       </g>;
      })}
      <line x1={left} x2={right} y1={bottom} y2={bottom} stroke="#687c83" strokeWidth={1.5}/>
      <line x1={left} x2={left} y1={top} y2={bottom} stroke="#687c83" strokeWidth={1.5}/>
      {ordered.map((trial,i)=><g key={trial.nct}>
       <line x1={xAt(i)} x2={xAt(i)} y1={bottom} y2={bottom+5} stroke="#768b8c"/>
       <text transform={'translate('+xAt(i)+' '+(bottom+12)+') rotate(63)'} fill={trial.nct===selectedNct?'#145a80':'#4c6468'}
         fontSize={11} fontWeight={trial.nct===selectedNct?800:400}>{trial.ticker+' · '+trial.nct.slice(-4)}</text>
      </g>)}
      {activeSeries.map(({level,values,points})=>{
       const segments:{x:number;y:number}[][]=[];
       let current:{x:number;y:number}[]=[];
       for(let i=0;i<values.length;i++){
        if(values[i].value===null){if(current.length)segments.push(current);current=[];}
        else current.push({x:i,y:values[i].value!});
       }
       if(current.length)segments.push(current);
       const regression=leastSquaresFit(points);
       const start=points[0],end=points[points.length-1];
       const trend=regression&&start&&end?{
        x1:xAt(start.x),y1:yAt(regression.intercept+regression.slope*start.x),
        x2:xAt(end.x),y2:yAt(regression.intercept+regression.slope*end.x)}:null;
       return <g key={level.number} data-survey-level={'L'+level.number}>
        {segments.filter(v=>v.length>=2).map((seg,i)=><polyline key={i} points={seg.map(p=>xAt(p.x)+','+yAt(p.y)).join(' ')}
          fill="none" stroke={level.color} strokeWidth={2.4} strokeLinejoin="round" strokeLinecap="round"/>)}
        {showTrend&&trend&&<line data-testid={'survey-fit-level-'+level.number}
          x1={trend.x1} y1={trend.y1} x2={trend.x2} y2={trend.y2} stroke={level.color}
          strokeWidth={2.7} strokeDasharray="9 6" opacity={0.75}/>}
        {points.map(p=>{
         const d=values[p.x],chosen=d.trial.nct===selectedNct;
         return <circle key={d.trial.nct} cx={xAt(p.x)} cy={yAt(p.y)} r={chosen?5.5:3.3}
          fill={level.color} stroke="#fff" strokeWidth={chosen?1.5:0.8}>
          <title>{d.trial.ticker+' · '+d.trial.nct+' · Level '+level.number+
           ' · '+textValue(p.y)+' · saved '+(d.at||'unknown')}</title>
         </circle>;
        })}
       </g>;
      })}
      {showDirection&&<g data-testid="survey-direction-series">
        <rect x={left-15} y={505} width={right-left+30} height={32} rx={6} fill="#eef1f3"/>
        <text x={left-18} y={497} textAnchor="start" fill="#344d57" fontSize={13} fontWeight="bold">
         FDA direction · categorical (not a probability)
        </text>
        {ordered.map((trial,i)=>{
         const direction=focusSurveyDirection(trial);
         return direction==='ABSTAIN'?<g key={trial.nct} data-testid="survey-direction-abstain">
           <circle cx={xAt(i)} cy={521} r={7} fill="#65737e"/>
           <text x={xAt(i)} y={524} textAnchor="middle" fontSize={9} fill="#fff">A</text>
           <title>{trial.ticker+' · '+trial.nct+' · ABSTAIN · no validated FDA forecast'}</title>
          </g>:null;
        })}
       </g>}
      <text x={(left+right)/2} y={height-11} textAnchor="middle" fill="#354f58" fontSize={13}>
       Alphabetically sorted FOCUS trials · numeric scores are evidence only; A = ABSTAIN
      </text>
     </svg>
    </div>
    <div style={{display:'flex',gap:18,flexWrap:'wrap',marginTop:10,fontSize:12}}>
     {validSeries.map(s=><span key={s.level.number} style={{color:s.level.color,fontWeight:650}}>
      {s.level.name}: {s.points.length}/{ordered.length} observed trials
      {showTrend&&s.points.length>=2?' · separate dashed fit':''}
     </span>)}
    </div>
    <div style={{overflowX:'auto',marginTop:14}}>
     <table data-testid="survey-overall-prediction-data-table"
      style={{borderCollapse:'collapse',minWidth:1050,width:'100%',fontSize:12}}>
      <thead><tr>
       <th scope="col">Trial</th><th scope="col">L1 evidence /100</th>
       <th scope="col">L2 evidence /100</th><th scope="col">L3 evidence /100</th>
       <th scope="col">L4 evidence /100</th><th scope="col">L5 evidence /100</th><th scope="col">L6 evidence /100</th>
       <th scope="col">Overall evidence /100</th><th scope="col">FDA direction</th>
       <th scope="col">FDA approval probability</th>
      </tr></thead>
      <tbody>{ordered.map(t=>{
       const values=[1,2,3,4,5,6].map(l=>focusSurveyDatum(t,l,'VERIFIED_PERCENT').value);
       const overall=focusSurveyOverallDatum(t,'VERIFIED_PERCENT').value;
       const direction=focusSurveyDirection(t);
       return <tr key={t.nct} style={{borderTop:'1px solid #dce5e0',
         background:t.nct===selectedNct?'#ecf5ff':undefined}}>
        <th scope="row" style={{textAlign:'left',padding:6}}>
         {t.ticker} · {t.nct}
        </th>
        {values.map((v,i)=><td key={i} style={{padding:6}}>{v===null?'—':v}</td>)}
        <td data-testid="survey-overall-score" style={{padding:6,fontWeight:700}}>
         {overall===null?'NOT AVAILABLE':overall}
        </td>
        <td data-testid="survey-prediction-direction" style={{padding:6}}>
         {direction}
        </td>
        <td style={{padding:6}}>NOT VALIDATED</td>
       </tr>;
      })}</tbody>
     </table>
    </div>
    <p style={{fontSize:12,margin:'9px 0 0',color:'#465d60'}}>
     {metric==='UNRESOLVED'?'Lower counts represent fewer unresolved documentary criteria, not FDA outcomes.':
      'L1–L3 provisional readiness and L4–L6 level-specific evidence coverage are separate methods. No approval probability is computed.'}
     {' '}Missing reports remain gaps; an absent survey is never assigned a zero.
     Chronological improvement requires multiple dated assessment versions for the same trials.
    </p>
   </>}
 </section>;
}
