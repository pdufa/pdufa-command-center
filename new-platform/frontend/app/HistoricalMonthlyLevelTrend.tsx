"use client";

import {useState} from "react";
import data from "../data/historicalMonthlyLevelRuns2026.json";
import {bestFitTrend} from "../lib/assessment-best-fit-trend";

type Case = {id:string;ticker:string;actualDecision:"APPROVAL"|"CRL"};
type Cohort = {
  cohortId:string;yearMonth:string;monthLabel:string;color:string;cohortSelection:string;
  sourceUrl:string;sourceBlobSha:string;sourceListedCount:number;
  benchmarkCaseIds:string[];benchmarkCases:Case[];
  excludedCases:{id:string;ticker:string;originalCall:string;reason:string}[];
  alwaysApproveMatches:number;
};
type Run = {
  runId:string;cohortId:string;assessmentLevel:number;assessmentType:string;
  methodVersion:string;runDate:string;assessmentBlind:boolean;priorOutcomeExposure:boolean;
  validatedBlindCases:number;validatedBlindAccuracy:null;
  comparisonType:string;predictionFreezeUrl:string;comparisonSourceUrl:string;
  caseCalls:{caseId:string;call:"APPROVAL"|"CRL"|"ABSTAIN"}[];
  revisionNumber?:number;
};
type MonthScore = {
  cohort:Cohort;run:Run;matches:number;misses:number;abstains:number;total:number;
  monthlyRate:number;cumulativeMatches:number;cumulativeTotal:number;cumulativeRate:number;
};
type Series = {level:number;months:(MonthScore|null)[];total:number;matches:number;misses:number;abstains:number;covered:number};
const cohorts=data.cohorts as Cohort[];
const runs=data.runs as Run[];
const W=960,H=340,L=64,R=26,T=40,B=67;
const muted="#5b716a",dark="#1e4c44";
function rate(n:number,d:number){return d?(n/d*100).toFixed(1)+"%":"N/A";}
function selectedRun(first:Run,second:Run){
  const a=first.revisionNumber??1,b=second.revisionNumber??1;
  return b>a||(a===b&&second.runDate>first.runDate)?second:first;
}

/** Snapshot data is compiled from outcome-exposed manual research, NOT blind FDA forecasts.
 * Display is selected-level dependent; exact FDA benchmark case identities never change.
 */
