"use client";
import {useEffect,useRef,useState} from "react";
import {createPortal} from "react-dom";
import type {ReadoutRow} from "../lib/phase3-public-readout";
import type {RaasStage} from "../lib/raas-metric-specs";
import {parseRaasTrialHistory,historyForTrial,currentHistoryScore,comparableScoreDelta} from "../lib/raas-trial-score-history";
import {provisionalScoresForTrial} from "../lib/raas-provisional-trial-scores";
import savedHistory from "../data/raas-trial-score-history.json";
import css from "./RaasTrialHistoryButton.module.css";

const ledger=parseRaasTrialHistory(savedHistory);
const stageName=(s:RaasStage)=>s==="pre"?"TOP":"BOTTOM";
const kindName=(k:string)=>({
 FIRST_CAPTURE:"First saved evidence",EVIDENCE_UPDATED:"Evidence updated",
 STAGE_ADDED:"Trial entered another stage",SCORE_UPDATED:"Overall score updated",
 METRIC_SCORE_UPDATED:"Experimental component score updated"
} as Record<string,string>)[k]||k;

export default function RaasTrialHistoryButton({row,bucket}:{
 row:ReadoutRow;bucket:RaasStage|null
}){
 const [open,setOpen]=useState(false);
 const [selected,setSelected]=useState(0);
 const buttonRef=useRef<HTMLButtonElement>(null);
 const history=historyForTrial(ledger,{nctId:row.nctId,ticker:row.ticker,
  drug:row.evidence?.drug,indication:row.evidence?.indication});
 const score=bucket?currentHistoryScore(history,bucket):null;
 const provisional=bucket?provisionalScoresForTrial({nctId:row.nctId,ticker:row.ticker,
  drug:row.evidence?.drug,indication:row.evidence?.indication},bucket):null;
 const researchGrades=provisional?.scoredMetrics??[];
 const stageEntries=history.filter(e=>e.stage===bucket);
 const lastForStage=stageEntries.at(-1);
 const earlierStageEntries=history.filter(e=>e.stage!==bucket);
 const event=[...history].reverse()[selected]||null;
 const label=bucket?stageName(bucket):"UNVERIFIED";
 const controlId="raas-trial-history-"+row.nctId+"-"+bucket;
 useEffect(()=>{
  if(!open)return;
  const prev=document.activeElement instanceof HTMLElement?document.activeElement:null;
  const escape=(e:KeyboardEvent)=>{
   if(e.key==="Escape"){e.preventDefault();setOpen(false);}
  };
  document.addEventListener("keydown",escape);
  return ()=>{document.removeEventListener("keydown",escape);(buttonRef.current||prev)?.focus();};
 },[open]);
 return <>
  <button ref={buttonRef} type="button" className={css.button}
   aria-label={"Open "+label+" RAAS cross-stage score history for "+row.ticker+" "+row.nctId}
   aria-expanded={open} aria-controls={controlId}
   data-raas-trial-history-button={row.nctId}
   onClick={()=>{setSelected(0);setOpen(true);}}>
   <strong>{score?score.score+"/100":"—/100"}</strong>
   <span>History <span aria-hidden="true">▸</span></span>
   {researchGrades.length>0&&<small title="Exploratory components only; NOT overall RAAS">{researchGrades.length}/30 experimental metrics</small>}
   <small>{history.length} captured</small>
  </button>
  {open&&createPortal(
   <div className={css.backdrop} role="presentation"
     onClick={e=>{if(e.currentTarget===e.target)setOpen(false);}}>
    <div id={controlId} className={css.scroll} role="dialog" aria-modal="true"
     aria-label={"RAAS trial history across TOP and BOTTOM for "+row.ticker+" "+row.nctId}
     data-raas-unified-history={row.nctId}>
     <div className={css.expanded}>
      <div className={css.left}>
       <button type="button" className={css.close} onClick={()=>setOpen(false)}
        aria-label="Close RAAS trial history">Close ✕</button>
       <small>RAAS SCORE HISTORY</small>
       <strong className={css.score}>{score?score.score+"/100":"—/100"}</strong>
       <span>{score?(score.scoreKind==="VALIDATED"?"Validated":"Provisional")+
        " · "+label:"No overall score yet"}</span>
       <small>{row.ticker} · {row.nctId}</small>
       <small>{label} spreadsheet</small>
       <small>{history.length} saved events</small>
       {researchGrades.length>0&&<small>{researchGrades.length}/30 research-only component grades</small>}
      </div>
      <div className={css.right}>
       <header className={css.head}>
        <div><h3>{row.ticker} · Trial RAAS score history</h3>
         <p>One NCT + therapy history follows the trial from TOP to BOTTOM.
          TOP scores are never reused as BOTTOM ratings. In UNVERIFIED, history remains visible
          while the public readout classification is unresolved.</p></div>
        <span className={css.tag}>{label} now</span>
       </header>
       <div className={css.cards}>
        <div><small>Current {label} score</small><strong>{score?score.score+"/100":bucket?"Not scored":"Stage unverified"}</strong></div>
        <div><small>{label} captures</small><strong>{bucket?stageEntries.length:"Not classified"}</strong></div>
        <div><small>Other stage retained</small><strong>{earlierStageEntries.length}</strong></div>
        <div><small>Latest evidence areas</small><strong>{lastForStage?lastForStage.metricCoverage+"/30":"N/A"}</strong></div>
       </div>
       {researchGrades.length>0&&<div className={css.eventDetail} data-raas-current-provisional-metric={row.nctId}>
        <h4>Current experimental components · {researchGrades.length}/30 graded</h4>
        {researchGrades.map(grade=><div key={grade.metricId} style={{margin:"10px 0"}}>
         <p><strong>{grade.label} · {grade.metricId} · {grade.score}/100</strong></p>
         <p><strong>Input:</strong> {grade.inputs}</p>
         <p><strong>Rule:</strong> {grade.explanation}</p>
         <p><strong>Source:</strong> <a href={grade.sourceUrl} target="_blank" rel="noopener noreferrer">Issuer evidence ↗</a> · {grade.sourceDate}</p>
        </div>)}
        <p><strong>Overall RAAS remains —/100.</strong> Experimental timing and clinical component proxies do not establish efficacy, FDA success, investment returns, or an approved RAAS rating.</p>
       </div>}
       {!history.length?<p className={css.empty}>No historical score or evidence-change snapshots have been captured for this trial.
        A current exploratory component rating, if displayed above, is NOT a saved past prediction or an overall RAAS score.
        Captures begin when the connected nightly journal records changes.
        Earlier research cannot be backdated into genuine predictions.</p>:
        <div className={css.history}>
         <div className={css.eventList} role="group" aria-label="Saved TOP and BOTTOM score events">
          {[...history].reverse().map((e,index)=><button key={e.eventId} type="button"
            className={selected===index?css.eventSelected:css.event}
            onClick={()=>setSelected(index)} aria-pressed={selected===index}>
             <strong>{new Date(e.recordedAt).toLocaleDateString("en-US",{year:"numeric",month:"short",day:"numeric"})} · {stageName(e.stage)}</strong>
             <span>{kindName(e.kind)}</span>
             <small>{e.kind==="METRIC_SCORE_UPDATED"?
              "Exploratory "+(e.metricGrades?.map(g=>g.metricId+" "+g.score+"/100").join(", ")||"metric")+
              " · overall unscored":
              e.score===null?"Evidence only · unscored":e.score+"/100 · "+e.scoreKind}</small>
             <span className={css.caret} aria-hidden="true">▸</span>
            </button>)}
         </div>
         {event&&<div className={css.eventDetail} aria-live="polite">
          <h4>{stageName(event.stage)} · {kindName(event.kind)}</h4>
          <p><strong>Recorded:</strong> {new Date(event.recordedAt).toLocaleString("en-US")}</p>
          <p><strong>Evidence as of:</strong> {event.sourceAsOf}</p>
          <p><strong>Overall RAAS:</strong> {event.score===null?"Not scored":event.score+"/100 · "+event.scoreKind}</p>
          <p><strong>Comparable change:</strong> {event.score===null?"N/A":(()=>{
           const delta=comparableScoreDelta(history,event);
           return delta===null?"No same-stage/version predecessor":delta>0?"+"+delta:delta.toString();
          })()}</p>
          <p><strong>Why recorded:</strong> {event.summary}</p>
          <p><strong>Evidence leads:</strong> {event.metricCoverage}/30 metric areas</p>
          <p><strong>Calculation version:</strong> {event.scoreVersion||"No calculated score"}</p>
          {event.metricGrades?.map(g=><div key={g.metricId} className={css.eventDetail}
             data-raas-historical-component-grade={g.metricId}>
           <p><strong>Experimental metric {g.metricId}: {g.score}/100</strong> · NOT overall RAAS</p>
           <p>{g.label}: {g.inputs}</p>
           <p>{g.explanation}</p>
           <p><strong>Rule:</strong> {g.ruleId} · <strong>Source date:</strong> {g.sourceDate}</p>
          </div>)}
          {event.sourceUrls.length>0&&<div className={css.links}>
           <strong>Source documents</strong>
           {event.sourceUrls.map((url,i)=><a key={url} href={url} target="_blank"
             rel="noopener noreferrer">Open evidence source {i+1} ↗</a>)}
          </div>}
         </div>}
        </div>}
       <p className={css.foot}>Original events are retained even if the trial's spreadsheet or
        scoring model changes. A change of stage does not permit comparing TOP and BOTTOM
        numbers directly. Research coverage is not a predictive accuracy rating.</p>
      </div>
     </div>
    </div>
   </div>,document.body)}
 </>;
}
