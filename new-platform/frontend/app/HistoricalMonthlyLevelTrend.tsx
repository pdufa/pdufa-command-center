import data from "../data/historicalMonthlyLevelRuns2026.json";

type BenchmarkCase = {id:string;ticker:string;actualDecision:string};
type Cohort = {
  cohortId:string;yearMonth:string;monthLabel:string;color:string;
  cohortSelection:string;sourceUrl:string;sourceBlobSha:string;
  sourceListedCount:number;benchmarkCaseIds:string[];benchmarkCases:BenchmarkCase[];
  excludedCases:{id:string;ticker:string;originalCall:string;reason:string}[];
  alwaysApproveMatches:number;
};
type LevelRun = {
  runId:string;cohortId:string;assessmentLevel:number;assessmentType:string;
  runDate:string;assessmentBlind:boolean;priorOutcomeExposure:boolean;
  validatedBlindCases:number;validatedBlindAccuracy:null;
  comparisonType:string;predictionFreezeUrl:string;comparisonSourceUrl:string;
  caseCalls:{caseId:string;call:string}[];
};
type Point = {cohort:Cohort;run:LevelRun;level:number;matches:number;misses:number;
  denominator:number;abstentions:number;rate:number;coverage:number;baselineRate:number};
const months=data.cohorts as Cohort[];
const runs=data.runs as LevelRun[];
const ink="#23463f", muted="#5e706c";
const W=860,H=320,L=62,R=31,T=46,B=70;

function percent(n:number,d:number){return (100*n/d).toFixed(1)+"%";}

/**
 * Historical-only display. Case IDs/denominators are locked by cohort so that
 * Level 4+ reruns can be overlaid without overwriting the Level 3 archive.
 */
