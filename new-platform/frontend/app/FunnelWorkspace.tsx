"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import styles from "./FunnelWorkspace.module.css";
import { calculateTherapyCosts, type TherapyCostComparison } from "../lib/post-phase3-population";
import { CompetitiveColumnPurposes, CompetitiveAssessmentHeaders, CompetitiveAssessmentCells } from "./CompetitiveAssessmentColumns";
import type { CompetitiveAssessment } from "../lib/competitive-assessment";
import { pacificToday, type TimelineDates } from "../lib/pipeline-timeline";
import { PipelineTimelineHeaders, PipelineTimelineCells } from "./PipelineTimelineColumns";
import PipelineFourViews from "./PipelineFourViews";

type PoolItem = {id:string;ticker:string;company?:string;drug?:string;indication?:string;stage?:string;marketCap?:number|null;capInRange?:boolean};
type ReviewItem = {
 nctId:string;ticker:string;company:string;drug:string|null;indication:string|null;
 sourceUrl:string;censusStatus:string;capUsd:number;capAsOf:string;
 poolStatus:string;postPhase3Evidence:string;qualification:string;reasons:string[];
 projectedAdoption12MonthPct?:number|null;
 therapyCostComparison?:TherapyCostComparison|null;
 commercialAssessment?:CompetitiveAssessment|null;
 timeline?:TimelineDates|null;
};
type Overview = {
 poolRecords:number;poolClinicalRecords:number|null;poolRegulatoryRecords:number|null;
 poolAsOf:string|null;poolSourceState:string;historicalPhase3Records:number;
 historicalCompletedRecords:number;matchedPhase3Records:number;matchedCompletedRecords:number;
 missingOrConflicted:number;noncompletedReadoutReview:number;qualifiedPrograms:null;censusAsOf:string;
};
type Page = {
 view:string;overview:Overview;total:number;offset:number;limit:number;
 rows:(PoolItem|ReviewItem)[];nextOffset:number|null;caveat:string;
};
const LIMIT=50;
const isReview=(r:PoolItem|ReviewItem):r is ReviewItem => "poolStatus" in r;
function formatCost(v:number|null){return v===null?"Insufficient data":v.toLocaleString("en-US",{style:"currency",currency:"USD",maximumFractionDigits:0});}
function display(v:string|number|null|undefined) {
 return v===null||v===undefined||v===""?"Not verified":String(v);
}
export default function FunnelWorkspace({section}:{section:"pool"|"pipeline"}) {
 const [reviewMode,setReviewMode]=useState(false);
 const [today,setToday]=useState("");
 useEffect(()=>{const update=()=>setToday(pacificToday());update();const timer=setInterval(update,60000);return ()=>clearInterval(timer);},[]);
 const [queryInput,setQueryInput]=useState("");
 const [query,setQuery]=useState("");
 const [offset,setOffset]=useState(0);
 const [page,setPage]=useState<Page|null>(null);
 const [error,setError]=useState("");
 const [loading,setLoading]=useState(true);
 const view=section==="pool"?"pool":reviewMode?"readout-review":"pipeline";
 useEffect(()=>{
   if(section==="pipeline"&&!reviewMode)return;
   const controller=new AbortController();
   let mounted=true;
   setLoading(true);setError("");
   const params=new URLSearchParams({view,offset:String(offset),limit:String(LIMIT)});
   if(query.trim())params.set("query",query.trim());
   void fetch("/api/scope-funnel?"+params.toString(),{cache:"no-store",signal:controller.signal})
     .then(async resp=>{
       if(!resp.ok)throw new Error(resp.status===401?"Sign in on the dashboard to view protected research data.":"Published POOL and Phase 3 census could not be jointly verified.");
       const raw:unknown=await resp.json();
       if(!raw||typeof raw!=="object")throw new Error("Invalid research response");
       const result=raw as Page;
       if(result.view!==view || !Array.isArray(result.rows) || !result.overview ||
         !Number.isSafeInteger(result.total) || result.total<0 ||
         result.offset!==offset || result.limit!==LIMIT ||
         result.rows.length>LIMIT || !result.caveat)
         throw new Error("Research reconciliation response failed validation.");
       if(mounted)setPage(result);
     }).catch(err=>{
       if(mounted && !controller.signal.aborted){setPage(null);setError(err instanceof Error?err.message:"Research data unavailable");}
     }).finally(()=>{if(mounted)setLoading(false)});
   return ()=>{mounted=false;controller.abort()};
 },[section,reviewMode,view,offset,query]);
 function applySearch(e:FormEvent<HTMLFormElement>) {
   e.preventDefault();setOffset(0);setQuery(queryInput);
 }
 function changeMode(review:boolean){setReviewMode(review);setOffset(0);}
 const overview=page?.overview;
 const first=page&&page.total?offset+1:0,last=page?Math.min(offset+page.rows.length,page.total):0;
 return <main className={styles.root}>
   <header className={styles.header}>
     <p className={styles.eyebrow}>PDUFA · SINGLE POOL → PIPELINE FUNNEL</p>
     <h1>{section==="pool"?"POOL — Master Trial Universe":"PIPELINE — $300M–$10B Post–Phase 3"}</h1>
     <p>{section==="pool"?
       "Unrestricted published research inventory. A Pipeline filter never deletes or changes a POOL record.":
       "Read-only Phase 3 eligibility review, linked by exact NCT and ticker to the master POOL. Only registry-completed, exact-linked trials appear in the initial screening queue."}</p>
     <div className={styles.links}>
       <Link href="/pool">Master POOL</Link>
       <Link href="/pipeline">Post–Phase 3 PIPELINE</Link>
       <Link href="/patient-population">#1 Patient Population</Link>
       {section==="pipeline"&&<a href="/api/scope-funnel?view=census-review&format=csv" download>Export all 741 historical census candidates (CSV)</a>}
     </div>
   </header>
   <section className={styles.notice}>
     <strong>Qualification rules:</strong> U.S.-listed publicly traded issuer; current sourced market capitalization $300 million–$10 billion inclusive;
     completed pivotal Phase 3 <em>or</em> independently verified final pivotal readout of the exact drug–indication program.
     No future-only readouts or Phase 1/2 records qualify. No PDUFA-day limit. Results can be positive, negative or mixed.
     All source gaps remain review items, never presumptive passes or failures.
   </section>
   {overview && <section className={styles.metrics} aria-label="Scope reconciliation counts">
     <div><span>Source POOL records</span><strong>{overview.poolRecords.toLocaleString()}</strong><small>Trials plus published regulatory-event records; not solely distinct trials</small></div>
     <div><span>Historical cap-screened Phase 3 NCTs</span><strong>{overview.historicalPhase3Records}</strong><small>October 26 research census</small></div>
     <div><span>Registry-completed records</span><strong>{overview.historicalCompletedRecords}</strong><small>Historical, not efficacy approval</small></div>
     <div><span>Completed exact-linked records</span><strong>{overview.matchedCompletedRecords}</strong><small>Matched NCT + ticker in POOL</small></div>
     <div><span>Fully verified qualified programs</span><strong>Not established</strong><small>Current listing, cap, readout and rights checks outstanding</small></div>
   </section>}
   <section className={styles.notice}>
     <strong>Source transparency:</strong> the Phase 3 cap values are historical research pointers, not current market quotations.
     The POOL is read from the published workspace; 741 Phase 3 NCT rows come from the October 26 census.
     These independently sourced universes are reconciled by exact identity rather than treated as identical. 
     {overview && <> POOL source state: <strong>{overview.poolSourceState}</strong>;
       as of {display(overview.poolAsOf)}. {overview.missingOrConflicted} of the 741 historical NCT rows lack an exact unconflicted POOL match.</>}
   </section>
   {section==="pipeline" && <div className={styles.modeTabs}>
     <button type="button" aria-pressed={!reviewMode} onClick={()=>changeMode(false)}
       className={!reviewMode?styles.selected:undefined}>Completed & exact-linked (research queue)</button>
     <button type="button" aria-pressed={reviewMode} onClick={()=>changeMode(true)}
       className={reviewMode?styles.selected:undefined}>Unmatched / verify final readout</button>
   </div>}
   {section==="pipeline"&&!reviewMode&&<PipelineFourViews />}
   {(section==="pool"||reviewMode)&&<section className={styles.panel}>
     <div className={styles.headline}>
       <h2>{section==="pool"?"Preserved published POOL records":reviewMode?"Unresolved census research records":"Post–Phase 3 screening — awaiting qualification"}</h2>
       <form onSubmit={applySearch} className={styles.search}>
         <input aria-label="Search ticker, trial, company, drug or indication" type="search" value={queryInput}
           onChange={event=>setQueryInput(event.target.value)} placeholder="Ticker, NCT, drug or indication" maxLength={100}/>
         <button type="submit">Search</button>
         <button type="button" onClick={()=>{setQuery("");setQueryInput("");setOffset(0)}}>Clear</button>
       </form>
     </div>
     {error && <p className={styles.error} role="alert">{error} <Link href="/">Dashboard / sign in</Link></p>}
     {loading && <p role="status">Verifying source inventories and eligibility evidence…</p>}
     {!loading && page && <>
       <p className={styles.muted} role="status">Showing {first}–{last} of {page.total.toLocaleString()} records in this view.</p>
       {page.total===0 && <p>No qualifying research rows found in this selected view. A zero row count does not establish zero eligible products.</p>}
       {section==="pipeline"&&<><p className={styles.muted}>Timeline columns count Pacific calendar days from the verified public Phase 3 readout release to today and to the FDA PDUFA target. Research ends at PDUFA − 3. Unverified dates never become numerical countdowns.</p><p className={styles.muted}>Competitive columns are source-gated. A blank assessment is neither zero nor evidence of failure. Expand each cell for its reason, exact purpose and required verification.</p><CompetitiveColumnPurposes /></>}
       <div className={styles.scroll}><table className={styles.table}>
         <thead><tr>
           {section==="pool"?
             ["Source ID","Ticker","Company","Drug","Indication","Recorded stage","Cap source value","Record type"].map(k=><th key={k}>{k}</th>):
             <>{["NCT","Ticker","Company","Drug","Indication"].map(k=><th key={k}>{k}</th>)}<PipelineTimelineHeaders /><CompetitiveAssessmentHeaders />{["Registry status","Cap at census","POOL match","Screening status","Current SOC cost ($/12 mo)","Proposed cost ($/12 mo)","Details"].map(k=><th key={k}>{k}</th>)}</>
           }
         </tr></thead>
         <tbody>{page.rows.map(r=>isReview(r)?
           <tr key={r.nctId}>
             <td><a href={r.sourceUrl} target="_blank" rel="noopener noreferrer">{r.nctId}</a></td>
             <td>{r.ticker}</td><td>{r.company}</td><td>{display(r.drug)}</td><td>{display(r.indication)}</td>
             <PipelineTimelineCells dates={r.timeline} today={today}/>
             <CompetitiveAssessmentCells row={r}/>
             <td>{r.censusStatus}</td><td>${r.capUsd.toLocaleString()}<small>as of {r.capAsOf.slice(0,10)}</small></td>
             <td>{r.poolStatus}</td><td>{r.qualification}</td>
             <td>{formatCost(calculateTherapyCosts(r.therapyCostComparison).currentUsd)}</td>
             <td>{formatCost(calculateTherapyCosts(r.therapyCostComparison).proposedUsd)}</td>
             <td><details><summary>Why?</summary><ul>{r.reasons.map(s=><li key={s}>{s}</li>)}</ul></details>
             <details><summary>Regimen and pricing evidence</summary>
               <p>Current: {r.therapyCostComparison?.current?.therapy || "Not researched"} — {r.therapyCostComparison?.current?.regimen || "Regimen unverified"}</p>
               <p>Proposed: {r.therapyCostComparison?.proposed?.therapy || "Not researched"} — {r.therapyCostComparison?.proposed?.regimen || "Regimen unverified"}</p>
               <p>Costs: first 12 months per U.S. treated patient; source and matching price bases required. Prelaunch prices can only be modeled where evidence exists.</p>
             </details></td>
           </tr>:
           <tr key={r.id}>
             <td>{r.id}</td><td>{r.ticker}</td><td>{display(r.company)}</td>
             <td>{display(r.drug)}</td><td>{display(r.indication)}</td>
             <td>{display(r.stage)}</td><td>{typeof r.marketCap==="number"?`$${r.marketCap.toLocaleString()}`:"Not verified"}</td>
             <td>{r.id.startsWith("TRIAL|")?"Trial source record":r.id.startsWith("APPLICATION|")?"Regulatory record":r.id.startsWith("RESULT|")?"Result record":"Other source record"}</td>
           </tr>)}</tbody>
       </table></div>
       <div className={styles.pagination}>
         <button type="button" disabled={offset===0||loading} onClick={()=>setOffset(Math.max(0,offset-LIMIT))}>Previous</button>
         <span>Page {Math.floor(offset/LIMIT)+1} of {Math.max(1,Math.ceil(page.total/LIMIT))}</span>
         <button type="button" disabled={page.nextOffset===null||loading} onClick={()=>setOffset(page.nextOffset!)}>Next</button>
       </div>
     </>}
   </section>}
   <p className={styles.footer}>Research-only scope separation. No source records are deleted, no scans or GEM presets are modified, and this does not certify FDA approval readiness or establish a live qualified-program count.</p>
 </main>;
}
