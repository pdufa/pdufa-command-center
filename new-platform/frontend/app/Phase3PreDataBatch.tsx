"use client";
import {useMemo,useState,useEffect} from "react";
import {phase3PredataSnapshot,phase3PreDataSourceFactCount} from "../lib/phase3-universal-questions";
import {phase3AnalysisCsvHeaders,phase3AnalysisCsvValues,phase3CompletedQuestions} from "../lib/phase3-top-questions";
import {TopPhase3Analysis} from "./Phase3TopAnalysis";
import research from "../data/phase3PreDataOfficialResearch.json";
const th={padding:"9px",borderBottom:"2px solid #a2c6af",textAlign:"left" as const};
const td={padding:"9px",borderBottom:"1px solid #d8e5dc",verticalAlign:"top" as const};
const PAGE_SIZE=25;
type PriorResult={nctId:string;sourceUrl?:string;registeredResults?:{primary?:{analyses?:{pValue?:string|number|null;pValueModifier?:string}[]}[]}|null};
type ResearchRecord={nctId:string;sourceState:string;sourceUrl?:string;registry?:{hasResults?:boolean;resultsFirstPosted?:string;status?:string};priorPhase2?:{matches:PriorResult[]}};
const publishedResearch=research as unknown as {sourceCutoff:string;records:ResearchRecord[];counts:{candidates:number;officialRegistryRecords:number;matchedPhase2PrimaryPValues:number}};
const researchByNct=new Map(publishedResearch.records.map(x=>[x.nctId,x] as const));
const postedAsOfCutoff=(nctId:string):boolean=>{
 const r=researchByNct.get(nctId);const day=r?.registry?.resultsFirstPosted||"";
 return Boolean(r?.registry?.hasResults&&(!day||day<=publishedResearch.sourceCutoff));
};
const postedIds=new Set(publishedResearch.records.filter(x=>postedAsOfCutoff(x.nctId)).map(x=>x.nctId));

