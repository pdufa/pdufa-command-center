"use client";
import {useEffect,useMemo,useState} from "react";
import type {ReadoutClassification} from "../lib/phase3-public-readout";
import {RAAS_RESTRICTED_TOP_PHASE3_CSV_QUERY,parseRaasScreenedPhase3Csv,
 type RaasScreenedTrialRoster} from "../lib/raas-full-universe-roster";
import {splitCapScreenedTopPhase3,capScreenedTopPhase3Csv}
 from "../lib/raas-cap-screened-top-phase3";

import {TopPhase3Analysis} from "./Phase3TopAnalysis";
const PAGE_SIZE=50;
const th={padding:"9px 10px",textAlign:"left" as const,borderBottom:"2px solid #94bba3"};
const td={padding:"9px 10px",borderBottom:"1px solid #d6e6db",verticalAlign:"top" as const};
export default function CapScreenedTopPhase3Spreadsheet({classification,query}:{
 classification:ReadoutClassification;query:string
}){
 const [roster,setRoster]=useState<RaasScreenedTrialRoster|null>(null);
 const [status,setStatus]=useState<"loading"|"ready"|"unavailable">("loading");
 const [reason,setReason]=useState("");
 const [page,setPage]=useState(0);
 useEffect(()=>{
  const controller=new AbortController();
  setStatus("loading");setRoster(null);setReason("");
  fetch(RAAS_RESTRICTED_TOP_PHASE3_CSV_QUERY,{cache:"no-store",
   credentials:"same-origin",signal:controller.signal})
   .then(async response=>{
    if(!response.ok)throw Error(response.status===401?
     "Sign in to load the market-cap-screened Phase 3 source.":
     "Current market-cap screening unavailable (HTTP "+response.status+").");
    return parseRaasScreenedPhase3Csv(await response.text(),classification);
   }).then(result=>{if(!controller.signal.aborted){setRoster(result);setStatus("ready");}})
   .catch(error=>{if(!controller.signal.aborted){setReason(error instanceof Error?error.message:
    "Current market-cap roster unavailable");setStatus("unavailable");}});
  return ()=>controller.abort();
 },[classification]);
 const split=useMemo(()=>roster?splitCapScreenedTopPhase3(roster,classification):null,
  [roster,classification]);
 const filtered=useMemo(()=>{
  const q=query.trim().toLowerCase();
  return split?.candidates.filter(row=>{
   const d=roster?.details.get(row.nctId);
   return !q||[row.nctId,row.ticker,row.company,d?.drug??"",d?.indication??""]
    .some(x=>x.toLowerCase().includes(q));
  })??[];
 },[roster,split,query]);
 const pages=Math.max(1,Math.ceil(filtered.length/PAGE_SIZE));
 const activePage=Math.min(page,pages-1);
 const visible=filtered.slice(activePage*PAGE_SIZE,(activePage+1)*PAGE_SIZE);
 function exportCsv(){
  if(!roster||!split)return;
  const csv=capScreenedTopPhase3Csv(roster,split);
  const url=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));
  const a=document.createElement("a");a.href=url;
  a.download="TOP-cap-screened-300M-10B-Phase3-trials.csv";
  document.body.appendChild(a);a.click();a.remove();
  window.setTimeout(()=>URL.revokeObjectURL(url),1000);
 }
 return <section data-raas-top-cap-screened-phase3="true"
  style={{padding:"14px",margin:"12px",border:"1px solid #96bea2",
   borderRadius:9,background:"#f5faf6"}}>
  <h4 style={{fontSize:16,margin:"0 0 6px"}}>
   TOP spreadsheet · $300M–$10B Phase 3 universe
  </h4>
  <p style={{fontSize:12,margin:"6px 0",lineHeight:1.5}}>
   Recorded <strong>Phase 3</strong> trials from the verified, dated
   Nasdaq/NYSE issuer-cap screen, separated from Phase 3 Results.
   Trials with a confirmed public Phase 3 readout are excluded.
   The remaining candidates are <strong>not automatically confirmed pre-readout</strong>.
  </p>
  {status==="loading"&&<p role="status">Loading all cap-screened Phase 3 trials…</p>}
  {status==="unavailable"&&<p role="alert">
   {reason}. No trial counts or membership guessed from the older census.
  </p>}
  {status==="ready"&&roster&&split&&<>
   <div role="status" style={{display:"flex",gap:14,flexWrap:"wrap",fontSize:13,
    margin:"10px 0"}}>
    <strong>{split.totalCurrentTopPhase3.toLocaleString()} current-screen Phase 3 rows for TOP</strong>
    <span>{split.candidates.length} stage-unverified candidates in this section</span>
    <span>{split.alreadyTop.length} already in issuer-checked TOP rows</span>
    <span>{split.excludedKnownPost} documented BOTTOM trials excluded</span>
   </div>
   <p style={{fontSize:12,margin:"6px 0"}}>
    Source snapshot: {roster.sourceAsOf}. Market-cap readings must pass the
    source's 30-day freshness checks; this is not confirmation of FDA/PDUFA eligibility.
   </p>
   <button type="button" onClick={exportCsv} style={{
    padding:"9px 13px",border:"1px solid #7da58b",borderRadius:7,
    background:"#e6f4e9",fontWeight:700,color:"#164a31",margin:"9px 0"}}>
    Export entire TOP Phase 3 cap-screened CSV
   </button>
   <div role="region" aria-label="TOP cap-screened Phase 3 trial spreadsheet"
    tabIndex={0} style={{overflowX:"auto",maxWidth:"100%"}}>
    <table style={{width:"100%",minWidth:900,borderCollapse:"collapse",fontSize:13}}>
     <thead><tr>{["#","Ticker","Trial / NCT","Company","Drug / therapy",
      "Indication","Phase 3 readout","30-question analysis"]
      .map(label=><th scope="col" style={th} key={label}>{label}</th>)}</tr></thead>
     <tbody>{visible.map((row,i)=>{
      const detail=roster.details.get(row.nctId);
      return <tr key={row.nctId} data-raas-top-cap-trial={row.nctId}>
       <td style={td}>{activePage*PAGE_SIZE+i+1}</td>
       <td style={td}><strong>{row.ticker}</strong></td>
       <td style={td}><a href={row.sourceUrl} target="_blank"
        rel="noopener noreferrer">{row.nctId}</a></td>
       <td style={td}>{row.company}</td>
       <td style={td}>{detail?.drug||"Not documented"}</td>
       <td style={td}>{detail?.indication||"Not documented"}</td>
       <td style={td}>Not issuer-verified · TOP candidate only</td>
       <td style={td}><TopPhase3Analysis nctId={row.nctId}/></td>
      </tr>;
     })}</tbody>
    </table>
   </div>
   {filtered.length===0&&<p role="status">No TOP candidates match this search.</p>}
   <div style={{display:"flex",gap:12,alignItems:"center",margin:"10px 0"}}>
    <button type="button" disabled={activePage===0}
     onClick={()=>setPage(p=>Math.max(0,p-1))}>Previous 50</button>
    <span>Page {activePage+1} of {pages}</span>
    <button type="button" disabled={activePage>=pages-1}
     onClick={()=>setPage(p=>Math.min(pages-1,p+1))}>Next 50</button>
   </div>
   <p style={{fontSize:12,margin:"9px 0 0",color:"#3d604c"}}>
    Confirmed historical TOP entries stay in the existing issuer-checked TOP
    rows below. Surveys and ratings are cancelled; the trial evidence remains.
   </p>
  </>}
 </section>;
}
