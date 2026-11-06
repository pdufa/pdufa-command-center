"use client";
import {useEffect,useMemo,useState} from "react";

type Trial={
 rank:number;nctId:string;ticker:string;company:string;indication:string;
 registryStatus:string;classificationCode:string;unscored:number;
 documentedFacts:number;predicted:number;observed:number;endpointReviewed:boolean;
 missingProtocol:boolean;missingFDAApplication:boolean;missingPDUFA:boolean;
 clinicalTrialUrl:string;
};
type Company={
 rank:number;ticker:string;company:string;trials:number;
 outstanding:number;averageOutstanding:number;maxUnscored:number;
 mostIncompleteNct:string;endpointNotReviewed:number;missingPDUFA:number;
};
type Ranking={
 asOf:string;generatedAt:string;source:string;scoringNote:string;
 trialsCount:number;companiesCount:number;totalUnscored:number;
 trials:Trial[];companies:Company[];
};
const th={textAlign:"left" as const,padding:"12px 10px",borderBottom:"2px solid #bad0bc",
 background:"#e7f1e7",position:"sticky" as const,top:0,zIndex:1,whiteSpace:"nowrap" as const};
const td={textAlign:"left" as const,padding:"10px",borderBottom:"1px solid #e2eae0",
 verticalAlign:"top" as const};
