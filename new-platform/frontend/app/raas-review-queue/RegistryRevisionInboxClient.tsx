"use client";
import {useMemo,useState} from "react";
import Link from "next/link";
import type {RaasRegistryRevisionReviewInbox}
 from "../../lib/raas-registry-revision-review-inbox";

const style={border:"1px solid #c7dbc9",borderRadius:7,
 background:"#fff",padding:"8px 11px",fontSize:12,color:"#1b4a33"} as const;
const limit=12;
export default function RegistryRevisionInboxClient({
 inbox,initialNctId="",initialMetricId=""
}:{
 inbox:RaasRegistryRevisionReviewInbox;
 initialNctId?:string;initialMetricId?:string;
}){
 const [nct,setNct]=useState(initialNctId);
 const [metric,setMetric]=useState(initialMetricId);
 const [stage,setStage]=useState<"all"|"pre"|"post">("all");
 const [version,setVersion]=useState<"all"|"current"|"superseded">("all");
 const [page,setPage]=useState(0);
 const filtered=useMemo(()=>inbox.tasks.filter(t=>
  (!nct||[t.nctId,t.ticker].some(x=>x.toLowerCase().includes(nct.trim().toLowerCase())))&&
  (!metric||[t.metricId,t.metricName].some(x=>
   x.toLowerCase().includes(metric.trim().toLowerCase())))&&
  (stage==="all"||t.metricStage===stage)&&
  (version==="all"||
   (version==="current"&&t.sourceMatch==="MATCHES_SAVED_REGISTRY")||
   (version==="superseded"&&t.sourceMatch!=="MATCHES_SAVED_REGISTRY"))
 ),[inbox.tasks,nct,metric,stage,version]);
 const pages=Math.max(1,Math.ceil(filtered.length/limit));
 const current=Math.min(page,pages-1);
 const shown=filtered.slice(current*limit,(current+1)*limit);
 const clear=()=>{setNct("");setMetric("");setStage("all");
  setVersion("all");setPage(0);};
 const sourceReady=inbox.auditState!=="AWAITING_FIRST_COMPARATIVE_SCAN";
 return <section data-raas-registry-metric-review-inbox="unapproved"
  id="raas-source-change-review-inbox"
  style={{display:"grid",gap:12,margin:"18px 0"}}>
  <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(135px,1fr))",gap:8}}>
   {([
    [inbox.uniqueTrialMetricTasks,"Exact trial/metric research alerts"],
    [inbox.uniqueNcts,"Distinct NCTs with metric alerts"],
    [inbox.existingProvisionalReviewPairs,"Alerts overlapping existing provisional review tasks"],
    [inbox.supersededOrUnsyncedTasks,"Alerts whose source version no longer matches current snapshot"],
    [inbox.independentlyApprovedMetrics,"Authenticated independent metric approvals"]
   ] as const).map(([value,label])=>
    <div key={label} style={{...style,padding:12,background:"#f5faf7"}}>
     <strong style={{display:"block",fontSize:24}}>{value}</strong>
     <span style={{fontSize:11}}>{label}</span>
    </div>)}
  </div>
  <p style={{fontSize:12,lineHeight:1.6,margin:0}}>
   <strong>Source audit:</strong> {inbox.auditState.replaceAll("_"," ")}
   {" "}· {inbox.lastComparedAt?
    "last compared "+inbox.lastComparedAt:
    "no completed source comparison recorded"}.
   {" "}These are additional <strong>source-revision investigation tasks</strong>,
   not additional provisional grades; the independent 82-packet queue below
   retains its original identities and scores. Research TOP/BOTTOM routing
   never proves the public-readout stage. No reviewer receipt, source update
   or previous AI check authorizes automatic RAAS approval.
  </p>
  <div style={{display:"flex",flexWrap:"wrap",alignItems:"end",gap:8}}>
   <label style={{display:"grid",gap:4,fontWeight:700,fontSize:11}}>
    Trial/ticker
    <input aria-label="Filter source revision tasks by NCT or ticker"
     value={nct} onChange={e=>{setNct(e.target.value);setPage(0);}}
     maxLength={40} placeholder="NCT or ticker" style={style}/>
   </label>
   <label style={{display:"grid",gap:4,fontWeight:700,fontSize:11}}>
    Metric
    <input aria-label="Filter source revision tasks by RAAS metric"
     value={metric} onChange={e=>{setMetric(e.target.value);setPage(0);}}
     maxLength={60} placeholder="post-1-5" style={style}/>
   </label>
   <label style={{display:"grid",gap:4,fontWeight:700,fontSize:11}}>
    Research metric stage
    <select aria-label="Filter source revision tasks by stage"
     value={stage} onChange={e=>{setStage(e.target.value as typeof stage);setPage(0);}}
     style={style}>
     <option value="all">Both TOP and BOTTOM</option>
     <option value="pre">TOP research</option>
     <option value="post">BOTTOM research</option>
    </select>
   </label>
   <label style={{display:"grid",gap:4,fontWeight:700,fontSize:11}}>
    Registry source version
    <select aria-label="Filter current and superseded source revisions"
     value={version} onChange={e=>{setVersion(e.target.value as typeof version);setPage(0);}}
     style={style}>
     <option value="all">All versions</option>
     <option value="current">Matches latest published source</option>
     <option value="superseded">Superseded or unsynced</option>
    </select>
   </label>
   <button type="button" onClick={clear} style={style}>Clear selections</button>
   <a href="/api/raas-registry-revision-review-tasks" download
    style={{...style,fontWeight:750}}>Export review alerts (CSV)</a>
   <Link href="/raas-evidence-changes">Full immutable source-change history</Link>
  </div>
  <p role="status" style={{fontSize:12}}>
   {filtered.length} matching metric alerts · showing{" "}
   {filtered.length?current*limit+1:0}–{Math.min((current+1)*limit,filtered.length)}
   {" "}· no approved metrics
  </p>
  {shown.length===0?<p style={{...style,padding:14,background:"#f7faf7"}}>
   {sourceReady?
    "There are no source-revision metric alerts matching these filters. A completed registry comparison does not constitute independent FDA or clinical validation.":
    "Awaiting a completed source comparison. There are no historical review alerts to display yet; this is not a claim that no source changes occurred."}
  </p>:<div style={{display:"grid",gap:9}}>
   {shown.map(task=><details key={task.id}
    data-raas-source-revision-metric-task={task.id}
    style={{border:"1px solid #c6ddcd",borderRadius:9,overflow:"hidden",background:"#fff"}}>
    <summary style={{cursor:"pointer",padding:12,display:"flex",
     flexWrap:"wrap",gap:12,justifyContent:"space-between",
     alignItems:"center",background:"#f3f9f5"}}>
     <span style={{display:"grid",gap:4,flex:"1 1 170px"}}>
      <strong>{task.ticker} · {task.nctId}</strong>
      <small>{task.metricStage==="pre"?"TOP":"BOTTOM"} candidate metric {task.metricId}</small>
      <small>Observed {task.observedAt}</small>
     </span>
     <span style={{display:"grid",gap:4,flex:"1 1 200px"}}>
      <strong>{task.metricName}</strong>
      <small>{task.changeCategories.join(", ").replaceAll("_"," ").toLowerCase()}</small>
      <small>{task.revisionCountForMetric} observed source revision(s) for this trial/metric</small>
     </span>
     <strong style={{fontSize:11}}>
      {task.sourceMatch==="MATCHES_SAVED_REGISTRY"?
       "Current version · review needed ▸":
       "Version superseded/unsynced · recheck ▸"}
     </strong>
    </summary>
    <div style={{padding:13,display:"grid",gap:9,fontSize:12,lineHeight:1.65}}>
     <p style={{margin:0}}><strong>Research-routing stage:</strong>{" "}
      {task.metricStage==="pre"?"TOP pre-readout":"BOTTOM post-readout"}
      {" "}metric definition only. The actual public-readout timing,
      exact drug and indication, and eligible Pipeline status still need
      independent primary-source verification.</p>
     <p style={{margin:0}}><strong>Current saved registry matching:</strong>{" "}
      {task.sourceMatch.replaceAll("_"," ").toLowerCase()}.
      {" "}New observed hash {task.newSourceHash.slice(0,16)}…;
      latest saved hash {task.currentRegistryHash.slice(0,16)}… .
      Check the complete historical receipt if this alert is superseded.</p>
     <p style={{margin:0}}><strong>Prior provisional exact NCT/metric research packets:</strong>{" "}
      {task.matchingExistingProvisionalResearchReviews}.
      {" "}{task.provisionalResearchIdentity===
       "MULTIPLE_PROGRAM_IDENTITIES_NEED_ADJUDICATION"?
       "Multiple drug/indication identities: do not combine their reviews.":
       "These are historical research packets, not authenticated independent signoffs."}
     </p>
     <p style={{margin:0}}><strong>Unresolved work:</strong> compare the previous
      and current original source, confirm the exact therapy and endpoint,
      reproduce the clinical or design difference, check uncertainty,
      and request a separately attributable independent review.
      Never backdate a provisional assessment or rewrite a previous score.</p>
     <p style={{margin:0,display:"flex",gap:12,flexWrap:"wrap"}}>
      <Link href={"/raas-trial-review?"+new URLSearchParams({
       nctId:task.nctId,ticker:task.ticker,metricId:task.metricId
      })} data-raas-open-exact-alert-metric={task.metricId}>
       Open {task.metricId} in the 60-metric trial reviewer</Link>
      <Link href={"/raas-evidence-changes?"+new URLSearchParams({
       nctId:task.nctId,ticker:task.ticker
      })}>View all observed NCT source revisions</Link>
      <a href={task.sourceUrl} target="_blank" rel="noopener noreferrer">
       Original official registry record</a>
     </p>
     {task.matchingExistingProvisionalResearchReviews>0&&
      <p style={{margin:0}}>
       <Link href={"/raas-review-queue?"+new URLSearchParams({
        reviewNctId:task.nctId,reviewMetricId:task.metricId
       })+"#raas-existing-source-checked-review-packets"}>
        Compare existing exact-metric provisional review packet(s)</Link>.
       A registry revision does not automatically invalidate an independently
       dated sponsor document; adjudicate relevance to each program.
      </p>}
    </div>
   </details>)}
  </div>}
  {pages>1&&<nav aria-label="Source revision metric review pages"
   style={{display:"flex",justifyContent:"space-between",gap:12}}>
   <button type="button" style={style} disabled={current===0}
    onClick={()=>setPage(p=>Math.max(0,p-1))}>Previous alerts</button>
   <span>Page {current+1}/{pages}</span>
   <button type="button" style={style} disabled={current===pages-1}
    onClick={()=>setPage(p=>Math.min(p+1,pages-1))}>Next alerts</button>
  </nav>}
 </section>;
}
