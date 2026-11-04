"use client";
import {useEffect,useRef,useState} from "react";
import {createPortal} from "react-dom";
import type {RaasSelfAccuracyAudit} from "../../lib/raas-self-accuracy-audit";
import snapshotData from "../../data/raas-self-audit-history.json";
import css from "../RaasTrialHistoryButton.module.css";

type AuditSnapshot={
 eventId:string;recordedAt:string;metricDefinitions:number;
 verifiedYearAudits:number;rawHistoricalTradeRows:number;
 rawHistoricalMetricRows:number;rawCalibrationRegistryEntries:number;
 rawReviewedTrialSnapshots:number;claimedPredecisionThreeWayForecasts:number;
 accuracyScore:null;accuracyPercent:null;status:"NOT_INDEPENDENTLY_RATED";
 evidenceFingerprint:string;note:string;
};
const snapshots=([...(snapshotData as unknown as {records:AuditSnapshot[]}).records]).reverse();
export default function RaasSelfAuditHistoryButton({audit}:{audit:RaasSelfAccuracyAudit}){
 const [open,setOpen]=useState(false);
 const [selected,setSelected]=useState(0);
 const ref=useRef<HTMLButtonElement>(null);
 const shown=snapshots[selected]||null;
 useEffect(()=>{
  if(!open)return;
  const onKey=(e:KeyboardEvent)=>{if(e.key==="Escape"){setOpen(false);e.preventDefault();}};
  document.addEventListener("keydown",onKey);
  return ()=>{document.removeEventListener("keydown",onKey);ref.current?.focus();};
 },[open]);
 return <>
  <button ref={ref} type="button" className={css.button}
   data-raas-system-history-button="true" aria-expanded={open}
   aria-controls="raas-system-rating-history"
   aria-label="Open RAAS rating-system accuracy history"
   onClick={()=>{setSelected(0);setOpen(true);}}>
   <strong>RAAS Accuracy · N/A</strong>
   <span>History <span aria-hidden="true">▸</span></span>
   <small>{snapshots.length} captures</small>
  </button>
  {open&&createPortal(<div className={css.backdrop} role="presentation"
   onClick={e=>{if(e.target===e.currentTarget)setOpen(false);}}>
   <div className={css.scroll} id="raas-system-rating-history" role="dialog" aria-modal="true"
    aria-label="RAAS rating-system accuracy and methodology history"
    data-raas-system-history="true">
    <div className={css.expanded}>
     <div className={css.left}>
      <button type="button" className={css.close} onClick={()=>setOpen(false)}
       aria-label="Close RAAS system history">Close ✕</button>
      <small>RAAS SYSTEM ACCURACY</small>
      <strong className={css.score}>N/A</strong>
      <span>Independent accuracy not measurable</span>
      <small>Evidence gates {audit.raasGatesPassed}/{audit.raasGatesRequired}</small>
      <small>{snapshots.length} dated source-inventory captures</small>
     </div>
     <div className={css.right}>
      <header className={css.head}>
       <div><h3>RAAS rating of the RAAS rating system</h3>
        <p>Tracks changes in the methodology's validation evidence.
         This is a system-wide audit, NOT an individual trial score.</p></div>
       <span className={css.tag}>NOT VALIDATED</span>
      </header>
      <div className={css.cards}>
       <div><small>Independent accuracy</small><strong>N/A</strong></div>
       <div><small>Evidence gates passed</small><strong>{audit.raasGatesPassed}/{audit.raasGatesRequired}</strong></div>
       <div><small>Independent returns accuracy</small><strong>N/A</strong></div>
       <div><small>FDA 3-way accuracy</small><strong>N/A</strong></div>
      </div>
      <h4>Current evidence requirements</h4>
      <div className={css.eventList} style={{maxHeight:"none",flex:"none"}}>
       {audit.raasGates.map(g=><div key={g.id} className={css.event}>
        <strong>{g.passed?"✓ ":"Pending · "}{g.name}</strong>
        <span>{g.achieved}/{g.required} {g.unit}</span>
       </div>)}
      </div>
      <h4>Recorded system-audit changes</h4>
      {!snapshots.length?
       <p className={css.empty}>No historical self-rating snapshots have been captured yet.
        The nightly audit will begin retaining source-inventory changes.
        A missing accuracy rating is not a 0/100 score.</p>:
       <div className={css.history}>
        <div className={css.eventList} role="group" aria-label="Recorded RAAS system evidence events">
         {snapshots.map((s,i)=><button key={s.eventId} type="button"
          className={selected===i?css.eventSelected:css.event}
          onClick={()=>setSelected(i)} aria-pressed={selected===i}>
          <strong>{new Date(s.recordedAt).toLocaleString("en-US")}</strong>
          <span>Methodology evidence inventory updated</span>
          <small>Independent accuracy N/A</small>
          <span className={css.caret} aria-hidden="true">▸</span>
         </button>)}
        </div>
        {shown&&<div className={css.eventDetail} aria-live="polite">
         <h4>Saved evidence snapshot</h4>
         <p>Metric definitions: {shown.metricDefinitions}/60</p>
         <p>2024/2025 year-census source attestations: {shown.verifiedYearAudits}/2</p>
         <p>Raw historical return rows: {shown.rawHistoricalTradeRows}</p>
         <p>Raw historical metric rows: {shown.rawHistoricalMetricRows}</p>
         <p>Raw calibration registry entries: {shown.rawCalibrationRegistryEntries}</p>
         <p>Reviewed trial records: {shown.rawReviewedTrialSnapshots}</p>
         <p>Claimed frozen 3-way forecasts awaiting independent audit: {shown.claimedPredecisionThreeWayForecasts}</p>
         <p><strong>Independent accuracy: N/A (not measured)</strong></p>
         <p>{shown.note}</p>
        </div>}
       </div>}
      <p className={css.foot}>A recorded raw count is not a passed scientific validation gate.
       Future approved system ratings must be independently tested, versioned and
       stored separately from research-evidence progress. No past score is backfilled.</p>
     </div>
    </div>
   </div>
  </div>,document.body)}
 </>;
}
