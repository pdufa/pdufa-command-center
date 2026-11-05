"use client";
import {useMemo,useState} from "react";
import type {ReadoutClassification} from "../lib/phase3-public-readout";
import {clinicalFiveForClassifiedRow} from "../lib/raas-clinical-five";
const csvCell=(v:string|number|null)=>{
 const s=v==null?"":String(v);
 return '"'+(/^[=+@-]/.test(s)?"'"+s:s).replace(/"/g,'""')+'"';
};
export default function RaasClinicalFiveCompletionPanel({data}:{
 data:ReadoutClassification
}){
 const [expanded,setExpanded]=useState(false),[missingOnly,setMissingOnly]=useState(true);
 const report=useMemo(()=>{
  const trials=[...data.pre.map(row=>({row,stage:"pre" as const})),
   ...data.post.map(row=>({row,stage:"post" as const}))];
  const cells=trials.flatMap(({row,stage})=>{
   const result=clinicalFiveForClassifiedRow(row,stage);
   return result.factors.map(f=>({nctId:row.nctId,ticker:row.ticker,
    stage:stage==="pre"?"TOP":"BOTTOM",score:result.researchScore,...f}));
  });
  return {cells,graded:cells.filter(x=>x.grade!==null).length,
   missing:cells.filter(x=>x.grade===null).length,
   complete:trials.filter(({row,stage})=>
    clinicalFiveForClassifiedRow(row,stage).researchScore!==null).length};
 },[data]);
 function exportCsv(){
  const header=["nctId","ticker","stage","factor","grade","finding",
   "trialEvidenceUrl","benchmarkUrl","reviewDate","clinicalFiveTotalIfComplete"];
  const lines=[header.map(csvCell).join(","),
   ...report.cells.map(x=>[x.nctId,x.ticker,x.stage,x.name,x.grade,x.finding??"",
    x.sourceUrl??"",x.benchmarkSourceUrl??"",x.assessedAt??"",x.score]
    .map(csvCell).join(","))];
  const blob=new Blob(["\uFEFF"+lines.join("\r
")+"\r
"],{type:"text/csv;charset=utf-8"});
  const url=URL.createObjectURL(blob),a=document.createElement("a");
  a.href=url;a.download="raas-active-five-clinical-factors.csv";
  document.body.appendChild(a);a.click();a.remove();
  window.setTimeout(()=>URL.revokeObjectURL(url),1000);
 }
 return <section data-raas-five-completion="true"
  style={{margin:"14px 0",padding:14,border:"1px solid #b7d5c0",borderRadius:10}}>
  <h2 style={{fontSize:17,margin:"0 0 8px"}}>RAAS · active five-factor clinical scoring</h2>
  <p style={{fontSize:13,lineHeight:1.5}}>
   {data.total} historical Phase 3 trial IDs · five available assessment slots
   each ({data.total*5} potential slots). {data.unverified.length} require a
   documented TOP/BOTTOM readout classification before an overall trial score.
   Historical 30-metric finance, FDA-regulatory, market and risk assessments
   are archived and excluded from active RAAS.
  </p>
  <p style={{fontSize:13}}><a href="/raas-741-active-five-clinical.csv" download
   style={{fontWeight:700,color:"#145e37",textDecoration:"underline"}}>Download all 741 historical trials · five clinical assessment fields each (CSV)</a></p>
  <div style={{display:"flex",gap:15,flexWrap:"wrap",fontSize:13,margin:"12px 0"}}>
   <strong>{report.cells.length} classified clinical slots</strong>
   <strong>{report.graded} graded</strong><strong>{report.missing} N/A</strong>
   <strong>{report.complete} complete five-factor research scores</strong>
  </div>
  <div role="progressbar" aria-label="Classified clinical factors graded"
   aria-valuenow={report.graded} aria-valuemin={0}
   aria-valuemax={report.cells.length}
   style={{height:10,background:"#e4eee7",borderRadius:10,overflow:"hidden"}}>
   <div style={{height:"100%",background:"#278353",
    width:(report.cells.length?100*report.graded/report.cells.length:0)+"%"}}/>
  </div>
  <div style={{display:"flex",gap:9,margin:"12px 0",flexWrap:"wrap"}}>
   <button type="button" onClick={exportCsv}
    style={{padding:10,border:"1px solid #8fbda1",borderRadius:7}}>
    Export five-factor grades and evidence
   </button>
   <button type="button" onClick={()=>setExpanded(v=>!v)}
    aria-expanded={expanded} style={{padding:10,border:"1px solid #8fbda1",borderRadius:7}}>
    {expanded?"Hide":"Show"} five-factor requirements
   </button>
  </div>
  {expanded&&<>
   <label style={{fontSize:12}}><input type="checkbox" checked={missingOnly}
    onChange={e=>setMissingOnly(e.target.checked)}/> Show missing only</label>
   <div style={{maxHeight:370,overflowY:"auto",marginTop:8}}>
    <table style={{width:"100%",fontSize:12,borderCollapse:"collapse"}}>
     <thead><tr>{["Trial","Stage","Clinical factor","Grade","Evidence"].map(x=>
      <th key={x} style={{textAlign:"left",padding:7}}>{x}</th>)}</tr></thead>
     <tbody>{report.cells.filter(x=>!missingOnly||x.grade===null).map(x=>
      <tr key={x.nctId+"-"+x.id}>
       <td style={{padding:7}}>{x.ticker} · {x.nctId}</td>
       <td>{x.stage}</td><td>{x.name}</td>
       <td>{x.grade===null?"N/A":x.grade+"/100"}</td>
       <td>{x.sourceUrl?<a href={x.sourceUrl}
        target="_blank" rel="noopener noreferrer">Source</a>:
        "Evidence review required"}</td>
      </tr>)}</tbody>
    </table>
   </div>
  </>}
 </section>;
}
