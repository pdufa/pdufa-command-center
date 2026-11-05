"use client";
import type {ReadoutRow} from "../lib/phase3-public-readout";
import type {RaasStage} from "../lib/raas-metric-specs";
import {exactClassifiedRaasComponentGrades}
 from "../lib/raas-classified-component-grades";

/** Per-row source-reconciled component grades, NOT 0–100 composite scores.
 * Native horizontal disclosure keeps 30 requirements accessible on iPhone.
 */
export default function RaasClassifiedComponentsCell({
 row,bucket
}:{row:ReadoutRow;bucket:RaasStage}){
 const audit=exactClassifiedRaasComponentGrades(bucket,row);
 return <section data-raas-classified-nct-score-populated={audit.nctId}
  data-raas-classified-stage={audit.stage}
  style={{padding:"9px 0",minWidth:175}}>
  <strong style={{display:"block",fontSize:14,color:"#194b2e"}}>
   {audit.gradedMetrics}/30 source-reviewed metric grades
  </strong>
  <span style={{display:"block",fontSize:12,color:"#536657"}}>
   {audit.missingMetrics} N/A · full RAAS: not validated
  </span>
  <details data-raas-metric-grade-expansion={audit.nctId}
   style={{marginTop:7,border:"1px solid #b5d5bf",borderRadius:7,
    padding:"7px 8px",background:"#f5faf5"}}>
   <summary style={{cursor:"pointer",fontSize:12,fontWeight:700}}>
    View 30 metric scores horizontally ▸
   </summary>
   <p style={{fontSize:12,margin:"8px 0",lineHeight:1.45}}>
    Numbers appear only for existing dated, exact-NCT, exact-therapy
    AI-assisted provisional reviews. Missing evidence is N/A, not a
    failing 0. No approved overall score or FDA approval probability.
   </p>
   <div role="list" aria-label={audit.stage+" 30 metric provisional grades for "+audit.nctId}
    style={{display:"flex",overflowX:"auto",gap:9,padding:"8px 0",maxWidth:"min(790px,75vw)"}}>
    {audit.provisionalGrades.map(m=>
     <div role="listitem" key={m.id} data-raas-metric-score={m.id}
      data-raas-metric-status={m.grade===null?"REVIEW_REQUIRED":"PROVISIONAL_REVIEWED"}
      style={{flex:"0 0 165px",minWidth:165,padding:9,border:"1px solid #c9dace",
       borderRadius:6,background:m.grade===null?"#fafafa":"#eaf6ee"}}>
      <small style={{display:"block",fontWeight:700}}>{m.id}</small>
      <strong style={{display:"block",fontSize:20,margin:"4px 0"}}>
       {m.grade===null?"N/A":m.grade+"/100"}
      </strong>
      <small style={{display:"block",fontSize:11}}>
       {m.name}
      </small>
      <small style={{display:"block",color:"#53705b",marginTop:5}}>
       {m.grade===null?"No documented grade":m.reviewClass===
        "INDEPENDENT_REVIEW"?"Provisional independently reviewed":
        "Provisional AI source cross-check"}
      </small>
      {m.grade!==null&&m.sourceUrl&&<div style={{marginTop:6,fontSize:11}}>
       <a href={m.sourceUrl} target="_blank" rel="noopener noreferrer">
        Primary source</a>
       {m.benchmarkSourceUrl&&<>
        {" · "}<a href={m.benchmarkSourceUrl} target="_blank"
         rel="noopener noreferrer">Comparator</a></>}
       <small style={{display:"block",marginTop:4}}>
        Evidence {m.sourceDate} · assessed {m.assessedAt}
       </small>
      </div>}
     </div>)}
   </div>
  </details>
 </section>;
}
