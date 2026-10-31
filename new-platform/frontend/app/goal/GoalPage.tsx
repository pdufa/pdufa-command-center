"use client";
import {useEffect,useState} from "react";
import Link from "next/link";
import DailyResultsPanel from "../DailyResultsPanel";
import SiteHealthStatus from "../SiteHealthStatus";

type Counts={
 poolRecords:number;poolClinicalRecords:number|null;poolRegulatoryRecords:number|null;
 poolAsOf:string|null;poolSourceState:string;
 historicalPhase3Records:number;historicalCompletedRecords:number;
 matchedCompletedRecords:number;missingOrConflicted:number;
 qualifiedPrograms:null;
};
export default function GoalPage(){
 const [counts,setCounts]=useState<Counts|null>(null);
 const [error,setError]=useState("");
 useEffect(()=>{
  const controller=new AbortController();
  void fetch("/api/scope-funnel?view=pool&limit=1&offset=0",{cache:"no-store",signal:controller.signal})
    .then(async response=>{
      if(!response.ok)throw Error(response.status===401?"Sign in on the dashboard to view the inventory.":"Published POOL verification is unavailable.");
      const data=await response.json() as {overview?:Counts};
      if(!data.overview||!Number.isSafeInteger(data.overview.poolRecords)
        ||data.overview.qualifiedPrograms!==null)throw Error("Source integrity not verified.");
      setCounts(data.overview);
    }).catch(e=>{if(!controller.signal.aborted)setError(e instanceof Error?e.message:"Source unavailable")});
  return()=>controller.abort();
 },[]);
 const metric=(title:string,value:string,description:string)=>
  <section key={title} style={{background:"#fff",border:"1px solid #b8cfbc",borderRadius:10,padding:16,minWidth:0}}>
    <small style={{display:"block",color:"#476c55",marginBottom:8}}>{title}</small>
    <strong style={{fontSize:24}}>{value}</strong>
    <p style={{fontSize:12,lineHeight:1.5,color:"#4b6658"}}>{description}</p>
  </section>;
 return <main className="shell">
  <div className="topline">GOAL · POOL → PIPELINE</div><h1>Research Operations</h1>
  <p>Track the full master inventory and Phase 3 screening separately. Nothing in this view establishes FDA approval, a trade, or an independently verified qualified Pipeline count.</p>
  <SiteHealthStatus/>
  {error&&<p role="alert">{error}</p>}
  <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(190px,1fr))",gap:10,margin:"18px 0"}}>
    {metric("Master source records",counts?counts.poolRecords.toLocaleString():"—",
     "Published combined trial and regulatory records; not a count of unique clinical trials")}
    {metric("Historical Phase 3 census",counts?counts.historicalPhase3Records.toLocaleString():"—",
     "Dated $300M–$10B company-cap research; current capitalization still requires verification")}
    {metric("Registry completed",counts?counts.historicalCompletedRecords.toLocaleString():"—",
     "Completed registry entries are not FDA efficacy or approval decisions")}
    {metric("Exactly linked completed",counts?counts.matchedCompletedRecords.toLocaleString():"—",
     "NCT and ticker match with the master source, still needs independent qualification")}
    {metric("Qualified Pipeline programs","Not established",
     "Require source-verified current listing, market capitalization, rights and final pivotal evidence")}
  </div>
  {counts&&<p>Source state: <strong>{counts.poolSourceState}</strong> · POOL as of {counts.poolAsOf||"Not verified"} · Unlinked historical NCTs: {counts.missingOrConflicted.toLocaleString()}.</p>}
  <p><Link href="/pool">Open full POOL</Link> · <Link href="/pipeline">Review Phase 3 screening</Link> · <Link href="/scans">Inspect scans</Link> · <Link href="/restrictions">Eligibility rules</Link></p>
  <h2>Dated research results</h2>
  <DailyResultsPanel/>
 </main>;
}
