"use client";
import {useEffect,useMemo,useState} from "react";

type TrialRow={
 nctId:string;ticker:string;company:string;registryStatus:string;rosterStatus:string;
 registryAsOf:string;classificationCode:string;classification:string;classificationEvidence:string;
 classificationVerified:boolean;readoutEvidenceType:string;readoutSourceDate:string|null;
 readoutEvidenceUrl:string|null;readoutOutcome:string;drug:string|null;indication:string|null;
 registeredInterventions:string|null;registrySourceUrl:string;fdaApplicationStatus:string;
 fdaReviewType:string;pdufaGoalDate:string|null;marketCapSourceStatus:string;
 inDatedMarketCapScreen:boolean;
};
type Snapshot={schemaVersion:number;asOf:string;total:number;note:string;
 classifications:{code:string;label:string}[];counts:Record<string,number>;rows:TrialRow[]};
const cell={padding:"8px 10px",borderBottom:"1px solid #d9e5de",textAlign:"left" as const,verticalAlign:"top" as const};
const labels:Record<string,string>={
 NOT_INDEPENDENTLY_REVIEWED:"Unreviewed",
 PRIMARY_ENDPOINT_MET:"Primary endpoint met",
 NOT_VERIFIED:"Not verified"
};
export default function Phase3UnifiedClassifications(){
 const [data,setData]=useState<Snapshot|null>(null);
 const [error,setError]=useState("");
 const [query,setQuery]=useState("");
 const [classification,setClassification]=useState("ALL");
 const [page,setPage]=useState(0);
 const perPage=50;
 useEffect(()=>{
  const controller=new AbortController();
  fetch("/phase3-unified-classifications-2026-11-05.json",{cache:"no-store",signal:controller.signal})
   .then(async r=>{if(!r.ok)throw new Error("Classification source unavailable");return await r.json() as Snapshot;})
   .then(d=>{
    if(d.total!==762||d.rows.length!==762||
      new Set(d.rows.map(x=>x.nctId)).size!==762||
      Object.values(d.counts).reduce((a,b)=>a+b,0)!==762)
     throw new Error("The 762-trial classification ledger failed validation");
    if(!controller.signal.aborted)setData(d);
   })
   .catch(()=>{if(!controller.signal.aborted)setError("The source classification ledger could not be loaded or verified.");});
  return ()=>controller.abort();
 },[]);
 const filtered=useMemo(()=>{
  const term=query.trim().toLowerCase();
  return (data?.rows||[]).filter(r=>
   (classification==="ALL"||r.classificationCode===classification)&&
   (!term||[r.nctId,r.ticker,r.company,r.registryStatus,r.classification,
    r.drug||"",r.indication||"",r.registeredInterventions||""]
    .some(v=>v.toLowerCase().includes(term))));
 },[data,query,classification]);
 const maxPage=Math.max(1,Math.ceil(filtered.length/perPage));
 const currentPage=Math.min(page,maxPage-1);
 const shown=filtered.slice(currentPage*perPage,(currentPage+1)*perPage);
 return <section data-phase3-unified-census="762" style={{margin:"14px 0 22px",padding:14,border:"2px solid #7ea18b",borderRadius:12}}>
  <h2 style={{margin:"0 0 7px"}}>Unified Phase 3 master spreadsheet · 762 trials</h2>
  <p style={{fontSize:13,margin:"0 0 10px"}}>One unique NCT per row. <strong>Classification is based on observed evidence, not assumed 425/337 counts.</strong> The original registry state and readout evidence are retained separately. Only exact-NCT evidence supports a documented primary-endpoint PASS; unadjudicated trials remain undetermined, not FAIL. A full 190-column assessment export is available below. FDA statuses are not asserted without an application-level source.</p>
  {!data?<p role="status">{error||"Loading classifications for 762 trials…"}</p>:<>
   <div style={{display:"flex",flexWrap:"wrap",gap:8,margin:"10px 0 14px"}}>
    {data.classifications.map(c=><button type="button" key={c.code} onClick={()=>{setClassification(classification===c.code?"ALL":c.code);setPage(0)}}
      aria-pressed={classification===c.code}
      style={{padding:"7px 10px",borderRadius:8,cursor:"pointer",fontSize:12,border:classification===c.code?"2px solid #287c53":"1px solid #a2b9aa",background:"transparent",color:"inherit",textAlign:"left"}}>
      {c.label} <strong>({data.counts[c.code]})</strong>
     </button>)}
    <button type="button" onClick={()=>{setClassification("ALL");setPage(0)}} aria-pressed={classification==="ALL"}
      style={{padding:"7px 10px",border:"1px solid #a2b9aa",borderRadius:8,background:"transparent",color:"inherit",cursor:"pointer",fontSize:12}}>All 762</button>
   </div>
   <label style={{display:"block",fontSize:13}}>Search the entire unified trial spreadsheet
    <input type="search" value={query} onChange={e=>{setQuery(e.target.value);setPage(0)}}
     placeholder="Ticker, NCT, company, indication, classification" style={{display:"block",padding:9,width:"100%",maxWidth:510,marginTop:5}}/>
   </label>
   <p style={{fontSize:12,margin:"12px 0"}}><strong><a href="/api/phase3-unified-190-columns">Download all 762 trials · 190 columns (CSV)</a></strong>{" · "}<a href="/phase3-unified-classifications-2026-11-05.csv" download>Original classification CSV</a></p>
   <p role="status" style={{fontSize:12}}>Showing {shown.length} of {filtered.length} matching trials · source classification as of {data.asOf}. Dated registry status is not proof of trial results.</p>
   <div role="region" aria-label="Unified Phase 3 trial classifications" style={{overflowX:"auto",maxHeight:630,overflowY:"auto"}}>
    <table style={{width:"100%",borderCollapse:"collapse",fontSize:12,minWidth:1000}}>
     <thead><tr>{["Ticker","Trial / NCT","Company","Registry status","Trial classification","Passing classification","Result","FDA / PDUFA","Evidence / details"].map(x=><th key={x} scope="col" style={{...cell,position:"sticky",top:0,background:"var(--surface,#f7f9f8)",zIndex:1}}>{x}</th>)}</tr></thead>
     <tbody>{shown.map(r=><tr key={r.nctId} data-nct-id={r.nctId} data-trial-classification={r.classificationCode} data-passing-classification={r.classificationVerified&&r.readoutOutcome==="PRIMARY_ENDPOINT_MET"&&r.readoutEvidenceUrl?"PASS_DOCUMENTED_PRIMARY_ENDPOINT":"UNDETERMINED"}>
      <td style={cell}>{r.ticker}</td>
      <td style={cell}><a href={r.registrySourceUrl} rel="noopener noreferrer" target="_blank">{r.nctId}</a></td>
      <td style={cell}>{r.company}</td>
      <td style={cell}>{r.registryStatus.replaceAll("_"," ")}</td>
      <td style={cell}><strong>{r.classification}</strong></td>
      <td style={cell}>{r.classificationVerified&&r.readoutOutcome==="PRIMARY_ENDPOINT_MET"&&r.readoutEvidenceUrl?<strong>PASS · documented primary endpoint</strong>:"Undetermined"}</td>
      <td style={cell}>{labels[r.readoutOutcome]||r.readoutOutcome.replaceAll("_"," ")}</td>
      <td style={cell}>{r.fdaApplicationStatus==="NOT_VERIFIED"?"FDA application not verified":r.fdaApplicationStatus}{r.pdufaGoalDate?" · "+r.pdufaGoalDate:""}</td>
      <td style={cell}>
       <details><summary style={{cursor:"pointer",fontWeight:650}}>Sources & status</summary>
        <div style={{padding:"8px 0",minWidth:240}}>
         <p style={{margin:"4px 0"}}>{r.classificationEvidence}</p>
         <p style={{margin:"4px 0"}}>Registry as of: {r.registryAsOf}</p>
         {r.drug&&<p style={{margin:"4px 0"}}>Drug: {r.drug}</p>}
         {r.indication&&<p style={{margin:"4px 0"}}>Indication: {r.indication}</p>}
         {r.readoutSourceDate&&<p style={{margin:"4px 0"}}>Public data date: {r.readoutSourceDate}</p>}
         <a href={r.registrySourceUrl} rel="noopener noreferrer" target="_blank">ClinicalTrials.gov</a>
         {r.readoutEvidenceUrl&&r.readoutEvidenceUrl!==r.registrySourceUrl&&
           <p><a href={r.readoutEvidenceUrl} rel="noopener noreferrer" target="_blank">Readout evidence</a></p>}
        </div>
       </details>
      </td>
     </tr>)}</tbody>
    </table>
   </div>
   <div style={{display:"flex",alignItems:"center",gap:14,marginTop:12}}>
    <button type="button" disabled={currentPage===0} onClick={()=>setPage(Math.max(0,currentPage-1))}>Previous</button>
    <span style={{fontSize:12}}>Page {currentPage+1} of {maxPage}</span>
    <button type="button" disabled={currentPage>=maxPage-1} onClick={()=>setPage(Math.min(maxPage-1,currentPage+1))}>Next</button>
   </div>
   <p style={{fontSize:12,marginBottom:0}}>Provisional pre-data means registry active without confirmed readout status. Official registry results and issuer publications are distinguished. Completed does not imply released results; review priority, PDUFA action date and FDA approval remain unverified without exact application evidence.</p>
  </>}
 </section>;
}
