"use client";
import {useEffect,useMemo,useState} from "react";
import type {ActivePhase3Trial} from "../lib/phase3-active-cohorts";
import Phase3UnifiedClassifications from "./Phase3UnifiedClassifications";
import Phase3PreDataBatch from "./Phase3PreDataBatch";
import {TopPhase3ResearchExample} from "./Phase3TopAnalysis";
import CapScreenedTopPhase3Spreadsheet from "./CapScreenedTopPhase3Spreadsheet";
import {parsePhase3CensusCsv} from "../lib/phase3-census-rows";
import {classifyPhase3Readouts,type ReadoutClassification} from "../lib/phase3-public-readout";
type CohortPayload={
 asOf:string;sourceAsOf:string;totalPool:number;activeTotal:number;
 counts:{PRE_DATA:number;POST_DATA:number;HISTORICAL:number;VERIFY:number};
 promotedNcts:string[];view:string;trialCount:number;rows:ActivePhase3Trial[];
 notes:string[];
};
const th={padding:"10px",borderBottom:"2px solid #9ab6a5",textAlign:"left" as const,whiteSpace:"nowrap" as const};
const td={padding:"10px",borderBottom:"1px solid #d9e5de",textAlign:"left" as const,verticalAlign:"top" as const};
const pageSize=50;
const outcome=(r:ActivePhase3Trial)=>{
 const v=r.readoutOutcome||"";
 if(v==="MIXED_COPRIMARY_RESULTS")return "Mixed co-primary outcomes";
 if(v==="PRIMARY_ENDPOINT_MET")return "Primary endpoint met";
 if(v==="PRIMARY_ENDPOINT_NOT_MET")return "Primary endpoint not met";
 if(v==="NO_BINARY_PASS_FAIL")return "Descriptive / nonbinary";
 return r.cohort==="PRE_DATA"?"Not yet source-adjudicated":"Result posted; clinical endpoint not yet adjudicated";
};
function Sheet({kind,rows,query}:{kind:"PRE_DATA"|"POST_DATA";rows:ActivePhase3Trial[];query:string}){
 const [page,setPage]=useState(0);
 const matched=useMemo(()=>{
  const q=query.trim().toLowerCase();
  return !q?rows:rows.filter(r=>[r.nctId,r.ticker,r.company,r.drug||"",
   r.indication||"",r.registeredInterventions||"",r.registryStatus,r.readoutOutcome||""]
   .some(s=>s.toLowerCase().includes(q)));
 },[rows,query]);
 const pageCount=Math.max(1,Math.ceil(matched.length/pageSize));
 const current=Math.min(page,pageCount-1);
 const shown=matched.slice(current*pageSize,(current+1)*pageSize);
 const pre=kind==="PRE_DATA";
 return <section aria-label={pre?"Active Phase 3 pre-data spreadsheet":"Active Phase 3 post-data spreadsheet"}
  data-active-phase3-cohort={kind} style={{border:"1px solid #a5c7b2",borderRadius:12,padding:12,margin:"14px 0"}}>
  <header style={{display:"flex",justifyContent:"space-between",gap:12,flexWrap:"wrap",alignItems:"center"}}>
   <div><h2 style={{margin:"0 0 5px"}}>{pre?"TOP · Phase 3 Pre-Data":"BOTTOM · Phase 3 Post-Data"}</h2>
    <p style={{margin:"0 0 8px",fontSize:13}}>{pre?
     "Active studies without a verified public Phase 3 readout in the saved sources; not proof that results do not exist.":
     "Active studies with issuer-reported Phase 3 readouts or posted registry results, each identified by evidence type."}</p></div>
   <strong style={{fontSize:24}}>{rows.length} trials</strong>
  </header>
  <p style={{fontSize:13}}>Showing {shown.length} of {matched.length} matching records · {rows.length} total exact NCTs ·
   <a style={{marginLeft:7}} href={"/api/phase3-active-cohorts?view="+(pre?"pre":"post")+"&format=csv"}>Export this spreadsheet (CSV)</a></p>
  <div role="region" tabIndex={0} aria-label={pre?"238 pre-data trial rows":"20 post-data trial rows"}
   style={{overflowX:"auto",maxHeight:640,overflowY:"auto",border:"1px solid #d9e5de",borderRadius:8}}>
   <table style={{width:"100%",minWidth:1040,borderCollapse:"collapse",fontSize:13}}>
    <thead><tr>{["#","Ticker","NCT / registry","Company","Drug / therapy","Indication","Trial status",
     "Primary outcome","Evidence classification","Result date / source"].map(h=><th key={h} scope="col" style={th}>{h}</th>)}</tr></thead>
    <tbody>{shown.map((r,i)=><tr key={r.nctId} data-trial-id={r.nctId}>
      <td style={td}>{current*pageSize+i+1}</td>
      <td style={td}><strong>{r.ticker}</strong></td>
      <td style={td}><a href={r.registrySourceUrl} target="_blank" rel="noopener noreferrer">{r.nctId}</a></td>
      <td style={td}>{r.company}</td>
      <td style={td}>{r.drug||r.registeredInterventions||"Not source-verified"}</td>
      <td style={td}>{r.indication||"Not verified"}</td>
      <td style={td}>{r.registryStatus.replaceAll("_"," ")}</td>
      <td style={td}>{outcome(r)}</td>
      <td style={td}>{pre?"Public readout not verified":
       r.evidenceBasis==="ISSUER_READOUT"?"Issuer readout verified":"Registry results posted"}
       {r.correctionApplied&&<p style={{fontSize:11,margin:"5px 0 0"}}>Corrected from stale Pre-Data label</p>}</td>
      <td style={td}>{r.readoutSourceDate||"Not established"}
       {r.readoutEvidenceUrl&&<p style={{margin:"5px 0 0"}}><a href={r.readoutEvidenceUrl} target="_blank" rel="noopener noreferrer">Readout evidence</a></p>}</td>
     </tr>)}</tbody>
   </table>
   {matched.length===0&&<p>No records match your search.</p>}
  </div>
  <div style={{display:"flex",gap:12,alignItems:"center",flexWrap:"wrap",marginTop:12}}>
   <button type="button" disabled={current===0} onClick={()=>setPage(p=>Math.max(0,p-1))}>Previous 50</button>
   <span>Page {current+1} / {pageCount}</span>
   <button type="button" disabled={current>=pageCount-1} onClick={()=>setPage(p=>Math.min(pageCount-1,p+1))}>Next 50</button>
  </div>
 </section>;
}
/** The previous 741-trial tools are retained as historical research, never mixed
 * into the two current 258-active-study spreadsheets. Mounted on demand only. */
