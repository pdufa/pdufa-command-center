"use client";
import {useEffect,useMemo,useState} from "react";
import {parsePhase3CensusCsv} from "../lib/phase3-census-rows";
import {classifyPhase3Readouts,type ReadoutRow,type ReadoutClassification} from "../lib/phase3-public-readout";

const perPage=50;
const card:React.CSSProperties={border:"1px solid #b9d0c1",borderRadius:9,padding:14,marginTop:14,background:"#fff"};
type Bucket="pre"|"post"|"unverified";
const descriptions:Record<Bucket,string>={
 pre:"Issuer readout not yet reported as of the saved evidence review",
 post:"Public issuer Phase 3 readout documented",
 unverified:"Issuer readout status not independently established"
};
function ReadoutTable({kind,rows,query}:{kind:Bucket;rows:ReadoutRow[];query:string}){
 const [page,setPage]=useState(0);
 const filtered=useMemo(()=>rows.filter(r=>!query||
  [r.nctId,r.ticker,r.company,r.status,r.evidence?.drug||"",r.evidence?.indication||""]
   .some(v=>v.toLowerCase().includes(query))),[rows,query]);
 const pages=Math.max(1,Math.ceil(filtered.length/perPage));
 const active=Math.min(page,pages-1);
 return <section style={card} aria-label={descriptions[kind]}>
  <h3>{descriptions[kind]} · {filtered.length.toLocaleString()}</h3>
  <div style={{overflowX:"auto"}}>
  <table style={{borderCollapse:"collapse",width:"100%",minWidth:760,fontSize:13}}>
   <thead><tr>{["Ticker","NCT ID","Company","Treatment / indication","Registry status","Issuer evidence"].map(h=>
    <th key={h} style={{textAlign:"left",padding:9,borderBottom:"1px solid #ddd"}}>{h}</th>)}</tr></thead>
   <tbody>{filtered.slice(active*perPage,(active+1)*perPage).map(r=><tr key={r.nctId}>
    <td style={{padding:9,borderBottom:"1px solid #eee"}}>{r.ticker}</td>
    <td style={{padding:9,borderBottom:"1px solid #eee"}}><a href={r.sourceUrl} target="_blank" rel="noopener noreferrer">{r.nctId}</a></td>
    <td style={{padding:9,borderBottom:"1px solid #eee"}}>{r.company}</td>
    <td style={{padding:9,borderBottom:"1px solid #eee"}}>{r.evidence?.drug||"Not established"}{r.evidence?.indication?" · "+r.evidence.indication:""}</td>
    <td style={{padding:9,borderBottom:"1px solid #eee"}}>{r.status.replaceAll("_"," ")}</td>
    <td style={{padding:9,borderBottom:"1px solid #eee"}}>{r.evidence?<><a href={r.evidence.evidenceUrl} target="_blank" rel="noopener noreferrer">Original source</a><div>{r.evidence.evidenceDate}</div></>:"Not verified"}</td>
   </tr>)}</tbody>
  </table></div>
  <div style={{display:"flex",gap:12,alignItems:"center",marginTop:12}}>
   <button disabled={active===0} onClick={()=>setPage(Math.max(0,active-1))}>Previous</button>
   <span>Page {active+1} of {pages}</span>
   <button disabled={active>=pages-1} onClick={()=>setPage(active+1)}>Next</button>
  </div>
 </section>;
}
export default function Phase3ReadoutSheets(){
 const [data,setData]=useState<ReadoutClassification|null>(null);
 const [error,setError]=useState("");
 const [query,setQuery]=useState("");
 useEffect(()=>{
  const controller=new AbortController();
  void Promise.all([
   fetch("/phase3-census-2026-10-26.csv",{cache:"no-store",signal:controller.signal}),
   fetch("/phase3-public-readout-evidence-2026-11-01.json",{cache:"no-store",signal:controller.signal})
  ]).then(async ([census,evidence])=>{
   if(!census.ok||!evidence.ok)throw Error("Clinical source snapshot unavailable");
   return classifyPhase3Readouts(await evidence.json(),parsePhase3CensusCsv(await census.text()).rows);
  }).then(result=>{if(!controller.signal.aborted)setData(result)})
   .catch(()=>{if(!controller.signal.aborted)setError("Original Phase 3 research could not be verified; no study status inferred.")});
  return ()=>controller.abort();
 },[]);
 return <main style={{maxWidth:1300,margin:"24px auto",padding:16,color:"#163e29",fontFamily:"system-ui,sans-serif"}}>
  <h1>Phase 3 trial readout evidence</h1>
  <p>ClinicalTrials.gov census and source-linked issuer announcements. Registry completion is not proof of an issuer readout or FDA approval.</p>
  {error?<p role="alert">{error}</p>:!data?<p role="status">Loading source-verified Phase 3 records…</p>:<>
   <p>{data.total.toLocaleString()} exact-NCT records · census {data.censusDate} · issuer review {data.sourceAsOf}</p>
   <label>Search trials <input type="search" value={query} onChange={e=>setQuery(e.target.value.toLowerCase())} placeholder="NCT, ticker, drug, company…" /></label>
   <ReadoutTable kind="pre" rows={data.pre} query={query}/>
   <ReadoutTable kind="post" rows={data.post} query={query}/>
   <ReadoutTable kind="unverified" rows={data.unverified} query={query}/>
  </>}
 </main>;
}
