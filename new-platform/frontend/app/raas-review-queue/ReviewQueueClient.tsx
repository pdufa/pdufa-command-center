"use client";
import {useMemo,useState} from "react";
import type {RaasIndependentReviewQueue,RaasReviewPriority} from "../../lib/raas-independent-review-queue";
import css from "../raas-history/page.module.css";

const label:Record<RaasReviewPriority,string>={
 FDA_ACCEPTED_PHASE3:"FDA-accepted Phase 3 application",
 CURRENT_PHASE3_TOP:"Current Phase 3 TOP research",
 OTHER_RESEARCH:"Other clinical research evidence"
};
const style={border:"1px solid #cadfd0",borderRadius:8,padding:"9px 12px",
 background:"white",color:"#184d34",fontSize:13};
const perPage=20;

export default function ReviewQueueClient({queue}:{queue:RaasIndependentReviewQueue}){
 const [text,setText]=useState("");
 const [priority,setPriority]=useState<"all"|RaasReviewPriority>("all");
 const [stage,setStage]=useState<"all"|"pre"|"post">("all");
 const [page,setPage]=useState(0);
 const filtered=useMemo(()=>{
  const needle=text.trim().toLowerCase();
  return queue.items.filter(item=>
   (priority==="all"||item.priority===priority)&&
   (stage==="all"||item.stage===stage)&&
   (!needle||[item.ticker,item.nctId,item.drug,item.indication,
    item.metricId,item.metricName,item.trialName||"",item.applicationKey||""]
    .some(value=>value.toLowerCase().includes(needle))));
 },[queue.items,priority,stage,text]);
 const count=Math.max(1,Math.ceil(filtered.length/perPage));
 const current=Math.min(page,count-1);
 const shown=filtered.slice(current*perPage,(current+1)*perPage);
 const resetPage=()=>setPage(0);
 return <>
  <div style={{display:"flex",flexWrap:"wrap",gap:10,alignItems:"end",margin:"16px 0"}}>
   <label style={{display:"grid",gap:4,fontSize:12,fontWeight:650}}>
    Find trial or metric
    <input value={text} onChange={e=>{setText(e.target.value);resetPage();}}
     aria-label="Search RAAS review tasks" placeholder="NCT, ticker, drug, metric"
     style={{...style,minWidth:175}} maxLength={100}/>
   </label>
   <label style={{display:"grid",gap:4,fontSize:12,fontWeight:650}}>
    Review priority
    <select aria-label="Filter independent review priority" value={priority}
     onChange={e=>{setPriority(e.target.value as typeof priority);resetPage();}} style={style}>
     <option value="all">All evidence tasks</option>
     <option value="FDA_ACCEPTED_PHASE3">Phase 3 FDA-accepted</option>
     <option value="CURRENT_PHASE3_TOP">Current Phase 3 TOP</option>
     <option value="OTHER_RESEARCH">Other research</option>
    </select>
   </label>
   <label style={{display:"grid",gap:4,fontSize:12,fontWeight:650}}>
    RAAS stage
    <select aria-label="Filter TOP and BOTTOM reviews" value={stage}
     onChange={e=>{setStage(e.target.value as typeof stage);resetPage();}} style={style}>
     <option value="all">TOP and BOTTOM</option>
     <option value="pre">TOP only</option>
     <option value="post">BOTTOM only</option>
    </select>
   </label>
   <button type="button" style={style}
    onClick={()=>{setText("");setPriority("all");setStage("all");resetPage();}}>
    Clear filters
   </button>
   <a href="/api/raas-independent-review-queue" download
    style={{...style,fontWeight:750,textDecoration:"underline"}}>
    Export review tasks (CSV)
   </a>
  </div>
  <p role="status" style={{fontSize:12,color:"#436d50",margin:"8px 0"}}>
   <strong>{filtered.length}</strong> pending source-review task records ·
   showing {filtered.length?current*perPage+1:0}–{Math.min((current+1)*perPage,filtered.length)}
   · 0 certified independent signoffs in this saved evidence source
  </p>
  <section aria-label="Source reviewed RAAS metrics requiring independent adjudication"
    style={{display:"grid",gap:8}}>
   {shown.map(x=><details key={x.id} data-raas-review-item={x.id}
     style={{border:"1px solid #cbded0",borderRadius:9,background:"#fff",overflow:"hidden"}}>
    <summary style={{cursor:"pointer",padding:"12px",display:"flex",
     flexWrap:"wrap",justifyContent:"space-between",gap:10,alignItems:"center",
     listStyle:"none",background:"#f6faf7",color:"#204b34"}}>
     <span style={{display:"grid",gap:3,minWidth:190,flex:1}}>
      <strong>{x.ticker} · {x.nctId} · {x.stage==="pre"?"TOP":"BOTTOM"}</strong>
      <small>{x.trialName||x.drug} · {x.indication}</small>
      <small>{label[x.priority]}</small>
     </span>
     <span style={{display:"grid",gap:3,flex:1,minWidth:180}}>
      <strong>{x.metricId} · {x.metricName}</strong>
      <small>Research band: {x.provisionalScore}/100 · {x.provisionalFinding.replaceAll("_"," ").toLowerCase()}</small>
      <small>{x.metricWeightPercent}% stage weight · not an overall RAAS score</small>
     </span>
     <span style={{fontSize:12,fontWeight:750,color:"#87582d",maxWidth:160}}>
      Awaiting independently documented review · ▸
     </span>
    </summary>
    <div style={{display:"grid",gap:10,padding:15,fontSize:12,lineHeight:1.6,color:"#345643"}}>
     <p style={{margin:0}}><strong>Review identity:</strong> {x.ticker} · {x.nctId}
      {" "}· {x.drug} · {x.indication} · {x.metricId}.
      {x.applicationKey?" FDA application "+x.applicationKey+".":""}
      {" "}Scoring stage is {x.stage==="pre"?"TOP":"BOTTOM"}. Review of this one metric
      cannot establish stage-wide RAAS, FDA odds, or another trial's grade.</p>
     <p style={{margin:0}}><strong>Evidence as-of:</strong> {x.sourceAsOf}
      {" "}· primary document dated {x.sourceDate} · preliminary research reviewed {x.assessedAt}.</p>
     <p style={{margin:0}}><strong>Observed fact:</strong> {x.observedResult}</p>
     <p style={{margin:0}}><strong>External benchmark:</strong> {x.benchmarkId}
      {" "}· {x.benchmarkContext}</p>
     <p style={{margin:0}}><strong>Uncertainty:</strong> {x.uncertaintyReview}</p>
     <p style={{margin:0}}><strong>Critical risk:</strong> {x.criticalRiskReview}</p>
     <p style={{margin:0}}><strong>Original research method:</strong> {x.reviewerMethod}</p>
     <div style={{display:"flex",flexWrap:"wrap",gap:14}}>
      <a href={"/api/raas-independent-review-packet?"+new URLSearchParams({task:x.id}).toString()}
       download data-raas-source-frozen-packet={x.id}
       style={{fontWeight:750}}>Download source-frozen unsigned review packet (JSON)</a>
      <a href={x.sourceUrl} target="_blank" rel="noopener noreferrer">Primary evidence</a>
      <a href={x.benchmarkSourceUrl} target="_blank" rel="noopener noreferrer">Independent benchmark</a>
      <a href={"https://clinicaltrials.gov/study/"+x.nctId}
       target="_blank" rel="noopener noreferrer">Exact NCT registry</a>
      <a href={"/raas-worklist?"+new URLSearchParams({
       nctId:x.nctId,ticker:x.ticker,drug:x.drug,indication:x.indication,stage:x.stage
      })}>All 30 stage metric requirements</a>
     </div>
     <details style={{border:"1px solid #d7e5d9",borderRadius:7,padding:10}}>
      <summary style={{cursor:"pointer",fontWeight:750}}>
       Required independent review and sign-off · not yet completed
      </summary>
      <ol style={{paddingLeft:20,margin:"10px 0",display:"grid",gap:6}}>
       <li>Confirm exact NCT, drug, indication, study arm, endpoint and research stage against contemporaneous primary sources.</li>
       <li>Check source dates, reporting denominators, measurement definitions and possible publication lag; preserve evidence available at the original review time.</li>
       <li>Reproduce the benchmark comparison independently and assess confounding, statistical uncertainty, multiplicity and safety limits.</li>
       <li>Record agreement or a changed provisional grade with an explicit reason and contrary evidence; do not infer missing metrics.</li>
       <li>Attach an attributable independent reviewer identity, signed date, source references and conflict-of-interest declaration before any approval request.</li>
       <li>Validate full 30/30 stage evidence and holdout calibration separately; retain no FDA PASS/CRL/EXTENSION probability until independent prospective validation.</li>
      </ol>
      <p><strong>Reviewer packet handoff:</strong> download the evidence-frozen JSON,
       complete the unsigned receipt template and have an external reviewer provide
       an attributable signed document in a restricted archive. A receipt submitted through
       a reviewed repository change remains unverified until identity, independence,
       signature and scientific conclusions are independently adjudicated.
       Do not publish personal contact details or signed documents to GitHub.</p>
      <p><strong>Current status:</strong> {x.reviewState.replaceAll("_"," ").toLowerCase()}.
       This read-only page cannot approve scores or capture signatures. Signed reviews must
       be reconciled into the authoritative metric ledger with a separate audit trail.</p>
     </details>
    </div>
   </details>)}
   {shown.length===0&&<p>No evidence tasks match these filters.</p>}
  </section>
  <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",
   flexWrap:"wrap",gap:10,marginTop:14,fontSize:12}}>
   <button type="button" disabled={current===0} style={style}
    onClick={()=>setPage(x=>Math.max(0,x-1))}>Previous 20</button>
   <span>Page {current+1} of {count}</span>
   <button type="button" disabled={current>=count-1} style={style}
    onClick={()=>setPage(x=>Math.min(count-1,x+1))}>Next 20</button>
  </div>
 </>;
}