function LegacyArchive({query}:{query:string}){
 const [data,setData]=useState<ReadoutClassification|null>(null);
 const [error,setError]=useState("");
 useEffect(()=>{
  const ctrl=new AbortController();
  Promise.all([
   fetch("/phase3-census-2026-10-26.csv",{cache:"no-store",signal:ctrl.signal}),
   fetch("/phase3-public-readout-evidence-2026-11-01.json",{cache:"no-store",signal:ctrl.signal})
  ]).then(async ([c,e])=>{
   if(!c.ok||!e.ok)throw Error("Archived issuer research unavailable");
   return classifyPhase3Readouts(await e.json(),parsePhase3CensusCsv(await c.text()).rows);
  }).then(d=>{if(!ctrl.signal.aborted)setData(d);})
   .catch(err=>{if(!ctrl.signal.aborted&&err.name!=="AbortError")setError("Archived issuer research could not be loaded.");});
  return()=>ctrl.abort();
 },[]);
 return <div>
  <p><strong>Legacy historical research only.</strong> This older 741-study issuer snapshot, its analysis and its review candidates are excluded from the new active TOP/BOTTOM spreadsheets. Original evidence has not been deleted.</p>
  <TopPhase3ResearchExample/>
  <Phase3PreDataBatch query={query}/>
  {error&&<p role="alert">{error}</p>}
  {!data&&!error&&<p role="status">Loading historical issuer research…</p>}
  {data&&<CapScreenedTopPhase3Spreadsheet classification={data} query={query}/>}
 </div>;
}
export default function Phase3SourceOnlySheets(){
 const [data,setData]=useState<CohortPayload|null>(null);
 const [error,setError]=useState("");
 const [query,setQuery]=useState("");
 const [openHistorical,setOpenHistorical]=useState(false);
 useEffect(()=>{
  const ctrl=new AbortController();
  fetch("/api/phase3-active-cohorts?view=all",{cache:"no-store",signal:ctrl.signal})
  .then(async r=>{if(!r.ok)throw Error("Active trial source reconciliation unavailable");return await r.json() as CohortPayload;})
  .then(d=>{
   if(d.totalPool!==762||d.activeTotal!==258||d.trialCount!==258||
    d.counts.PRE_DATA!==238||d.counts.POST_DATA!==20||d.counts.HISTORICAL!==501||
    d.counts.VERIFY!==3||d.rows.length!==258||new Set(d.rows.map(r=>r.nctId)).size!==258||
    d.rows.filter(r=>r.cohort==="PRE_DATA").length!==238||
    d.rows.filter(r=>r.cohort==="POST_DATA").length!==20)
    throw Error("Active Phase 3 spreadsheets failed count/identity verification");
   if(!ctrl.signal.aborted)setData(d);
  }).catch(e=>{if(!ctrl.signal.aborted&&e.name!=="AbortError")setError(e.message);});
  return()=>ctrl.abort();
 },[]);
 if(error)return <p role="alert">{error}. No misleading trial rows have been displayed.</p>;
 if(!data)return <p role="status">Loading the reconciled 238 Pre-Data and 20 Post-Data trials…</p>;
 const pre=data.rows.filter(r=>r.cohort==="PRE_DATA");
 const post=data.rows.filter(r=>r.cohort==="POST_DATA");
 return <section data-phase3-active-top-bottom="258" data-surveys-ratings-cancelled="true" style={{padding:"8px 0"}}>
  <div style={{display:"flex",flexWrap:"wrap",alignItems:"center",gap:14}}>
   <h2 style={{margin:"4px 0"}}>Active Phase 3 · TOP and BOTTOM spreadsheets</h2>
   <strong>{data.activeTotal} total active studies</strong>
  </div>
  <p><strong>238 Pre-Data + 20 Post-Data = 258</strong>. These are active Phase 3 research classifications;
   the remaining {data.counts.HISTORICAL} closed and {data.counts.VERIFY} unverified-status trials do not appear in either active spreadsheet.</p>
  <p><strong>Five previously misclassified issuer readouts were moved into Post-Data.</strong> Existing underlying source records, history and RAAS research were not deleted.</p>
  <label style={{display:"block",margin:"12px 0"}}>Search both spreadsheets by ticker, NCT, company, drug, indication or status
   <input type="search" value={query} onChange={e=>setQuery(e.target.value)}
    placeholder="Find trial" style={{display:"block",width:"100%",maxWidth:440,padding:9,marginTop:5}}/>
  </label>
  <Sheet kind="PRE_DATA" rows={pre} query={query}/>
  <Sheet kind="POST_DATA" rows={post} query={query}/>
  <details open={openHistorical} onToggle={e=>setOpenHistorical(e.currentTarget.open)}
   style={{border:"1px solid #a5c7b2",borderRadius:10,padding:12,marginTop:14}}>
   <summary style={{cursor:"pointer",fontWeight:700}}>Historical / full 762-NCT source archive (not in active spreadsheets)</summary>
   {openHistorical&&<>
    <Phase3UnifiedClassifications/>
    <details style={{border:"1px solid #cbd8d0",borderRadius:8,padding:12,margin:"12px 0"}}>
      <summary style={{cursor:"pointer",fontWeight:700}}>Legacy issuer research tools (741-study archived snapshot)</summary>
      <LegacyArchive query={query}/>
    </details>
   </>}
  </details>
  <p style={{fontSize:12}}>Classification reconciled {data.asOf} against the source snapshot dated {data.sourceAsOf}.
   Pre-Data does not guarantee unpublished results. Posted registry results and issuer announcements are not interchangeable.
   These views do not independently establish public-company rights, current market cap or FDA/PDUFA eligibility.</p>
 </section>;
}
