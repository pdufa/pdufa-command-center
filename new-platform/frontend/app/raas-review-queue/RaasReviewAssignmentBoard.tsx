"use client";
import {useMemo,useState} from "react";
import Link from "next/link";
import type {RaasReviewAssignmentPlan}
 from "../../lib/raas-review-assignment-plan";
import type {RaasReviewPriority}
 from "../../lib/raas-independent-review-queue";
import type {RaasReviewSourceGateSummary}
 from "../../lib/raas-review-source-alert-gate";

const control={border:"1px solid #bcd4c4",borderRadius:7,
 padding:"9px 11px",color:"#174e33",background:"#fff",fontSize:12} as const;
const rankLabel:Record<RaasReviewPriority,string>={
 FDA_ACCEPTED_PHASE3:"FDA-accepted Phase 3 · action-date priority",
 CURRENT_PHASE3_TOP:"Current Phase 3 TOP research",
 OTHER_RESEARCH:"Historical / other research"
};
export default function RaasReviewAssignmentBoard({
 plan,sourceGates
}:{plan:RaasReviewAssignmentPlan;sourceGates:RaasReviewSourceGateSummary}){
 const [priority,setPriority]=useState<"all"|RaasReviewPriority>("all");
 const [search,setSearch]=useState("");
 const groups=useMemo(()=>plan.groups.filter(group=>
  (priority==="all"||group.priority===priority)&&
  (!search.trim()||[group.nctId,group.ticker,group.drug,group.indication,
   group.applicationKey??""].some(value=>
   value.toLowerCase().includes(search.trim().toLowerCase())))
 ),[plan.groups,priority,search]);
 const packets=groups.reduce((n,g)=>n+g.provisionalMetrics,0);
 const sourceGateById=new Map(sourceGates.gates.map(g=>[g.programId,g]));
 return <section data-raas-review-assignment-board="unsigned-source-frozen"
  style={{display:"grid",gap:12,margin:"20px 0"}}>
  <header>
   <h2 style={{margin:"0 0 6px"}}>External reviewer assignment board</h2>
   <p style={{fontSize:12,margin:0,lineHeight:1.6}}>
    Organize <strong>{plan.totalPackets} provisional metric research packets</strong>
    {" "}across <strong>{plan.distinctPrograms} exact trial/program-stage dossiers</strong>.
    Each packet has a source-bound SHA-256 fingerprint and a downloadable unsigned
    evidence file. No reviewer is assigned by this board, and no metric is
    independently approved merely because the packet is complete.
   </p>
  </header>
  <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(130px,1fr))",gap:8}}>
   {([
    [plan.fdaAcceptedPhase3Packets,"FDA-accepted Phase 3 metric packets"],
    [plan.currentPhase3TopPackets,"Current Phase 3 TOP metric packets"],
    [plan.otherResearchPackets,"Other historical research packets"],
    [plan.pendingReceiptAuthentication,"Receipt references pending authentication"],
    [plan.certifiedIndependentMetricSignoffs,"Certified independent metric reviews"]
   ] as const).map(([value,label])=>
    <div key={label} style={{border:"1px solid #cce0d1",
     background:"#f5faf6",borderRadius:8,padding:11}}>
     <strong style={{display:"block",fontSize:22}}>{value}</strong>
     <span style={{fontSize:11}}>{label}</span>
    </div>)}
  </div>
  <p data-raas-revision-review-handoff-gates="unapproved" style={{fontSize:12,margin:0,lineHeight:1.6}}>
   <strong>Source-change preflight:</strong>{" "}
   {sourceGates.needRevisionRecheck} program(s) with unresolved clinical registry
   metric alerts; {sourceGates.sourceAuditUnconfirmed} with unconfirmed audit
   coverage; {sourceGates.noRecordedMetricRevisions} without recorded
   metric-level revisions in the saved comparison. A clean saved comparison
   does not establish clinical accuracy or real-time freshness.
  </p>
  <div style={{display:"flex",gap:9,flexWrap:"wrap",alignItems:"end"}}>
   <label style={{display:"grid",gap:3,fontSize:11,fontWeight:700}}>
    Worklist priority
    <select aria-label="Filter RAAS external review assignments by priority"
     value={priority} style={control}
     onChange={e=>setPriority(e.target.value as typeof priority)}>
     <option value="all">All programs</option>
     <option value="FDA_ACCEPTED_PHASE3">FDA-accepted Phase 3 first</option>
     <option value="CURRENT_PHASE3_TOP">Current Phase 3 TOP</option>
     <option value="OTHER_RESEARCH">Historical/other research</option>
    </select>
   </label>
   <label style={{display:"grid",gap:3,fontSize:11,fontWeight:700}}>
    Find exact trial or program
    <input aria-label="Find RAAS review program by NCT, ticker or therapy"
     style={control} value={search} maxLength={90}
     onChange={e=>setSearch(e.target.value)}
     placeholder="NCT, ticker, therapy"/>
   </label>
   <button type="button" style={control}
    onClick={()=>{setPriority("all");setSearch("");}}>Clear filters</button>
   <a href="/api/raas-review-assignment-manifest" download
    style={{...control,fontWeight:700}}>
    Download all {plan.totalPackets} packet fingerprints (CSV)
   </a>
  </div>
  <p role="status" style={{fontSize:12,margin:0}}>
   {groups.length} matching program-stage dossiers · {packets} unsigned
   metric packets · no certified scores or FDA predictions
  </p>
  <div style={{display:"grid",gap:9}}>
   {groups.map(group=><details key={group.id}
    data-raas-exact-review-program={group.nctId+":"+group.stage}
    style={{border:"1px solid #c6decd",borderRadius:9,overflow:"hidden"}}>
    <summary style={{cursor:"pointer",padding:12,background:"#f4faf6",
     display:"flex",flexWrap:"wrap",justifyContent:"space-between",gap:12,
     alignItems:"center"}}>
     <span style={{display:"grid",gap:4,flex:"1 1 185px"}}>
      <strong>{group.ticker} · {group.nctId} · {group.stage==="pre"?"TOP":"BOTTOM"}</strong>
      <small>{group.trialName??group.drug} · {group.indication}</small>
      <small>{rankLabel[group.priority]}</small>
     </span>
     <span style={{display:"grid",gap:3,flex:"1 1 185px"}}>
      <strong>{group.provisionalMetrics}/30 provisional metric packets</strong>
      <small>{group.remainingStageMetrics} unreviewed metric requirements · N/A, not zero</small>
      <small>{group.receiptPending} receipt(s) pending identity authentication · {group.receiptBlocked} blocked</small>
      <small data-raas-exact-program-source-gate={sourceGateById.get(group.id)?.status??"MISSING"}>
       {sourceGateById.get(group.id)?.status==="RECHECK_SOURCE_REVISIONS"?
        "Registry changed — independently recheck affected metrics":
        sourceGateById.get(group.id)?.status==="SOURCE_AUDIT_INCOMPLETE_OR_UNSYNCED"?
        "Registry audit not confirmed — reconcile first":
        "No recorded metric revision in saved source audit (not certified)"}
      </small>
     </span>
     <strong style={{fontSize:11}}>View evidence packets ▸</strong>
    </summary>
    <div style={{padding:12,display:"grid",gap:10}}>
     <p style={{fontSize:12,margin:0}}>
      <strong>Source snapshot:</strong> {group.sourceAsOf}.
      {group.applicationKey?" FDA application "+group.applicationKey+".":""}
      {" "}The one-file expert handoff includes all 30 stage requirements:
      {group.provisionalMetrics} unapproved prior research packets and
      {group.remainingStageMetrics} missing-evidence entries (N/A, not zero).
      A source fingerprint establishes file identity, not scientific
      correctness. No authenticated reviewer assignment or stage rating exists.
     </p>
     <p style={{fontSize:12,margin:0}}>
      <strong>Registry source-change check:</strong>{" "}
      {sourceGateById.get(group.id)?.explanation??"Not available."}
      {" "}Latest saved registry audit: {sourceGateById.get(group.id)?.registryAsOf??"unavailable"}.
      {sourceGateById.get(group.id)?.sourceChangedMetricIds.length?
       " Affected metric IDs: "+sourceGateById.get(group.id)?.sourceChangedMetricIds.join(", ")+".":""}
      {" "}<Link href="/raas-evidence-changes">Source-change history</Link>
     </p>
     <div style={{display:"flex",gap:10,flexWrap:"wrap",fontSize:12}}>
      <a href={"/api/raas-exact-program-review-bundle?"+
       new URLSearchParams({task:group.tasks[0].taskId}).toString()}
       download data-raas-complete-stage-review-handoff="30-metrics">
       Download one expert handoff · all 30 {group.stage==="pre"?"TOP":"BOTTOM"} metrics
      </a>
      <Link href={"/raas-trial-review?"+new URLSearchParams({
       nctId:group.nctId,ticker:group.ticker
      })}>Open 60-metric review worksheet</Link>
      <Link href={"/raas-review-queue?"+new URLSearchParams({
       reviewNctId:group.nctId
      })+"#raas-existing-source-checked-review-packets"}>
       Compare existing provisional packet evidence</Link>
     </div>
     <div style={{display:"grid",gap:7}}>
      {group.tasks.map(task=><div key={task.taskId}
       style={{padding:10,border:"1px solid #e0ebe3",borderRadius:6,
        display:"flex",gap:10,flexWrap:"wrap",justifyContent:"space-between"}}>
       <div style={{display:"grid",gap:3,flex:"1 1 180px",fontSize:12}}>
        <strong>{task.metricId} · {task.metricName}</strong>
        <small>Primary source dated {task.sourceDate}
         {" "}· {task.metricWeightPercent}% of stage weight</small>
        <small>Fingerprint {task.sourceFingerprint.slice(0,20)}…</small>
        <small>{task.receiptState==="NO_RECEIPT"?
         "No external signed-document receipt":
         task.receiptState==="BLOCKED_RECEIPT"?
         "Submitted receipt blocked by audit":
         "Submitted receipt pending independent authentication"}</small>
       </div>
       <div style={{display:"flex",flexWrap:"wrap",alignItems:"center",gap:10,fontSize:12}}>
        <a href={"/api/raas-independent-review-packet?"+
         new URLSearchParams({task:task.taskId}).toString()}
         download>Download unsigned packet</a>
        <a href={task.sourceUrl} target="_blank" rel="noopener noreferrer">
         Primary source</a>
        <Link href={"/raas-trial-review?"+new URLSearchParams({
         nctId:group.nctId,ticker:group.ticker,metricId:task.metricId
        })}>Open metric</Link>
       </div>
      </div>)}
     </div>
    </div>
   </details>)}
   {groups.length===0&&<p style={control}>No matching exact-trial review packets.</p>}
  </div>
  <p style={{fontSize:11,lineHeight:1.6,margin:0}}>
   <strong>External review boundary:</strong> The public dashboard does not
   assign experts, collect private signatures, certify reviewer independence,
   rewrite historical grades or publish calibrated PASS / CRL / EXTENSION odds.
   Reviewer identity and signed evidence belong in a restricted archive, followed
   by an independently audited receipt and scientific adjudication.
  </p>
 </section>;
}
