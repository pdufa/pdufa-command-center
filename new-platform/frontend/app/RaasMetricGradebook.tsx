"use client";
import {useEffect,useMemo,useRef,useState} from "react";
import {createPortal} from "react-dom";
import type {ReadoutRow} from "../lib/phase3-public-readout";
import type {RaasStage} from "../lib/raas-metric-specs";
import {buildRaasMetricGradebook} from "../lib/raas-metric-gradebook";

/** A horizontal, scrollable score-detail panel, loaded only when the user opens it. */
export default function RaasMetricGradebook({row,bucket}:{
 row:ReadoutRow;bucket:RaasStage|null
}){
 const [open,setOpen]=useState(false);
 const trigger=useRef<HTMLButtonElement>(null);
 const book=useMemo(()=>open&&bucket?buildRaasMetricGradebook({
  nctId:row.nctId,ticker:row.ticker,
  drug:row.evidence?.drug,indication:row.evidence?.indication
 },bucket):null,[open,bucket,row.nctId,row.ticker,row.evidence?.drug,row.evidence?.indication]);
 useEffect(()=>{
  if(!open)return;
  const handler=(event:KeyboardEvent)=>{if(event.key==="Escape")setOpen(false);};
  document.addEventListener("keydown",handler);
  return ()=>{document.removeEventListener("keydown",handler);trigger.current?.focus();};
 },[open]);
 if(!bucket)return <span style={{fontSize:11}}>Stage unverified</span>;
 const label=bucket==="pre"?"TOP":"BOTTOM";
 return <>
  <button ref={trigger} type="button" aria-expanded={open}
   aria-label={"Expand "+label+" all 30 RAAS metric scores for "+row.ticker+" "+row.nctId}
   data-raas-metric-gradebook-trigger={row.nctId}
   style={{border:"1px solid #91bba3",borderRadius:7,padding:"7px 10px",
    background:"#eff8f0",color:"#15472f",fontWeight:700,cursor:"pointer"}}
   onClick={()=>setOpen(v=>!v)}>30 metrics <span aria-hidden="true">▸</span></button>
  {open&&book&&createPortal(
   <div role="presentation" onClick={e=>{if(e.target===e.currentTarget)setOpen(false);}}
    style={{position:"fixed",inset:0,zIndex:1200,background:"rgba(7,28,20,.65)",
     display:"flex",alignItems:"stretch",justifyContent:"flex-end",padding:12}}>
    <section role="dialog" aria-modal="true" aria-label={label+" detailed RAAS metric grades for "+row.ticker}
     data-raas-metric-gradebook={row.nctId}
     style={{width:"min(1050px,96vw)",maxHeight:"100%",overflowY:"auto",
      background:"#fff",borderRadius:12,padding:"18px 20px",color:"#173b29",
      boxShadow:"0 18px 65px rgba(0,0,0,.3)"}}>
     <header style={{display:"flex",justifyContent:"space-between",gap:12,alignItems:"start",flexWrap:"wrap"}}>
      <div>
       <strong style={{fontSize:19}}>{label} · {row.ticker} · {row.nctId}</strong>
       <p style={{margin:"6px 0"}}>All 30 RAAS ingredients · current source-evidence gradebook</p>
      </div>
      <button type="button" onClick={()=>setOpen(false)}
       style={{padding:"9px 12px",border:"1px solid #85ad98",borderRadius:7}}>
       Close ✕
      </button>
     </header>
     <div role="status" style={{display:"flex",gap:16,flexWrap:"wrap",
      padding:"12px 0",borderBottom:"1px solid #d3e4d8"}}>
      <span><strong>{book.graded}/30</strong> experimental metrics graded</span>
      <span><strong>{book.mappedOnly}</strong> evidence-lead-only metrics</span>
      <span><strong>{book.withoutEvidence}</strong> without mapped evidence</span>
      <span><strong>Overall RAAS: N/A</strong> · not validated</span>
     </div>
     <p style={{fontSize:13,lineHeight:1.5}}>
      A source lead is not a completed grade. A clinical effect, responder rate or
      cash balance is a factual measurement, not a 0–100 clinical success or investment
      score. No missing score is replaced with zero. Trial history remains keyed to
      the same NCT if it moves between TOP and BOTTOM.
     </p>
     <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(100%,340px),1fr))",gap:12}}>
      {book.categories.map((category,index)=>
       <details key={category.id} style={{border:"1px solid #bfd8c7",borderRadius:9,
        background:"#f9fcfa",alignSelf:"start",padding:12}}>
        <summary style={{cursor:"pointer",fontWeight:700}}>
         {index+1}. {category.name} · {category.graded}/5 graded
         <small style={{display:"block",fontWeight:400}}>{category.weight}% model weight
          · {category.withEvidence}/5 with source leads</small>
        </summary>
        {category.rows.map(metric=>
         <article key={metric.id} data-raas-metric-status={metric.status}
          style={{borderTop:"1px solid #d6e5dc",padding:"12px 0",lineHeight:1.4}}>
          <strong>{metric.id} · {metric.name}</strong>
          <div style={{fontWeight:700,margin:"5px 0"}}>
           {metric.grade?metric.grade.score+"/100 · experimental only":
            metric.status==="SOURCE_LEADS_ONLY"?"N/A · evidence available, grading incomplete":
            "N/A · missing required evidence"}
          </div>
          {metric.grade&&<p style={{fontSize:12}}>
           <strong>Rule:</strong> {metric.grade.ruleId}<br/>
           <strong>Evidence:</strong> {metric.grade.inputs}<br/>
           {metric.grade.explanation}
          </p>}
          {metric.evidence.map(lead=>
           <div key={lead.id} style={{fontSize:12,marginBottom:8,padding:8,
            background:"#eef6f0",borderRadius:6}}>
            {lead.measurement&&<strong>{lead.measurement.value.toLocaleString("en-US",
             {maximumFractionDigits:2})} {lead.measurement.unit} · {lead.measurement.label}</strong>}
            <p style={{margin:"3px 0"}}>{lead.description}</p>
            <a href={lead.sourceUrl} rel="noopener noreferrer" target="_blank">
             Primary source · {lead.sourceDate}
            </a>
           </div>)}
          <details style={{fontSize:12,margin:"8px 0",border:"1px solid #d4e4da",
           borderRadius:6,padding:6}}>
           <summary style={{cursor:"pointer",fontWeight:600}}>
            Experimental five-band review rubric · {metric.policy.method==="AUTOMATED_NARROW_PILOT"?
             "narrow source-based pilot":"full evidence review required"}
           </summary>
           {([0,25,50,75,100] as const).map(band=>
            <p key={band} style={{margin:"5px 0"}}><strong>{band}/100</strong> — {metric.policy.anchors[band]}</p>)}
           <p><strong>Reference needed:</strong> {metric.policy.benchmarkRequired}</p>
           <p>Neither a band definition nor a mapped source is an approved score.</p>
          </details>
          <p style={{fontSize:12,marginBottom:3}}><strong>Needed for scoring:</strong> {metric.requiredEvidence}</p>
          <p style={{fontSize:12,marginBottom:3}}><strong>Grading basis:</strong> {metric.scoreRule}</p>
          <p style={{fontSize:12,marginBottom:0}}><strong>Risk to check:</strong> {metric.criticalRisk}</p>
         </article>)}
       </details>)}
     </div>
     <p style={{fontSize:12,marginTop:14}}>
      Source dates identify publications, not the date a historical RAAS forecast was made.
      Experimental component grades are not approved for the weighted overall score.
     </p>
    </section>
   </div>,document.body)}
 </>;
}
