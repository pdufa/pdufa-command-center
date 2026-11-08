"use client";
import {useEffect,useState} from "react";
import {parseRegistryPostingSnapshot,type RegistryPostingRow,type RegistryPostingSnapshot} from "../lib/phase3-registry-posting";
const card:React.CSSProperties={border:"1px solid #bbd0c2",borderRadius:9,padding:12,marginTop:14};
function PostingTable({title,rows,query}:{title:string;rows:RegistryPostingRow[];query:string}){
 const filtered=rows.filter(row=>!query||[row.nctId,row.ticker,row.company,row.registryStatus].some(v=>v.toLowerCase().includes(query)));
 return <section style={card}><h3>{title} · {filtered.length.toLocaleString()} records</h3>
 <div style={{overflowX:"auto",maxHeight:650}}>
 <table style={{width:"100%",borderCollapse:"collapse",fontSize:13}}>
 <thead><tr><th>Ticker</th><th>NCT</th><th>Company</th><th>Registry status</th><th>First results posted</th></tr></thead>
 <tbody>{filtered.map(row=><tr key={row.nctId} style={{borderTop:"1px solid #ddd"}}>
 <td>{row.ticker}</td><td><a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">{row.nctId}</a></td>
 <td>{row.company}</td><td>{row.registryStatus}</td><td>{row.resultsFirstPostedDate||"Not established"}</td>
 </tr>)}</tbody></table></div></section>;
}
export default function Phase3RegistryPostingSheets(){
 const [data,setData]=useState<RegistryPostingSnapshot|null>(null);
 const [error,setError]=useState("");
 const [query,setQuery]=useState("");
 useEffect(()=>{
  const ctrl=new AbortController();
  void fetch("/phase3-registry-postings-current.json",{cache:"no-store",signal:ctrl.signal})
   .then(async r=>{if(r.ok)return parseRegistryPostingSnapshot(await r.json());
     const fallback=await fetch("/phase3-registry-postings-2026-10-18.json",{cache:"no-store",signal:ctrl.signal});
     if(!fallback.ok)throw Error("Registry source unavailable");
     return parseRegistryPostingSnapshot(await fallback.json());})
   .then(result=>{if(!ctrl.signal.aborted)setData(result)})
   .catch(()=>{if(!ctrl.signal.aborted)setError("Registry results-posting source unavailable.")});
  return ()=>ctrl.abort();
 },[]);
 return <section style={{margin:"16px auto",maxWidth:1250,padding:12}}>
 <h2>Phase 3 ClinicalTrials.gov results-posting records</h2>
 <p>Source-only registry evidence. No survey questions, ratings, or survey background requests.</p>
 {error?<p role="alert">{error}</p>:!data?<p>Loading registry records…</p>:<>
 <p>{data.total.toLocaleString()} NCT records · snapshot {data.date} · registry posting does not establish FDA acceptance.</p>
 <input aria-label="Search clinical trial records" type="search" value={query} onChange={e=>setQuery(e.target.value.toLowerCase())} placeholder="Search trial, ticker, company…" />
 <PostingTable title="Results not posted" rows={data.before} query={query}/>
 <PostingTable title="Results posted" rows={data.after} query={query}/>
 </>}</section>;
}