const n=(value:number)=>value.toLocaleString("en-US");
const pageSize=40;
export default function Phase3OutstandingRankedPage(){
 const [data,setData]=useState<Ranking|null>(null);
 const [error,setError]=useState("");
 const [mode,setMode]=useState<"trials"|"companies">("trials");
 const [search,setSearch]=useState("");
 const [ticker,setTicker]=useState("");
 const [page,setPage]=useState(0);
 const [sort,setSort]=useState<"high"|"low">("high");
 useEffect(()=>{
  const controller=new AbortController();
  fetch("/api/phase3-outstanding-ranked",{cache:"no-store",signal:controller.signal})
   .then(async res=>{if(!res.ok)throw Error("Ranking service unavailable");return await res.json() as Ranking;})
   .then(result=>{
    if(result.trialsCount!==762||result.trials.length!==762||
       new Set(result.trials.map(x=>x.nctId)).size!==762||
       result.companies.length!==result.companiesCount||
       result.trials.reduce((s,x)=>s+x.unscored,0)!==result.totalUnscored)
     throw Error("762-trial ranking integrity check failed");
    if(!controller.signal.aborted)setData(result);
   }).catch(e=>{if(!controller.signal.aborted)setError(e instanceof Error?e.message:"Ranking unavailable");});
  return ()=>controller.abort();
 },[]);
 const filteredTrials=useMemo(()=>{
  const q=search.trim().toLowerCase();
  const arr=(data?.trials||[]).filter(r=>
    (!ticker||r.ticker===ticker)&&
    (!q||[r.nctId,r.company,r.ticker,r.indication,r.registryStatus]
      .some(s=>s.toLowerCase().includes(q))));
  return sort==="low"?arr.reverse():arr;
 },[data,search,ticker,sort]);
 const filteredCompanies=useMemo(()=>{
  const q=search.trim().toLowerCase();
  const arr=(data?.companies||[]).filter(c=>
    !q||[c.company,c.ticker,c.mostIncompleteNct].some(s=>s.toLowerCase().includes(q)));
  return sort==="low"?arr.reverse():arr;
 },[data,search,sort]);
 const total=mode==="trials"?filteredTrials.length:filteredCompanies.length;
 const pages=Math.max(1,Math.ceil(total/pageSize));
 const safePage=Math.min(page,pages-1);
 const trialsShown=filteredTrials.slice(safePage*pageSize,(safePage+1)*pageSize);
 const companiesShown=filteredCompanies.slice(safePage*pageSize,(safePage+1)*pageSize);
 const changeMode=(m:"trials"|"companies")=>{setMode(m);setSearch("");setTicker("");setPage(0);setSort("high");};
 const showCompany=(c:Company)=>{
  setMode("trials");setTicker(c.ticker);setSearch("");setPage(0);setSort("high");
 };
 return <main className="shell" style={{maxWidth:1400}}>
  <div className="topline">PDUFA / PHASE 3 / EVIDENCE BACKLOG</div>
  <h1 style={{marginBottom:7}}>Outstanding trial research — ranked</h1>
  <p className="subtle" style={{marginBottom:18}}>
   Every trial is ranked from the most unscored of its 30 assessments to the least.
   Company totals sum missing assessments across all of that company&apos;s trials.
   This is separate from the number of blank cells in the 190-column export.
  </p>
  {error&&<div className="banner" role="alert">Unable to load live ranking: {error}</div>}
  {!data&&!error&&<div className="panel" role="status">Loading 762-trial missing-data ranking…</div>}
  {data&&<>
   <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(150px,1fr))",gap:10,marginBottom:18}}>
    {[
     ["Trials ranked",n(data.trialsCount)],
     ["Companies",n(data.companiesCount)],
     ["Total unscored",n(data.totalUnscored)],
     ["Worst trial",data.trials[0].unscored+"/30"]
    ].map(([label,value])=><div key={label} className="panel" style={{padding:14,boxShadow:"none"}}>
     <div style={{fontSize:12,color:"#5a6b5a",fontWeight:700}}>{label}</div>
     <div style={{fontSize:27,fontWeight:800,marginTop:5}}>{value}</div>
    </div>)}
   </div>
   <section className="panel" style={{padding:14}}>
    <div style={{display:"flex",flexWrap:"wrap",alignItems:"center",gap:9,marginBottom:14}}>
     <button onClick={()=>changeMode("trials")} aria-pressed={mode==="trials"}
       style={{background:mode==="trials"?"#173f2b":"#fff",color:mode==="trials"?"white":"#173f2b"}}>All 762 trials</button>
     <button onClick={()=>changeMode("companies")} aria-pressed={mode==="companies"}
       style={{background:mode==="companies"?"#173f2b":"#fff",color:mode==="companies"?"white":"#173f2b"}}>Companies ({data.companiesCount})</button>
     <div style={{flex:"1 1 160px"}}/>
     <a style={{fontWeight:700,fontSize:13}} href="/api/phase3-outstanding-ranked?format=trials.csv">Download ranked trials CSV</a>
     <a style={{fontWeight:700,fontSize:13}} href="/api/phase3-outstanding-ranked?format=companies.csv">Download companies CSV</a>
    </div>
    {ticker&&mode==="trials"&&<div style={{marginBottom:12,padding:9,background:"#e6f1e9",borderRadius:7}}>
     Showing {ticker} only. <button className="secondary" style={{padding:"5px 10px",marginLeft:6}} onClick={()=>{setTicker("");setPage(0);}}>Clear company filter</button>
    </div>}
    <div style={{display:"flex",flexWrap:"wrap",alignItems:"flex-end",gap:12,marginBottom:12}}>
     <label style={{display:"flex",flexDirection:"column",gap:5,minWidth:210,flex:"1 1 250px"}}>
      Search {mode==="trials"?"company, ticker, trial or indication":"company or ticker"}
      <input value={search} onChange={e=>{setSearch(e.target.value);setPage(0);}}
       placeholder="Type to filter the table…" aria-label="Search ranking table"/>
     </label>
     <label style={{display:"flex",flexDirection:"column",gap:5}}>
      Sort order
      <select value={sort} onChange={e=>{setSort(e.target.value as "high"|"low");setPage(0);}}>
       <option value="high">Most outstanding first</option>
       <option value="low">Least outstanding first</option>
      </select>
     </label>
    </div>
    <p style={{fontSize:13,color:"#516354",margin:"6px 0 13px"}}>
     Showing {total? n(safePage*pageSize+1):0}–{n(Math.min((safePage+1)*pageSize,total))} of {n(total)}
     {mode==="trials"?" trials":" companies"}.
     {mode==="trials"?" Missing means UNSCORED, not necessarily unavailable online.":" Select a company to see its trial rankings."}
    </p>
    <div role="region" aria-label={mode==="trials"?"Ranked Phase 3 trials":"Ranked companies"}
     style={{overflowX:"auto",maxHeight:"68vh",overflowY:"auto",border:"1px solid #dce5dc",borderRadius:9}}>
     {mode==="trials"?<table style={{borderCollapse:"collapse",width:"100%",minWidth:910,fontSize:13}}>
      <thead><tr>
       {["Rank","Company / ticker","Trial NCT","Indication","Unscored / 30","Source facts","Endpoint reviewed","Registry status"].map(h=><th key={h} style={th}>{h}</th>)}
      </tr></thead>
      <tbody>{trialsShown.map((r,i)=><tr key={r.nctId} style={{background:i%2?"#f5f8f4":"#fff"}}>
       <td style={td}><strong>#{r.rank}</strong></td>
       <td style={{...td,minWidth:180}}><strong>{r.company}</strong><div style={{color:"#627666"}}>{r.ticker}</div></td>
       <td style={td}><a href={r.clinicalTrialUrl} target="_blank" rel="noopener noreferrer">{r.nctId}</a></td>
       <td style={{...td,minWidth:170,maxWidth:330}}>{r.indication||"Not recorded"}</td>
       <td style={td}><strong style={{color:r.unscored>=22?"#a12e1c":"#1c4631",fontSize:15}}>{r.unscored}</strong><span style={{color:"#7c8c7d"}}> / 30</span></td>
       <td style={td}>{r.documentedFacts}</td>
       <td style={td}>{r.endpointReviewed?"Yes":"No"}</td>
       <td style={td}>{r.registryStatus.replaceAll("_"," ").toLowerCase()}</td>
      </tr>)}</tbody>
     </table>:<table style={{borderCollapse:"collapse",width:"100%",minWidth:830,fontSize:13}}>
      <thead><tr>
       {["Rank","Company / ticker","Trials","Total unscored","Average per trial","Worst trial","Endpoints not reviewed","PDUFA unverified","Open"].map(h=><th key={h} style={th}>{h}</th>)}
      </tr></thead>
      <tbody>{companiesShown.map((c,i)=><tr key={c.ticker} style={{background:i%2?"#f5f8f4":"#fff"}}>
       <td style={td}><strong>#{c.rank}</strong></td>
       <td style={{...td,minWidth:185}}><strong>{c.company}</strong><div style={{color:"#627666"}}>{c.ticker}</div></td>
       <td style={td}>{c.trials}</td>
       <td style={td}><strong style={{fontSize:15}}>{n(c.outstanding)}</strong></td>
       <td style={td}>{c.averageOutstanding.toFixed(2)} / 30</td>
       <td style={td}>{c.mostIncompleteNct} ({c.maxUnscored})</td>
       <td style={td}>{c.endpointNotReviewed}</td>
       <td style={td}>{c.missingPDUFA}</td>
       <td style={td}><button className="secondary" style={{padding:"6px 10px",fontSize:12}} onClick={()=>showCompany(c)}>See trials</button></td>
      </tr>)}</tbody>
     </table>}
    </div>
    <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",gap:10,marginTop:14}}>
     <button className="secondary" disabled={safePage<=0} onClick={()=>setPage(p=>Math.max(0,p-1))}>Previous</button>
     <span style={{fontSize:13,fontWeight:700}}>Page {safePage+1} of {pages}</span>
     <button className="secondary" disabled={safePage>=pages-1} onClick={()=>setPage(p=>Math.min(pages-1,p+1))}>Next</button>
    </div>
   </section>
   <p className="subtle" style={{marginTop:13}}>Source: production Phase 3 missing-data audit, 762 unique NCTs, 30 assessments per trial.
    Generated: {new Date(data.generatedAt).toLocaleString()}. These are outstanding assessment counts, not 192 columns of missing data.
   </p>
  </>}
 </main>;
}
