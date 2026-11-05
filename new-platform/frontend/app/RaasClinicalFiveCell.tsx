"use client";
import {useState} from "react";
import type {ReadoutRow} from "../lib/phase3-public-readout";
import type {RaasStage} from "../lib/raas-metric-specs";
import {clinicalFiveForTrial} from "../lib/raas-clinical-five";

/** The only active per-trial RAAS scorecard. Legacy research history is kept separately. */
export default function RaasClinicalFiveCell({row,bucket,researchStageOnly}:{
 row:ReadoutRow;bucket:RaasStage|null;researchStageOnly?:RaasStage
}){
 const [selected,setSelected]=useState<RaasStage>(researchStageOnly??"pre");
 const stage=bucket??researchStageOnly??selected;
 const verified=bucket!==null;
 const report=clinicalFiveForTrial({
  nctId:row.nctId,ticker:row.ticker,
  drug:row.evidence?.drug,indication:row.evidence?.indication
 },stage,verified);
 return <section data-raas-clinical-five={row.nctId}
  data-raas-five-stage={verified?(stage==="pre"?"TOP":"BOTTOM"):"UNVERIFIED"}
  style={{padding:"8px 0",minWidth:170,color:"#194b2e"}}>
  <strong style={{display:"block",fontSize:14}}>{report.graded}/5 clinical grades</strong>
  <small style={{display:"block",color:"#536657"}}>
   {report.missing} N/A · {report.researchScore===null?
   "Full clinical score: N/A":"Clinical score: "+report.researchScore+"/100"}
  </small>
  <details data-raas-clinical-five-expand={row.nctId}
   style={{border:"1px solid #b5d5bf",borderRadius:7,
    padding:"8px",marginTop:6,background:"#f5faf5"}}>
   <summary style={{cursor:"pointer",fontSize:12,fontWeight:700}}>
    View five clinical assessments ▸
   </summary>
   {!verified&&<p style={{fontSize:12,margin:"8px 0"}}>
    TOP/BOTTOM readout status has not been issuer-classified. These are research
    questions, not a verified trial stage or overall rating.</p>}
   {!verified&&!researchStageOnly&&<div style={{display:"flex",gap:8,margin:"8px 0"}}>
    {(["pre","post"] as const).map(s=><button key={s} type="button"
      onClick={()=>setSelected(s)} aria-pressed={selected===s}
      style={{padding:"6px 10px",borderRadius:6,border:"1px solid #83a992",
       background:selected===s?"#d8eddf":"white",color:"#194b2e"}}>
      {s==="pre"?"Before results":"After results"}</button>)}
   </div>}
   <div role="list" aria-label="Five clinical RAAS factors"
    style={{display:"flex",overflowX:"auto",maxWidth:"min(780px,78vw)",
     gap:8,padding:"8px 0"}}>
    {report.factors.map(f=><article role="listitem" key={f.id}
      data-raas-clinical-factor={f.key}
      style={{flex:"0 0 178px",border:"1px solid #c6dccc",
       borderRadius:7,padding:9,background:f.grade===null?"white":"#eaf6ee"}}>
      <strong style={{display:"block",fontSize:12}}>{f.name}</strong>
      <strong style={{display:"block",fontSize:20,margin:"7px 0"}}>
       {f.grade===null?"N/A":f.grade+"/100"}</strong>
      <small>{f.finding?.replaceAll("_"," ")??"Source-backed assessment not yet graded"}</small>
      <p style={{fontSize:11,marginTop:6}}>{f.requiredEvidence}</p>
      {f.sourceUrl&&<div style={{fontSize:11}}>
       <a href={f.sourceUrl} target="_blank" rel="noopener noreferrer">Trial evidence</a>
       {f.benchmarkSourceUrl&&<>{' · '}<a href={f.benchmarkSourceUrl}
        target="_blank" rel="noopener noreferrer">Benchmark</a></>}
       <small style={{display:"block"}}>Reviewed {f.assessedAt}</small>
      </div>}
    </article>)}
   </div>
   <p style={{fontSize:11,lineHeight:1.5}}>
    Five equal-weight scientific factors only. Missing ratings are N/A.
    Financial, commercial, FDA-regulatory and investment-risk grades are excluded.
    FDA dates and outcomes remain factual records, not RAAS factors.
    A complete research score requires five documented grades and verified stage;
    it is not a calibrated FDA decision probability.
   </p>
  </details>
 </section>;
}