export default function HistoricalMonthlyLevelTrend({compact=false}:{compact?:boolean}){
  const [choice,setChoice]=useState("3");
  const [yearChoice,setYearChoice]=useState("2026");
  if(data.schemaVersion!==2||
    data.dataset!=="HISTORICAL_MONTHLY_LEVEL_COMPARISONS_2026_V2"||
    data.methodGuardrails.notLiveAccuracy!==true||
    data.methodGuardrails.validatedBlindPredictionCount!==0||
    data.methodGuardrails.validBlindAccuracy!==null||
    data.methodGuardrails.cohortsNotPopulationComparable!==true||
    data.methodGuardrails.doNotPromoteHistoricalToLiveAccuracy!==true||
    cohorts.length<10||new Set(cohorts.map(c=>c.cohortId)).size!==cohorts.length||
    new Set(cohorts.map(c=>c.yearMonth)).size!==cohorts.length||
    cohorts.slice(0,10).some((c,i)=>c.yearMonth!=="2026-"+String(i+1).padStart(2,"0"))||
    cohorts.some((c,i)=>!/^20\d{2}-(0[1-9]|1[0-2])$/.test(c.yearMonth)||
      (i>0&&cohorts[i-1].yearMonth>=c.yearMonth))){
    throw new Error("HISTORICAL_TEN_MONTH_LEVEL_BENCHMARK_INVALID");
  }
  const seenRunIds=new Set<string>();
  const byLevel=new Map<number,Map<string,Run>>();
  for(const c of cohorts){
    if(!/^#[0-9a-f]{6}$/i.test(c.color)||!c.sourceUrl.startsWith("https://")||
      !c.sourceBlobSha||c.sourceListedCount!==c.benchmarkCases.length+c.excludedCases.length||
      c.benchmarkCaseIds.length!==c.benchmarkCases.length||
      new Set(c.benchmarkCaseIds).size!==c.benchmarkCaseIds.length||
      c.benchmarkCases.some((x,i)=>x.id!==c.benchmarkCaseIds[i]||
        !["APPROVAL","CRL"].includes(x.actualDecision))||
      c.alwaysApproveMatches!==c.benchmarkCases.filter(x=>x.actualDecision==="APPROVAL").length){
      throw new Error("HISTORICAL_BENCHMARK_COHORT_INVALID_"+c.yearMonth);
    }
  }
  for(const run of runs){
    const c=cohorts.find(x=>x.cohortId===run.cohortId);
    if(!c||seenRunIds.has(run.runId)||
      !Number.isInteger(run.assessmentLevel)||run.assessmentLevel<1||run.assessmentLevel>20||
      !run.methodVersion||!run.runDate||run.assessmentBlind!==false||
      run.priorOutcomeExposure!==true||run.validatedBlindCases!==0||
      run.validatedBlindAccuracy!==null||
      run.comparisonType!=="RETROSPECTIVE_DIRECTIONAL_AGREEMENT_ONLY"||
      !run.predictionFreezeUrl.startsWith("https://")||
      !run.comparisonSourceUrl.startsWith("https://")||
      run.caseCalls.length!==c.benchmarkCaseIds.length||
      (run.revisionNumber!==undefined&&(!Number.isInteger(run.revisionNumber)||run.revisionNumber<1))){
      throw new Error("HISTORICAL_ASSESSMENT_LEVEL_RUN_INVALID_"+run.runId);
    }
    seenRunIds.add(run.runId);
    const ids=new Set(run.caseCalls.map(x=>x.caseId));
    if(ids.size!==run.caseCalls.length||c.benchmarkCaseIds.some(id=>!ids.has(id))||
      run.caseCalls.some(x=>!["APPROVAL","CRL","ABSTAIN"].includes(x.call))){
      throw new Error("HISTORICAL_LEVEL_RUN_MUST_USE_FIXED_CASE_IDS_"+run.runId);
    }
    const group=byLevel.get(run.assessmentLevel)??new Map<string,Run>();
    const previous=group.get(run.cohortId);
    group.set(run.cohortId,previous?selectedRun(previous,run):run);
    byLevel.set(run.assessmentLevel,group);
  }
  const levels=[...byLevel.keys()].sort((a,b)=>a-b);
  if(!levels.includes(3))throw new Error("LEVEL_3_BASELINE_MISSING");
  // Only list years with actual case-level assessment runs. Switching years
  // resets the trend and denominators rather than joining unrelated years.
  const years=[...new Set(runs.map(r=>cohorts.find(c=>c.cohortId===r.cohortId)!.yearMonth.slice(0,4)))]
    .sort((a,b)=>b.localeCompare(a));
  const activeYear=years.includes(yearChoice)?yearChoice:years[0];
  const yearCohorts=cohorts.filter(c=>c.yearMonth.startsWith(activeYear+"-"));
  if(new Set(yearCohorts.map(c=>c.color.toLowerCase())).size!==yearCohorts.length){
    throw new Error("DUPLICATE_COLORS_WITHIN_PDUFA_YEAR_"+activeYear);
  }
  const yearLevels=levels.filter(level=>yearCohorts.some(c=>byLevel.get(level)?.has(c.cohortId)));
  if(!yearLevels.length)throw new Error("PDUFA_YEAR_HAS_NO_RECORDED_LEVELS_"+activeYear);
  const visibleChoice=choice==="all"?"all":
    yearLevels.includes(Number(choice))?choice:String(yearLevels[0]);
  const selectedLevels=visibleChoice==="all"?yearLevels:
    yearLevels.filter(l=>String(l)===visibleChoice);
  const series:Series[]=selectedLevels.map(level=>{
    let total=0,matches=0,misses=0,abstains=0,covered=0;
    const months=yearCohorts.map(cohort=>{
      const run=byLevel.get(level)?.get(cohort.cohortId);
      if(!run)return null;
      const actual=new Map(cohort.benchmarkCases.map(x=>[x.id,x.actualDecision]));
      const correct=run.caseCalls.filter(x=>x.call!=="ABSTAIN"&&x.call===actual.get(x.caseId)).length;
      const absent=run.caseCalls.filter(x=>x.call==="ABSTAIN").length;
      const n=cohort.benchmarkCaseIds.length;
      total+=n;matches+=correct;misses+=n-correct-absent;abstains+=absent;covered++;
      return {cohort,run,matches:correct,misses:n-correct-absent,abstains:absent,total:n,
        monthlyRate:100*correct/n,cumulativeMatches:matches,cumulativeTotal:total,
        cumulativeRate:100*matches/total};
    });
    return {level,months,total,matches,misses,abstains,covered};
  });
  const graphPoints=series.flatMap(s=>s.months.filter((v):v is MonthScore=>v!==null));
  // A true least-squares trend uses observed cumulative monthly values; dots remain
  // the actual values, without a zig-zag line joining them.
  const bestFits=series.map(s=>bestFitTrend(s.months.flatMap((point,index)=>
    point?[{x:index,y:point.cumulativeRate}]:[])));
  const minCumulative=Math.min(
    ...graphPoints.map(x=>x.cumulativeRate),
    ...bestFits.flatMap(f=>f?[f.yStart,f.yEnd]:[])
  );
  const bottom=Math.max(0,Math.floor((minCumulative-5)/10)*10);
  const ticks=Array.from({length:Math.round((100-bottom)/10)+1},(_,i)=>bottom+i*10);
  const px=(i:number)=>yearCohorts.length===1?(L+W-R)/2:
    L+i*(W-L-R)/(yearCohorts.length-1);
  const py=(v:number)=>T+(100-Math.max(bottom,Math.min(100,v)))*(H-T-B)/(100-bottom);
  // Mobile chart uses a dedicated small viewport, not a clipped 650px desktop SVG.
  const MW=360,MH=244,ML=34,MR=10,MT=26,MB=47;
  const mx=(i:number)=>yearCohorts.length===1?(ML+MW-MR)/2:
    ML+i*(MW-ML-MR)/(yearCohorts.length-1);
  const my=(v:number)=>MT+(100-Math.max(bottom,Math.min(100,v)))*(MH-MT-MB)/(100-bottom);
  const lines=["#168267","#415F9D","#9C4B8E","#B07813"];
  const lineColor=(i:number)=>lines[i%lines.length];
  const panel={border:"1px solid #d7d5ea",borderRadius:11,background:"#f8f7ff",padding:"13px 15px"} as const;
  return <section id="historical-performance" data-testid="historical-monthly-level-trend"
    aria-label={"Level-dependent historical FDA assessment dashboard for PDUFA year "+activeYear}
    style={{border:"1px solid #c7bddf",borderRadius:14,background:"#fff",
      padding:"clamp(14px,2vw,22px)",margin:"0 0 22px",color:dark}}>
    <div style={{background:"#4a277f",color:"#fff",borderRadius:9,padding:"11px 14px",
      fontSize:15,fontWeight:850}}>◴ OLD PREDICTIONS · HISTORICAL LEVEL COMPARISONS</div>
    {compact?<p style={{fontSize:13,color:"#304e47",margin:"9px 0 4px"}}>
      <strong>Historical trend — {visibleChoice==="all"?"all recorded levels":"Level "+visibleChoice}
      {" · PDUFA "+activeYear}:</strong>{" "}
      {visibleChoice==="all"?"Compare recorded historical levels.":
        series[0].matches+" of "+series[0].total+" retrospective matches ("+
        rate(series[0].matches,series[0].total)+")."}
      {" "}The straight best-fit line summarizes cumulative agreement; the colored dots are observed monthly values. Not verified blind accuracy.
    </p>:null}
    {!compact?<p style={{color:muted,fontSize:13,lineHeight:1.6}}>
      Outcome-aware Level 3-style research reconstructed after FDA decisions, not genuine blind accuracy.
      The assessment level and PDUFA year selectors update every historical metric; live forecasts are separate.
    </p>:null}
    <div style={{display:"flex",flexWrap:"wrap",alignItems:"end",gap:14,margin:"14px 0"}}>
      <div data-testid="historical-level-year-controls"
        style={{display:"grid",gridTemplateColumns:"minmax(0,1.35fr) minmax(0,1fr)",
          alignItems:"end",gap:10,width:"min(100%,570px)"}}>
      <div style={{display:"grid",gap:5,minWidth:0}}>
        <label htmlFor="historical-assessment-level-select"
          style={{fontSize:13,fontWeight:850}}>Assessment Level</label>
        <select id="historical-assessment-level-select"
          data-testid="historical-assessment-level-dropdown"
          value={visibleChoice} onChange={e=>setChoice(e.currentTarget.value)}
          style={{background:"#fff",color:dark,border:"1px solid #a8b7b3",
            borderRadius:8,fontWeight:750,fontSize:15,padding:"11px",minHeight:44,
            width:"100%",minWidth:0}}>
          {Array.from({length:data.methodGuardrails.maxResearchLevel},(_,i)=>i+1).map(level=>
            <option key={level} value={String(level)} disabled={!yearLevels.includes(level)}>
              {"Level "+level+(yearLevels.includes(level)?" — recorded":" — not assessed")}
            </option>)}
          <option value="all">Compare all recorded levels</option>
        </select>
      </div>
      <div style={{display:"grid",gap:5,minWidth:0}}>
        <label htmlFor="historical-pdufa-year-select"
          style={{fontSize:13,fontWeight:850}}>PDUFA Year</label>
        <select id="historical-pdufa-year-select"
          data-testid="historical-pdufa-year-dropdown"
          value={activeYear} onChange={e=>setYearChoice(e.currentTarget.value)}
          style={{background:"#fff",color:dark,border:"1px solid #a8b7b3",
            borderRadius:8,fontWeight:750,fontSize:15,padding:"11px",minHeight:44,
            width:"100%",minWidth:0}}>
          {years.map(year=><option key={year} value={year}>{year}</option>)}
        </select>
      </div>
      </div>
      <p data-testid="historical-selected-level-status" role="status" aria-live="polite"
        style={{fontSize:12,color:muted,maxWidth:600,lineHeight:1.5,margin:0}}>
        {visibleChoice==="all"?"Comparing all recorded levels for PDUFA "+activeYear+".":
          "Displaying Level "+visibleChoice+" results for PDUFA "+activeYear+"."}
        {" "}Only years and levels with saved case assessments appear.
        {" "}Future runs must retain the same case IDs for each month.
      </p>
    </div>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(150px,1fr))",gap:10,
      margin:"12px 0 16px"}}>
      {series.map(s=><div key={s.level} data-testid={"historical-level-summary-"+s.level}
        style={panel}>
        <div style={{color:"#5e4c81",fontSize:11,fontWeight:850}}>LEVEL {s.level} · RETROSPECTIVE</div>
        <strong data-testid={"historical-level-rate-"+s.level}
          style={{fontSize:27,color:"#4d2788",display:"block",margin:"3px 0"}}>
          {rate(s.matches,s.total)}
        </strong>
        <div style={{fontWeight:750,fontSize:13}}>{s.matches} / {s.total} matched</div>
        <div style={{color:muted,fontSize:12,marginTop:5}}>
          {s.misses} missed · {s.abstains} abstained<br/>
          {s.covered} / {yearCohorts.length} months assessed
        </div>
      </div>)}
      <div style={{...panel,background:"#f6faf8",borderColor:"#cbded4"}}>
        <div style={{fontSize:11,fontWeight:850,color:"#286657"}}>VERIFIED BLIND ACCURACY</div>
        <strong style={{fontSize:27,display:"block",margin:"3px 0"}}>N/A</strong>
        <div style={{fontSize:12,color:muted}}>Historical runs cannot validate prospective accuracy</div>
      </div>
    </div>
    <h2 style={{fontSize:20,margin:"12px 0 6px"}}>
      Best-fit trend of cumulative FDA agreement · {yearCohorts[0].monthLabel.slice(0,3)}
      {"–"}{yearCohorts.at(-1)!.monthLabel.slice(0,3)} {activeYear}
    </h2>
    <p data-testid="historical-trend-key" style={{fontSize:13,fontWeight:800,color:"#096C56",margin:"4px 0 8px"}}>
      <span aria-hidden="true" style={{display:"inline-block",width:35,height:5,
        borderRadius:4,verticalAlign:"middle",background:"#096C56",marginRight:7}}/>
      Solid green line = least-squares best-fit trend; colored dots = recorded cumulative results
    </p>
    <p style={{fontSize:12,color:muted,lineHeight:1.5,margin:"0 0 12px"}}>
      Dots show cumulative agreement across all scored applications up to each month.
      The straight line is a least-squares summary of those cumulative values,
      not connected monthly points or a forecast of future FDA prediction accuracy.
    </p>
    {!compact?<div style={{display:"flex",gap:12,flexWrap:"wrap",marginBottom:10}}>
      {yearCohorts.map(cohort=><div key={cohort.cohortId}
        data-testid={"month-color-"+cohort.yearMonth}
        style={{display:"flex",alignItems:"center",gap:6,fontSize:12,color:dark}}>
        <span style={{width:11,height:11,borderRadius:"50%",background:cohort.color}}/>
        {cohort.monthLabel}
      </div>)}
    </div>:null}
    <div style={{display:"flex",gap:14,flexWrap:"wrap",marginBottom:8}}>
      {series.map((s,i)=><div key={s.level}
        data-testid={"historical-level-tag-"+s.level}
        style={{display:"flex",gap:6,alignItems:"center",fontSize:12,fontWeight:750}}>
        <svg width="28" height="9" viewBox="0 0 28 9" aria-hidden="true">
          <line x1="0" y1="4" x2="28" y2="4" stroke={lineColor(i)} strokeWidth="3"
            strokeDasharray={i===0?undefined:"7 4"}/>
        </svg>Level {s.level}
      </div>)}
    </div>
    <div className="historical-trend-desktop" style={{overflowX:"auto",background:"#f8faf9",borderRadius:10,padding:7}}>
      <svg data-testid="historical-monthly-level-line-chart" role="img"
        aria-label={"Case-weighted cumulative historical agreement trend: "+
          series.map(s=>"Level "+s.level+" "+rate(s.matches,s.total)+
          " across "+s.covered+" recorded months").join("; ")+". Not blind."}
        viewBox={"0 0 "+W+" "+H}
        style={{display:"block",width:"100%",height:"auto"}}>
        {ticks.map(t=><g key={t}>
          <line x1={L} y1={py(t)} x2={W-R} y2={py(t)} stroke="#dce7e0"/>
          <text x={L-12} y={py(t)+4} textAnchor="end" fontSize="13" fill="#5a6e66">{t}%</text>
        </g>)}
        {series.map((s,seriesIndex)=><g key={s.level} data-testid={"level-line-"+s.level}>
          {bestFits[seriesIndex]&&<line data-testid={"historical-best-fit-line-"+s.level}
            x1={px(bestFits[seriesIndex]!.xStart)} y1={py(bestFits[seriesIndex]!.yStart)}
            x2={px(bestFits[seriesIndex]!.xEnd)} y2={py(bestFits[seriesIndex]!.yEnd)}
            stroke={lineColor(seriesIndex)} strokeWidth={6} strokeLinecap="round"
            strokeDasharray={seriesIndex===0?undefined:"8 5"}>
            <title>{"Level "+s.level+": least-squares best-fit across "+
              bestFits[seriesIndex]!.observations+" observed cumulative monthly agreements."}</title>
          </line>}
          {s.months.map((point,index)=>point?<g key={point.cohort.cohortId}>
            <circle cx={px(index)} cy={py(point.cumulativeRate)} r="7"
              stroke={lineColor(seriesIndex)} strokeWidth="2" fill={point.cohort.color}>
              <title>{point.cohort.monthLabel+" Level "+s.level+
                " cumulative "+rate(point.cumulativeMatches,point.cumulativeTotal)+
                " ("+point.cumulativeMatches+"/"+point.cumulativeTotal+")."}</title>
            </circle>
            {visibleChoice!=="all"?<text x={px(index)} y={py(point.cumulativeRate)-16}
              fontSize="12" textAnchor="middle" fill={dark} fontWeight="800">
              {rate(point.cumulativeMatches,point.cumulativeTotal)}
            </text>:null}
          </g>:null)}
        </g>)}
        {yearCohorts.map((c,i)=><text key={c.cohortId} x={px(i)} y={H-B+27}
          textAnchor="middle" fill={c.color} fontWeight="800" fontSize="14">
          {c.monthLabel.slice(0,3)}
        </text>)}
      </svg>
    </div>
    <div className="historical-trend-mobile" data-testid="historical-trend-mobile-view"
      style={{display:"none",background:"#f8faf9",borderRadius:10,padding:"8px 2px"}}>
      <svg data-testid="historical-mobile-trend-line-chart" role="img"
        aria-label={"Mobile cumulative FDA historical agreement for PDUFA "+activeYear+". "+
          series.map(s=>"Level "+s.level+": "+rate(s.matches,s.total)).join("; ")+
          ". Not verified blind accuracy."}
        viewBox={"0 0 "+MW+" "+MH}
        style={{display:"block",width:"100%",maxWidth:520,height:"auto",margin:"0 auto"}}>
        {ticks.filter((_,i)=>i%2===0||i===ticks.length-1).map(t=><g key={t}>
          <line x1={ML} x2={MW-MR} y1={my(t)} y2={my(t)} stroke="#d8e5dc" strokeWidth="1"/>
          <text x={ML-5} y={my(t)+3} fill="#527167" fontSize="10" textAnchor="end">{t}%</text>
        </g>)}
        {series.map((s,i)=>{
          const plotted=s.months.flatMap((point,index)=>
            point?[{x:mx(index),y:my(point.cumulativeRate),index,point}]:[]);
          return <g key={s.level} data-testid={"mobile-level-line-"+s.level}>
            {bestFits[i]&&<line
              data-testid={"mobile-best-fit-line-"+s.level}
              x1={mx(bestFits[i]!.xStart)} y1={my(bestFits[i]!.yStart)}
              x2={mx(bestFits[i]!.xEnd)} y2={my(bestFits[i]!.yEnd)}
              stroke={lineColor(i)} strokeWidth="5"
              strokeLinecap="round" strokeDasharray={i>0?"8 5":undefined}>
              <title>{"Level "+s.level+" best-fit trend (not a forecast)."}</title>
            </line>}
            {plotted.map(pt=><circle key={pt.index} cx={pt.x} cy={pt.y} r="4.5"
              fill={pt.point.cohort.color} stroke="#fff" strokeWidth="1.5"/>)}
            {visibleChoice!=="all"&&plotted.length>0&&<g>
              <text x={Math.max(ML+17,plotted[0].x)}
                y={Math.min(MH-MB-12,plotted[0].y+21)}
                fontSize="11" fontWeight="800" textAnchor="start" fill="#155F50">
                {rate(plotted[0].point.cumulativeMatches,plotted[0].point.cumulativeTotal)}
              </text>
              <text x={Math.min(MW-17,plotted[plotted.length-1].x)}
                y={Math.max(16,plotted[plotted.length-1].y-11)}
                fontSize="11" fontWeight="850" textAnchor="end" fill="#096C56">
                {rate(plotted[plotted.length-1].point.cumulativeMatches,plotted[plotted.length-1].point.cumulativeTotal)}
              </text>
            </g>}
          </g>;
        })}
        {yearCohorts.map((c,i)=><text key={c.cohortId} x={mx(i)} y={MH-MB+22}
          textAnchor="middle" fontSize="10" fontWeight="800" fill={c.color}>
          {c.monthLabel.slice(0,3)}
        </text>)}
      </svg>
    </div>
    <p style={{color:muted,fontSize:11,lineHeight:1.5,margin:"7px 0 10px"}}>
      Colored dots are recorded cumulative monthly results; the straight line is their
      best-fit historical trend. With fewer than two recorded months, no trendline is drawn.
      Month-to-month case mixes vary. A rising historical trend does not establish improved
      prospective prediction accuracy.
    </p>
    {!compact?<>
    <div style={{overflowX:"auto",border:"1px solid #e2e9e5",borderRadius:9}}>
      <table data-testid="historical-monthly-level-table"
        style={{borderCollapse:"collapse",width:"100%",minWidth:930,fontSize:12}}>
        <thead><tr style={{background:"#e9f3ef",textAlign:"left"}}>
          {["Month","Level","Matched","Missed / abstain","Monthly agreement","Cumulative trend","Always approve","Run / evidence"].map(h=>
            <th scope="col" key={h} style={{padding:"10px 8px",whiteSpace:"nowrap"}}>{h}</th>)}
        </tr></thead>
        <tbody>{series.flatMap(s=>s.months.map((point,i)=>({s,point,i}))).map(({s,point,i})=>
          <tr key={s.level+"-"+yearCohorts[i].cohortId}
            style={{background:i%2?"#fbfdfa":"#fff"}}>
            <td style={{padding:8,color:yearCohorts[i].color,fontWeight:850}}>
              {yearCohorts[i].monthLabel} {activeYear}</td>
            <td style={{padding:8}}>Level {s.level}</td>
            <td style={{padding:8,fontWeight:800}}>{point?point.matches+" / "+point.total:"—"}</td>
            <td style={{padding:8}}>{point?point.misses+" missed · "+point.abstains+" abstain":"Not assessed"}</td>
            <td style={{padding:8}}>{point?rate(point.matches,point.total):"N/A"}</td>
            <td style={{padding:8,fontWeight:850}}>{point?rate(point.cumulativeMatches,point.cumulativeTotal):"N/A"}</td>
            <td style={{padding:8}}>{point?rate(point.cohort.alwaysApproveMatches,point.total):"N/A"}</td>
            <td style={{padding:8}}>
              {point?<div style={{display:"grid",gap:3}}>
                <span style={{color:muted}}>Method {point.run.methodVersion}</span>
                <span>
                  <a href={point.run.predictionFreezeUrl} target="_blank" rel="noopener noreferrer">Assessment</a>
                  {" · "}
                  <a href={point.cohort.sourceUrl} target="_blank" rel="noopener noreferrer">FDA result</a>
                </span>
              </div>:"Awaiting recorded assessment"}
            </td>
          </tr>)}</tbody>
      </table>
    </div>
    <details style={{marginTop:13,fontSize:12,lineHeight:1.6,color:muted}}>
      <summary style={{cursor:"pointer",fontWeight:850,color:dark}}>
        Fixed-case replay rules and source limitations
      </summary>
      <p>
        This PDUFA Year selector groups the tracked historical calendar year; some records
        do not have independently verified original PDUFA goal dates.
        The historical cases are outcome-aware reconstructions, not blind forecasts.
        The cumulative slope is descriptive, not a controlled measure of model improvement.
      </p>
      <p>
        As the analysis level advances to 4–20, save a full exact-case run with its method
        version and timestamp. The display will offer the level once the run is present in
        this versioned dataset and the site is redeployed. Missing levels remain disabled.
        Further revisions may increment revisionNumber while retaining prior Git history.
      </p>
      {yearCohorts.map(c=><p key={c.cohortId}>
        <strong style={{color:c.color}}>{c.monthLabel}:</strong> {c.cohortSelection}{" "}
        <a href={c.sourceUrl} target="_blank" rel="noopener noreferrer">Case-level source</a>
      </p>)}
    </details>
    <p style={{fontSize:12,color:"#815b27",fontWeight:800,lineHeight:1.55}}>
      All results here are OUTCOME-AWARE RECONSTRUCTIONS. They must never enter live FDA
      forecast accuracy, active FOCUS ranking, or probability calibration.
    </p></>:
      <p style={{fontSize:13,margin:"9px 0 2px",fontWeight:800}}>
        <a href="/predictions/assessment#historical-performance"
          style={{color:"#08725d",textDecoration:"underline"}}>
          Full Level 3–20 historical chart, source table and review methods
        </a>
      </p>}
  </section>;
}
