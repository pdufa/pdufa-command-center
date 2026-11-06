"use client";
import {useEffect,useMemo,useState} from "react";
import {parsePhase3CensusCsv} from "../lib/phase3-census-rows";
import {classifyPhase3Readouts,type ReadoutClassification,type ReadoutRow} from "../lib/phase3-public-readout";
import CapScreenedTopPhase3Spreadsheet from "./CapScreenedTopPhase3Spreadsheet";
import {TopPhase3ResearchExample} from "./Phase3TopAnalysis";
const tableStyle={width:"100%",borderCollapse:"collapse" as const,fontSize:13};
const cell={padding:"9px",borderBottom:"1px solid #d8e2dc",textAlign:"left" as const};
function Rows({rows,query}:{rows:ReadoutRow[];query:string}){
 const filtered=rows.filter(r=>!query||[r.nctId,r.ticker,r.company,r.status,r.evidence?.drug||"",r.evidence?.indication||""].some(s=>s.toLowerCase().includes(query)));
 return <div role="region" aria-label="Phase 3 trial records" style={{overflowX:"auto",maxHeight:520,overflowY:"auto"}}>
  <table style={tableStyle}><thead><tr>{["Ticker","NCT","Company","Drug","Indication","Registry status","Dated issuer evidence"].map(x=><th key={x} style={cell}>{x}</th>)}</tr></thead>
   <tbody>{filtered.map(r=><tr key={r.nctId}>
    <td style={cell}>{r.ticker}</td>
    <td style={cell}><a href={r.sourceUrl} target="_blank" rel="noopener noreferrer">{r.nctId}</a></td>
    <td style={cell}>{r.company}</td>
    <td style={cell}>{r.evidence?.drug||"Not documented"}</td>
    <td style={cell}>{r.evidence?.indication||"Not documented"}</td>
    <td style={cell}>{r.status.replaceAll("_"," ")}</td>
    <td style={cell}>{r.evidence?<a href={r.evidence.evidenceUrl} target="_blank" rel="noopener noreferrer">{r.evidence.evidenceDate||"Source"}</a>:"Not verified"}</td>
   </tr>)}</tbody></table>
  {!filtered.length&&<p>No matching trial rows.</p>}
 </div>;
}
export default function Phase3SourceOnlySheets(){
 const [data,setData]=useState<ReadoutClassification|null>(null);
 const [status,setStatus]=useState("Loading trial source evidence…");
 const [query,setQuery]=useState("");
 const [showUnverified,setShowUnverified]=useState(false);
 useEffect(()=>{const controller=new AbortController();
  Promise.all([fetch("/phase3-census-2026-10-26.csv",{cache:"no-store",signal:controller.signal}),
   fetch("/phase3-public-readout-evidence-2026-11-01.json",{cache:"no-store",signal:controller.signal})])
   .then(async ([c,e])=>{if(!c.ok||!e.ok)throw Error("Dated research sources unavailable");
    return classifyPhase3Readouts(await e.json(),parsePhase3CensusCsv(await c.text()).rows);})
   .then(result=>{if(!controller.signal.aborted){setData(result);setStatus("");}})
   .catch(()=>{if(!controller.signal.aborted)setStatus("Dated source evidence unavailable; no trial counts asserted.");});
  return()=>controller.abort();
 },[]);
 const q=useMemo(()=>query.trim().toLowerCase(),[query]);
 if(!data)return <p role="status">{status}</p>;
 return <section data-surveys-ratings-cancelled="true" style={{padding:"8px 0"}}>
  <p role="status"><strong>Surveys and ratings: cancelled.</strong> Source-only Phase 3 spreadsheets remain available; no clinical grades or scorecards are generated here.</p>
  <label style={{display:"block",margin:"12px 0"}}>Search ticker, NCT, company, therapy or indication
   <input type="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search trial records" style={{display:"block",width:"100%",maxWidth:400,padding:8}}/>
  </label>
  <details open style={{border:"1px solid #b0cbb9",borderRadius:9,padding:12,margin:"12px 0"}}>
   <summary style={{fontWeight:750,cursor:"pointer"}}>TOP · Phase 3 before a documented public readout ({data.pre.length} issuer-classified historical)</summary>
   <TopPhase3ResearchExample/>
   <CapScreenedTopPhase3Spreadsheet classification={data} query={query}/>
   <Rows rows={data.pre} query={q}/>
  </details>
  <details style={{border:"1px solid #b0cbb9",borderRadius:9,padding:12,margin:"12px 0"}}>
   <summary style={{fontWeight:750,cursor:"pointer"}}>BOTTOM · Public Phase 3 readout documented ({data.post.length} historical)</summary>
   <Rows rows={data.post} query={q}/>
  </details>
  <details open={showUnverified} onToggle={e=>setShowUnverified(e.currentTarget.open)} style={{border:"1px solid #b0cbb9",borderRadius:9,padding:12,margin:"12px 0"}}>
   <summary style={{fontWeight:750,cursor:"pointer"}}>Not issuer-classified ({data.unverified.length} historical)</summary>
   {showUnverified&&<Rows rows={data.unverified} query={q}/>}
  </details>
  <p style={{fontSize:12}}>Dated research snapshot: {data.sourceAsOf}. ClinicalTrials.gov results-posting alone does not confirm a company Phase 3 readout. Historical records preserved without surveys or ratings.</p>
 </section>;
}