export default function HistoricalMonthlyLevelTrend(){
  if(data.schemaVersion!==1||data.dataset!=="HISTORICAL_MONTHLY_LEVEL_COMPARISONS_2026_V1"||
    data.methodGuardrails.notLiveAccuracy!==true||
    data.methodGuardrails.validatedBlindPredictionCount!==0||
    data.methodGuardrails.validBlindAccuracy!==null||
    data.methodGuardrails.originalOutcomesWereKnownBeforeRetrospectiveCalls!==true||
    data.methodGuardrails.cohortsNotPopulationComparable!==true||
    months.length!==5||new Set(months.map(c=>c.cohortId)).size!==months.length){
    throw new Error("HISTORICAL_MONTHLY_LEVEL_TREND_QUARANTINE_MISMATCH");
  }
  const byKey=new Map<string,Point>();
  for(const cohort of months){
    if(!/^#[0-9a-f]{6}$/i.test(cohort.color)||!cohort.sourceUrl.startsWith("https://")||
      !cohort.sourceBlobSha||cohort.sourceListedCount!==
      cohort.benchmarkCases.length+cohort.excludedCases.length||
      cohort.benchmarkCases.length!==cohort.benchmarkCaseIds.length||
      new Set(cohort.benchmarkCaseIds).size!==cohort.benchmarkCaseIds.length||
      cohort.benchmarkCases.some((c,i)=>c.id!==cohort.benchmarkCaseIds[i]||
        !["APPROVAL","CRL"].includes(c.actualDecision))||
      cohort.alwaysApproveMatches!==cohort.benchmarkCases.filter(c=>c.actualDecision==="APPROVAL").length){
      throw new Error("INVALID_FROZEN_HISTORICAL_MONTH_COHORT_"+cohort.yearMonth);
    }
  }
  for(const run of runs){
    const cohort=months.find(c=>c.cohortId===run.cohortId);
    if(!cohort||run.assessmentBlind!==false||run.priorOutcomeExposure!==true||
      run.validatedBlindCases!==0||run.validatedBlindAccuracy!==null||
      run.assessmentLevel<1||run.assessmentLevel>20||
      run.comparisonType!=="RETROSPECTIVE_DIRECTIONAL_AGREEMENT_ONLY"||
      run.caseCalls.length!==cohort.benchmarkCaseIds.length||
      !run.predictionFreezeUrl.startsWith("https://")||
      !run.comparisonSourceUrl.startsWith("https://")){
      throw new Error("HISTORICAL_LEVEL_RUN_INVALID_"+run.runId);
    }
    const found=new Set(run.caseCalls.map(c=>c.caseId));
    if(found.size!==run.caseCalls.length||cohort.benchmarkCaseIds.some(id=>!found.has(id))||
      run.caseCalls.some(c=>!["APPROVAL","CRL","ABSTAIN"].includes(c.call))){
      throw new Error("HISTORICAL_LEVEL_RUN_MUST_USE_FIXED_CASE_IDS_"+run.runId);
    }
    const key=run.cohortId+"|"+run.assessmentLevel;
    if(byKey.has(key)){
      throw new Error("DUPLICATE_MONTH_AND_LEVEL_RUN_"+key);
    }
    const caseById=new Map(cohort.benchmarkCases.map(c=>[c.id,c.actualDecision]));
    const matches=run.caseCalls.filter(c=>c.call!=="ABSTAIN"&&c.call===caseById.get(c.caseId)).length;
    const abstentions=run.caseCalls.filter(c=>c.call==="ABSTAIN").length;
    const denominator=cohort.benchmarkCaseIds.length;
    byKey.set(key,{cohort,run,level:run.assessmentLevel,matches,
      misses:denominator-matches-abstentions,denominator,abstentions,
      rate:100*matches/denominator,coverage:(denominator-abstentions)/denominator,
      baselineRate:100*cohort.alwaysApproveMatches/denominator});
  }
  const levels=Array.from(new Set(runs.map(r=>r.assessmentLevel))).sort((a,b)=>a-b);
  const series=levels.map(level=>({level,points:months.map(c=>byKey.get(c.cohortId+"|"+level)??null)}));
  const allPoints=series.flatMap(s=>s.points.filter((p):p is Point=>p!==null));
  if(allPoints.length!==runs.length)throw new Error("INVALID_MONTHLY_LEVEL_POINT_COUNT");
  const allRates=allPoints.flatMap(p=>[p.rate,p.baselineRate]);
  const minRate=Math.min(...allRates),minY=Math.max(0,Math.floor((minRate-8)/10)*10);
  const ticks=Array.from({length:Math.round((100-minY)/10)+1},(_,i)=>minY+i*10);
  const x=(index:number)=>L+index*(W-L-R)/(months.length-1);
  const y=(rate:number)=>T+(100-rate)*(H-T-B)/(100-minY);
  const levelDash=(index:number)=>index===0?undefined:index%2===1?"9 5":"3 5";
  return <section data-testid="historical-monthly-level-trend"
    aria-label="June through October historical FDA retrospective Level 3 comparison trend"
    style={{background:"#fff",border:"1px solid #c3d8d1",borderRadius:14,
      padding:"clamp(14px,2vw,22px)",margin:"0 0 22px",color:ink}}>
    <div style={{fontSize:11,fontWeight:850,letterSpacing:".09em",color:"#28685e"}}>
      HISTORICAL COMPARISONS · LEVEL-LOCKED BENCHMARK
    </div>
    <h2 style={{fontSize:22,margin:"8px 0 4px"}}>Monthly FDA assessment trend · June–October 2026</h2>
    <p style={{fontSize:13,color:muted,lineHeight:1.55,margin:"6px 0 13px"}}>
      Each month has its own color. The line connects case-level <strong>retrospective directional match rates</strong>
      for the indicated assessment level; this is not blind prediction accuracy.
      The exact case population is frozen for comparisons when the assessment level rises.
    </p>
    <div style={{display:"flex",gap:8,flexWrap:"wrap",marginBottom:12}}>
      {levels.map((level,i)=><span key={level} data-testid={"historical-level-tag-"+level}
        style={{display:"inline-flex",alignItems:"center",gap:8,
          padding:"6px 11px",fontSize:12,fontWeight:800,
          border:"1px solid #bfd2cb",borderRadius:8,background:"#f5faf7"}}>
        <svg width="27" height="8" viewBox="0 0 27 8" aria-hidden="true">
          <line x1="0" y1="4" x2="27" y2="4" stroke="#304c50"
            strokeWidth="3" strokeDasharray={levelDash(i)}/>
        </svg>
        Assessment Level {level} · manual research
      </span>)}
      <span style={{padding:"6px 11px",fontSize:12,color:"#895d25",fontWeight:800,
        background:"#fff7e9",borderRadius:8}}>Blind accuracy: N/A</span>
    </div>
    <div style={{display:"flex",gap:12,flexWrap:"wrap",margin:"9px 0 5px"}}>
      {months.map(c=><div key={c.cohortId} data-testid={"month-color-"+c.yearMonth}
        style={{display:"inline-flex",alignItems:"center",gap:6,fontSize:12,fontWeight:750}}>
        <span aria-hidden="true" style={{width:12,height:12,borderRadius:"50%",background:c.color}}/>
        {c.monthLabel}
      </div>)}
    </div>
    <div style={{overflowX:"auto",background:"#f9fbfa",borderRadius:10,padding:"10px 5px"}}>
      <svg data-testid="historical-monthly-level-line-chart" role="img"
        aria-label={series.map(s=>"Level "+s.level+": "+s.points.map(p=>p?
          p.cohort.monthLabel+" "+percent(p.matches,p.denominator):"not assessed").join(", ")).join("; ")+
          ". June through October month colors are distinct. Not blind."}
        viewBox={"0 0 "+W+" "+H} style={{display:"block",width:"100%",minWidth:540,height:"auto"}}>
        {ticks.map(t=><g key={t}>
          <line x1={L} x2={W-R} y1={y(t)} y2={y(t)} stroke="#dce8e3" strokeWidth="1"/>
          <text x={L-11} y={y(t)+4} textAnchor="end" fill="#647c75" fontSize="13">{t}%</text>
        </g>)}
        {series.map((s,levelIndex)=><g key={s.level} data-testid={"level-line-"+s.level}>
          {s.points.slice(0,-1).map((point,index)=>{
            const next=s.points[index+1];
            return point&&next?<line key={index} x1={x(index)} y1={y(point.rate)}
              x2={x(index+1)} y2={y(next.rate)}
              stroke={months[index].color} strokeWidth={levelIndex===0?3:2.5}
              strokeDasharray={levelDash(levelIndex)} opacity={levelIndex===0?1:.8}/>:null;
          })}
          {s.points.map((point,index)=>point?<g key={point.cohort.cohortId}>
            <circle cx={x(index)} cy={y(point.rate)} r={levelIndex===0?9:6}
              fill={point.cohort.color} stroke={levelIndex===0?"#fff":"#304c50"}
              strokeWidth={levelIndex===0?3:2}>
              <title>{point.cohort.monthLabel+" · Level "+s.level+" · "+
                percent(point.matches,point.denominator)+" ("+
                point.matches+"/"+point.denominator+"). Nonblind retrospective agreement."}</title>
            </circle>
            {levelIndex===0?<text x={x(index)} y={y(point.rate)-16}
              fontSize="15" fontWeight="800" textAnchor="middle" fill="#253f3b">
              {percent(point.matches,point.denominator)}
            </text>:null}
          </g>:null)}
        </g>)}
        {months.map((c,index)=><g key={c.cohortId}>
          <text x={x(index)} y={H-B+28} textAnchor="middle" fontSize="15"
            fontWeight="800" fill={c.color}>{c.monthLabel}</text>
          <text x={x(index)} y={H-B+45} textAnchor="middle"
            fontSize="11" fill="#62756e">2026</text>
        </g>)}
      </svg>
    </div>
    <p style={{fontSize:11,lineHeight:1.5,color:muted,margin:"7px 0 12px"}}>
      Y-axis: matched cases / locked cases (%); it adjusts to display the recorded levels.
      Future levels appear as additional dashed or dotted lines; month colors remain fixed.
      Abstentions on a later level cannot artificially increase its fixed-cohort match rate.
    </p>
    <div style={{overflowX:"auto",border:"1px solid #e0e9e5",borderRadius:9}}>
      <table data-testid="historical-monthly-level-table"
        style={{borderCollapse:"collapse",width:"100%",minWidth:730,fontSize:12}}>
        <thead><tr style={{background:"#edf5f0",textAlign:"left"}}>
          {["Month","Assessment level","Matched","Missed","Rate","Always approve baseline","Method / sources"].map(h=>
            <th key={h} scope="col" style={{padding:"10px 9px",borderBottom:"1px solid #d6e4dc"}}>{h}</th>)}
        </tr></thead>
        <tbody>{allPoints.map((p,i)=><tr key={p.run.runId} style={{background:i%2?"#f9fcfa":"#fff"}}>
          <td style={{padding:9,fontWeight:850,color:p.cohort.color}}>
            {p.cohort.monthLabel} 2026</td>
          <td style={{padding:9}}>Level {p.level} · {p.run.assessmentType==="MANUAL_LEVEL3_STYLE_RECONSTRUCTION"?"manual":p.run.assessmentType}</td>
          <td style={{padding:9,fontWeight:800}}>{p.matches} / {p.denominator}</td>
          <td style={{padding:9}}>{p.misses}{p.abstentions?" · "+p.abstentions+" abstain":""}</td>
          <td style={{padding:9,fontWeight:850}}>{percent(p.matches,p.denominator)}</td>
          <td style={{padding:9}}>{percent(p.cohort.alwaysApproveMatches,p.denominator)}</td>
          <td style={{padding:9,whiteSpace:"nowrap"}}>
            <a href={p.run.predictionFreezeUrl} target="_blank" rel="noopener noreferrer"
              style={{color:"#086f62"}}>Assessment</a>{" · "}
            <a href={p.cohort.sourceUrl} target="_blank" rel="noopener noreferrer"
              style={{color:"#086f62"}}>FDA comparison</a>
          </td>
        </tr>)}</tbody>
      </table>
    </div>
    <details style={{marginTop:14,fontSize:12,color:muted,lineHeight:1.6}}>
      <summary style={{cursor:"pointer",fontWeight:750,color:"#295e55"}}>Locked case selection and how to repeat a level</summary>
      <p>
        The monthly sources cover different selected populations: June includes a May original goal,
        July excludes three actions already decided before July, August contains some cases with
        unverified August goals, September is an approvals-only action-date group, and October
        includes early decisions and a withdrawal. Month-to-month changes are not evidence that
        the engine became more or less accurate.
      </p>
      <p>
        To rerun at Level 4, Level 5, etc., append a new case-by-case run for the same
        <code>cohortId</code> and locked case IDs, record the assessment level and method version,
        and preserve all earlier runs. A new case roster requires a new cohort version.
        Previous FDA outcomes remain known; historical reruns remain nonblind.
      </p>
      {months.map(c=><p key={c.cohortId}>
        <strong style={{color:c.color}}>{c.monthLabel}:</strong> {c.cohortSelection}.
        {" "+c.benchmarkCaseIds.length+" locked directional cases; "+
        c.excludedCases.length+" excluded. "}
        <a href={c.sourceUrl} target="_blank" rel="noopener noreferrer">See source.</a>
      </p>)}
    </details>
    <p style={{fontSize:12,lineHeight:1.6,color:"#906426",fontWeight:750,margin:"12px 0 0"}}>
      INTEGRITY: All five Level 3 results were reconstructed after FDA outcomes became public.
      This chart cannot be used as calibrated prediction accuracy, a verified blind test,
      or a live FOCUS ranking signal.
    </p>
  </section>;
}
