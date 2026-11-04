"use client";
import {useEffect,useRef,useState} from "react";
import {createPortal} from "react-dom";
import type {ReadoutRow} from "../lib/phase3-public-readout";
import type {RaasStage} from "../lib/raas-metric-specs";
import {parseRaasTrialHistory,historyForTrial,currentHistoryScore,comparableScoreDelta} from "../lib/raas-trial-score-history";
import savedHistory from "../data/raas-trial-score-history.json";
import css from "./RaasTrialHistoryButton.module.css";

const ledger=parseRaasTrialHistory(savedHistory);
const stageName=(s:RaasStage)=>s==="pre"?"TOP":"BOTTOM";
const kindName=(k:string)=>({
 FIRST_CAPTURE:"First saved evidence",EVIDENCE_UPDATED:"Evidence updated",
 STAGE_ADDED:"Trial entered another stage",SCORE_UPDATED:"Score updated"
} as Record<string,string>)[k]||k;

export default function RaasTrialHistoryButton({row,bucket}:{
 row:ReadoutRow;bucket:RaasStage
}){
 const [open,setOpen]=useState(false);
 const [selected,setSelected]=useState(0);
 const buttonRef=useRef<HTMLButtonElement>(null);
 const history=historyForTrial(ledger,{nctId:row.nctId,ticker:row.ticker,
  drug:row.evidence?.drug,indication:row.evidence?.indication});
 const score=currentHistoryScore(history,bucket);
 const stageEntries=history.filter(e=>e.stage===bucket);
 const lastForStage=stageEntries.at(-1);
 const earlierStageEntries=history.filter(e=>e.stage!==bucket);
 const event=[...history].reverse()[selected]||null;
 const label=stageName(bucket);
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
      </div>
      <div className={css.right}>
       <header className={css.head}>
        <div><h3>{row.ticker} · Trial RAAS score history</h3>
         <p>One NCT + therapy history follows the trial from TOP to BOTTOM.
          TOP scores are never reused as BOTTOM ratings.</p></div>
        <span className={css.tag}>{label} now</span>
       </header>
       <div className={css.cards}>
        <div><small>Current {label} score</small><strong>{score?score.score+"/100":"Not scored"}</strong></div>
        <div><small>{label} captures</small><strong>{stageEntries.length}</strong></div>
        <div><small>Other stage retained</small><strong>{earlierStageEntries.length}</strong></div>
        <div><small>Latest evidence areas</small><strong>{lastForStage?lastForStage.metricCoverage+"/30":"N/A"}</strong></div>
       </div>
       {!history.length?<p className={css.empty}>No score or evidence-change snapshots have been captured for this trial.
        The button is ready; a source check is not a 0/100 rating.
        Captures begin when the connected nightly journal observes saved research evidence.
        Earlier results cannot be backdated into genuine predictions.</p>:
        <div className={css.history}>
         <div className={css.eventList} role="group" aria-label="Saved TOP and BOTTOM score events">
          {[...history].reverse().map((e,index)=><button key={e.eventId} type="button"
            className={selected===index?css.eventSelected:css.event}
            onClick={()=>setSelected(index)} aria-pressed={selected===index}>
             <strong>{new Date(e.recordedAt).toLocaleDateString("en-US",{year:"numeric",month:"short",day:"numeric"})} · {stageName(e.stage)}</strong>
             <span>{kindName(e.kind)}</span>
             <small>{e.score===null?"Evidence only · unscored":e.score+"/100 · "+e.scoreKind}</small>
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