const csvCell=(s:string)=>'"'+(/^[=+\-@]/.test(s)?"'"+s:s).replaceAll('"','""')+'"';
export default function Phase3PreDataBatch({query}:{query:string}){
 const [page,setPage]=useState(0);
 const trials=useMemo(()=>phase3PredataSnapshot.trials.filter(t=>!postedIds.has(t.nctId)),[]);
 const excludedPosted=useMemo(()=>phase3PredataSnapshot.trials.filter(t=>postedIds.has(t.nctId)),[]);
 const matching=useMemo(()=>{
  const q=query.trim().toLowerCase();
  return q?trials.filter(t=>[t.nctId,t.ticker,t.company,t.indication,t.interventions,t.registryStatus]
   .some(v=>v.toLowerCase().includes(q))):trials;
 },[query,trials]);
 useEffect(()=>setPage(0),[query]);
 const lastPage=Math.max(1,Math.ceil(matching.length/PAGE_SIZE));
 const activePage=Math.min(page,lastPage-1);
 const visible=matching.slice(activePage*PAGE_SIZE,(activePage+1)*PAGE_SIZE);
 function exportBatch(){
  const headers=["NCT","Ticker","Company","Registered indication","Registered interventions","Registry status",
   "Exact issuer readout verification","Protocol snapshot as of","Market cap USD","Market cap check date",
   "Outcome predictions documented","Registry source fact checks",
   "Original registry source status","Same-drug same-disease Phase 2 matches","Registered Phase 2 primary p-values",
   ...phase3AnalysisCsvHeaders()];
  const rows=[headers.map(csvCell).join(",")];
  for(const t of trials){
   const official=researchByNct.get(t.nctId);
   const priors=official?.priorPhase2?.matches||[];
   const primaryP=priors.flatMap(p=>(p.registeredResults?.primary||[]).flatMap(o=>
    (o.analyses||[]).filter(a=>a.pValue!==null&&a.pValue!==undefined&&a.pValue!=="")
     .map(a=>p.nctId+" "+(a.pValueModifier||"")+"p="+a.pValue)));
   const values=[t.nctId,t.ticker,t.company,t.indication,t.interventions,t.registryStatus,
    t.readoutStatus==="HISTORICAL_PRE_CHECK_ONLY"?"Historical pre-check only; not current confirmation":"UNVERIFIED — do not claim unreleased",
    t.protocol?.checkedAt||"Not retrieved",String(t.marketCapUsd),t.marketCapCheckedAt,
    String(phase3CompletedQuestions(t.nctId)),String(phase3PreDataSourceFactCount(t.nctId)),
    official?.sourceState||"Not collected",String(priors.length),primaryP.slice(0,20).join("; "),
    ...phase3AnalysisCsvValues(t.nctId)];
   rows.push(values.map(csvCell).join(","));
  }
  const url=URL.createObjectURL(new Blob(["\uFEFF"+rows.join("\r\n")+"\r\n"],{type:"text/csv;charset=utf-8"}));
  const a=document.createElement("a");a.href=url;a.download="TOP-registry-unposted-Phase3-30-question-research-2026-11-05.csv";
  document.body.appendChild(a);a.click();a.remove();window.setTimeout(()=>URL.revokeObjectURL(url),1000);
 }
 return <section data-phase3-batch-questions="true" style={{padding:12,margin:"14px 0",
  border:"2px solid #669d7b",borderRadius:10,background:"#f7fcf8"}}>
  <h3 style={{margin:"0 0 6px",fontSize:18}}>Phase 3 pre-readout candidate batch · 30 questions per trial</h3>
  <p style={{margin:"6px 0",fontSize:13}}>
   Dated $300M–$10B active Phase 3 source screen ({phase3PredataSnapshot.asOf}):
   <strong> {trials.length} registry-unposted candidates</strong>, after excluding
   {phase3PredataSnapshot.counts.knownIssuerReadoutsExcluded} previously confirmed issuer readouts and
   {excludedPosted.length} additional trials with official registry results posted.
   These are <strong>not all independently confirmed unpublished</strong>;
   an issuer may have announced results before registry posting.
  </p>
  <p style={{fontSize:12,margin:"7px 0"}}>
   Official ClinicalTrials.gov source records: {publishedResearch.counts.officialRegistryRecords} /
   {publishedResearch.counts.candidates}. Earlier drug-and-disease-matched Phase 2 primary p-value
   leads: {publishedResearch.counts.matchedPhase2PrimaryPValues} trials (review individual comparisons).
   Every remaining trial has all 30 questions.
   A 100/100 field-documentation score is <strong>not an outcome prediction</strong>. Without
   matched prior drug/indication evidence, clinical outcomes are UNSCORED, not invented.
   IZAR-2 keeps its 30 independently reasoned predictions. RAAS surveys remain cancelled.
  </p>
  <button type="button" onClick={exportBatch} style={{padding:"9px 12px",borderRadius:8,
   background:"#e1f3e6",color:"#145331",border:"1px solid #7da58b",fontWeight:700}}>
   Export all {trials.length} candidates × 30 questions (CSV)
  </button>
  <div role="region" aria-label="All Phase 3 pre-readout research candidates with 30 questions"
   style={{overflowX:"auto",marginTop:12}}>
   <table style={{borderCollapse:"collapse",fontSize:13,width:"100%",minWidth:1060}}>
    <thead><tr>{["#","Ticker","NCT","Company","Indication","Registered therapy",
     "Issuer readout","Registry protocol","30-question analysis"].map(t=><th key={t} scope="col" style={th}>{t}</th>)}</tr></thead>
    <tbody>{visible.map((t,i)=><tr key={t.nctId} data-phase3-batch-nct={t.nctId}>
     <td style={td}>{activePage*PAGE_SIZE+i+1}</td>
     <td style={td}><strong>{t.ticker}</strong></td>
     <td style={td}><a href={t.registrySourceUrl} target="_blank" rel="noopener noreferrer">{t.nctId}</a></td>
     <td style={td}>{t.company}</td><td style={td}>{t.indication||"Not in saved source"}</td>
     <td style={td}>{t.interventions||"Not in saved source"}</td>
     <td style={td}>Unverified {t.readoutStatus==="HISTORICAL_PRE_CHECK_ONLY"?"(historical pre-check)":""}</td>
     <td style={td}>{t.protocol?"Stored · "+(t.protocol.sourceUpdated||"dated snapshot"):"Not collected"}</td>
     <td style={td}><TopPhase3Analysis nctId={t.nctId}/></td>
    </tr>)}</tbody>
   </table>
  </div>
  {matching.length===0&&<p>No trial candidates match your search.</p>}
  <div style={{display:"flex",alignItems:"center",gap:12,flexWrap:"wrap",marginTop:12}}>
   <button type="button" disabled={activePage===0} onClick={()=>setPage(p=>Math.max(0,p-1))}>Previous 25</button>
   <span>Page {activePage+1} / {lastPage} · {matching.length} matching trials</span>
   <button type="button" disabled={activePage>=lastPage-1} onClick={()=>setPage(p=>Math.min(lastPage-1,p+1))}>Next 25</button>
  </div>
  <details style={{marginTop:12}}><summary style={{cursor:"pointer",fontWeight:700}}>
   Registry results already posted · {excludedPosted.length} excluded from pre-data batch
  </summary>
   <p>These records remain available for historical research but are not treated as unreleased Phase 3 outcomes.
    Company/issuer readout confirmation is a separate check.</p>
   <ul>{excludedPosted.map(t=><li key={t.nctId}>
    <a href={t.registrySourceUrl} target="_blank" rel="noopener noreferrer">{t.ticker} · {t.nctId}</a>
    {" — registry results first posted "+(researchByNct.get(t.nctId)?.registry?.resultsFirstPosted||"date not provided")}
   </li>)}</ul>
  </details>
  <p style={{fontSize:11,color:"#435b4c",marginTop:10}}>
   Historical research snapshot, not continuously verified issuer readout status.
   Registry study activity alone cannot establish that data remain unpublished.
  </p>
 </section>;
}
