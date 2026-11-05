"use client";
import {useMemo,useState} from "react";
import publishedClinicalLeads from "../data/raas-classified-published-metric-leads.json";
import sourcePolicy from "../data/raas-source-acceptance-policy.json";
import type {ReadoutClassification} from "../lib/phase3-public-readout";
import {buildRaasTopBottomCompletion,type RaasClassifiedCompletionTask,
 type RaasPublishedMetricLead} from "../lib/raas-top-bottom-completion";

const buttonStyle={
 padding:"9px 12px",border:"1px solid #8fbea0",borderRadius:7,
 background:"#eef8ef",color:"#164d2e",fontSize:13,fontWeight:650
} as const;
const PAGE_SIZE=20;

/** Honest score completion dashboard: all source-classified trial requirements
 * are visible, even when numerical evidence is not yet verified.
 */
export default function RaasTopBottomCompletionPanel({
 data
}:{data:ReadoutClassification}){
 const [stage,setStage]=useState<"all"|"TOP"|"BOTTOM">("all");
 const [needle,setNeedle]=useState("");
 const [showAll,setShowAll]=useState(false);
 const [page,setPage]=useState(0);
 const [expanded,setExpanded]=useState(false);
 const plan=useMemo(()=>{
  try{return buildRaasTopBottomCompletion(data)}
  catch{return null}
 },[data]);
 // Scholarly outcome measurements are review leads, not gradebook entries.
 // Fail closed on mismatched NCT, drug, ticker, stage, or already rated metric.
 const publishedByMetric=useMemo(()=>{
  const keyed=new Map<string,RaasPublishedMetricLead[]>();
  if(!plan)return keyed;
  const rows=new Map([...data.pre,...data.post].map(x=>[x.nctId,x]));
  const tasks=new Map(plan.tasks.map(t=>[t.nctId+"|"+t.metricId,t]));
  for(const lead of publishedClinicalLeads.records as RaasPublishedMetricLead[]){
   const row=rows.get(lead.nctId),task=tasks.get(lead.nctId+"|"+lead.metricId);
   if(!row||!row.evidence||!task||task.numericProvisionalGrade!==null||
    row.ticker!==lead.ticker||row.evidence.drug!==lead.drug||
    task.stage!==lead.stage||lead.approvedNumericGrade!==null||
    !lead.sourceUrl.startsWith("https://")||
    !lead.referenceUrl.startsWith("https://"))continue;
   const key=lead.nctId+"|"+lead.metricId;
   keyed.set(key,[...(keyed.get(key)||[]),lead]);
  }
  return keyed;
 },[data,plan]);
 const publishedCount=[...publishedByMetric.values()].reduce((n,a)=>n+a.length,0);
 const filtered=useMemo(()=>{
  if(!plan)return [];
  const query=needle.trim().toLowerCase();
  return plan.tasks.filter(t=>
   (stage==="all"||t.stage===stage)&&
   (showAll||t.numericProvisionalGrade===null)&&
   (!query||[t.nctId,t.ticker,t.metricId,t.metricName,t.category,
    t.requiredSourceEvidence,t.criticalRisk]
     .some(x=>x.toLowerCase().includes(query)))
  );
 },[plan,stage,needle,showAll]);
 const pages=Math.max(1,Math.ceil(filtered.length/PAGE_SIZE));
 const currentPage=Math.min(page,pages-1);
 const displayed=filtered.slice(currentPage*PAGE_SIZE,(currentPage+1)*PAGE_SIZE);
 function exportList(kind:"all"|"missing"|"handoff"){
  if(!plan)return;
  const csv=kind==="all"?plan.allCsv:kind==="missing"?
   plan.missingOnlyCsv:plan.independentReviewHandoffCsv;
  const blob=new Blob(["\uFEFF",csv],{type:"text/csv;charset=utf-8"});
  const uri=URL.createObjectURL(blob);
  const a=document.createElement("a");
  a.download="raas-TOP-BOTTOM-"+(kind==="all"?"all-metric-status":
    kind==="missing"?"missing-evidence-review":"independent-review-handoff")+".csv";
  a.href=uri;document.body.appendChild(a);a.click();a.remove();
  window.setTimeout(()=>URL.revokeObjectURL(uri),1500);
 }
 if(!plan)return <p role="alert" data-raas-top-bottom-completion-error="true">
  Exact TOP/BOTTOM score and source identity counts could not be reconciled.
  No completion or rating is inferred.
 </p>;
 const {summary}=plan;
 return <section data-raas-top-bottom-metric-completion="SOURCE_VERIFIED_RESEARCH_ONLY"
  aria-label="TOP and BOTTOM RAAS scoring completeness and missing evidence"
  style={{margin:"12px 0 18px",padding:13,border:"1px solid #a4cfb1",
   background:"#f4faf5",borderRadius:10}}>
  <h2 style={{fontSize:18,margin:"0 0 9px",color:"#16492b"}}>
   TOP + BOTTOM RAAS · metric completion tracker
  </h2>
  <p data-raas-user-accepted-source-policy="true"
   style={{fontSize:13,lineHeight:1.5,margin:"6px 0 12px",color:"#295239"}}>
   <strong>Source acceptance active · {sourcePolicy.effectiveDate}.</strong>{" "}
   Published and documented evidence is trusted for internal RAAS research scoring.
   A separate human source-verification signature is not required to grade a
   metric or complete a 30/30 research score. Missing metrics stay N/A; this
   does not represent independent certification or calibrated FDA predictions.
  </p>
  <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(135px,1fr))",
   gap:9,marginBottom:11}}>
   {[
    {n:summary.classifiedTrialRows,label:"Trials in TOP/BOTTOM"},
    {n:summary.allMetricSlots,label:"Exact metric slots set up"},
    {n:summary.provisionalMetricGrades,label:"Source-accepted research grades"},
    {n:publishedCount,label:"Published evidence leads · need rubric grade"},
    {n:summary.missingMetricGrades,label:"Missing numerical metric grades"},
    {n:summary.missingWithoutPublishedMetricLead,
     label:"Missing grades requiring more source discovery"},
    {n:summary.independentFullScores,label:"Independently validated full RAAS scores"}
   ].map(x=><div key={x.label} style={{border:"1px solid #c1dcc6",
    background:"white",borderRadius:8,padding:10}}>
    <strong style={{display:"block",fontSize:22}}>{x.n}</strong>
    <small style={{color:"#496654"}}>{x.label}</small>
   </div>)}
  </div>
  <p style={{fontSize:13,lineHeight:1.5,color:"#395d44"}}>
   <strong>All rows and metric requirements are set up.</strong> Numerical
   scores are filled only where exact-trial, same-therapy documentary evidence
   supports a rubric grade. Missing ratings stay N/A—not zero, 50, or a fabricated
   30/30 total. Published clinical observations are attached to exact tasks;
   their metric grades still need a supported benchmark and uncertainty assessment,
   but no external reviewer is required to proceed. No individual grade establishes an FDA PASS/CRL/EXTENSION
   prediction. The 11,000+ POOL and unclassified trial roster are excluded.
  </p>
  <h3 style={{fontSize:15,margin:"14px 0 9px"}}>Coverage by trial</h3>
  <div style={{overflowX:"auto"}}>
   <table style={{borderCollapse:"collapse",width:"100%",fontSize:13}}>
    <thead><tr>
     {["Trial","Spreadsheet","Reviewed metrics","Awaiting review","Published leads","Overall RAAS"].map(t=>
      <th key={t} scope="col" style={{textAlign:"left",padding:"8px 6px",
       borderBottom:"1px solid #bfdac7"}}>{t}</th>)}
    </tr></thead>
    <tbody>{plan.trials.map(t=><tr key={t.nctId}>
     <td style={{padding:"8px 6px",borderBottom:"1px solid #d7e8dc"}}>
      <strong>{t.ticker}</strong>
      <small style={{display:"block"}}><a href={"https://clinicaltrials.gov/study/"+t.nctId}
       target="_blank" rel="noopener noreferrer">{t.nctId}</a></small>
     </td>
     <td style={{padding:"8px 6px"}}>{t.stage}</td>
     <td style={{padding:"8px 6px"}}>{t.reviewed}/30</td>
     <td style={{padding:"8px 6px"}}>{t.missing}</td>
     <td style={{padding:"8px 6px"}}>{[...publishedByMetric.keys()].filter(k=>k.startsWith(t.nctId+"|")).length}</td>
     <td style={{padding:"8px 6px"}}>{t.sourceAcceptedResearchScore===null?
      "N/A · 30 metrics incomplete":t.sourceAcceptedResearchScore+"/100 · research only"}</td>
    </tr>)}</tbody>
   </table>
  </div>
  <div style={{display:"flex",flexWrap:"wrap",gap:9,margin:"13px 0"}}>
   <button type="button" style={buttonStyle}
    data-raas-independent-review-handoff="300-source-linked-tasks"
    onClick={()=>exportList("handoff")}>
    Download optional external-review worksheet · {summary.allMetricSlots} metrics
   </button>
   <button type="button" style={buttonStyle} data-raas-missing-review-csv="true"
    onClick={()=>exportList("missing")}>
    Export {summary.missingMetricGrades} exact missing-grade evidence tasks
   </button>
   <button type="button" style={buttonStyle} data-raas-all-150-score-status-csv="true"
    onClick={()=>exportList("all")}>
    Export all {summary.allMetricSlots} metric statuses and source requirements
   </button>
  </div>
  <p style={{fontSize:12,color:"#496454"}}>
   The optional review export includes {summary.provisionalMetricGrades} accepted
   research grades, {summary.publishedUngradedMetricLeads} published leads still
   requiring a rubric assessment, and {summary.missingWithoutPublishedMetricLead}
   grades requiring additional evidence. A human signoff is optional for research
   scoring, and the worksheet leaves external reviewer fields blank. None of this
   implies independent validation or a calibrated FDA probability.
  </p>
  <button type="button" aria-expanded={expanded}
   data-raas-missing-tasks-expand="true"
   onClick={()=>setExpanded(x=>!x)} style={buttonStyle}>
   {expanded?"Hide evidence review tasks ▴":
    "Review every missing score requirement ▾"}
  </button>
  {expanded&&<div data-raas-missing-tasks-panel="true" style={{marginTop:12}}>
   <div style={{display:"flex",flexWrap:"wrap",gap:9,margin:"8px 0",alignItems:"end"}}>
    <label style={{display:"flex",flexDirection:"column",gap:4,fontSize:12}}>
     Spreadsheet
     <select value={stage} onChange={e=>{setStage(e.target.value as typeof stage);setPage(0)}}
      aria-label="Filter missing RAAS evidence tasks by TOP or BOTTOM" style={buttonStyle}>
      <option value="all">TOP + BOTTOM</option><option value="TOP">TOP only</option>
      <option value="BOTTOM">BOTTOM only</option>
     </select>
    </label>
    <label style={{display:"flex",flexDirection:"column",gap:4,fontSize:12}}>
     Trial or metric
     <input type="search" aria-label="Find exact NCT or missing RAAS metric"
      placeholder="NCT, ticker, metric, evidence" maxLength={95}
      value={needle} onChange={e=>{setNeedle(e.target.value);setPage(0)}}
      style={{...buttonStyle,background:"white"}}/>
    </label>
    <label style={{fontSize:12,display:"flex",gap:5,alignItems:"center"}}>
     <input type="checkbox" checked={showAll}
      onChange={e=>{setShowAll(e.target.checked);setPage(0)}}/>
     Include already reviewed metrics
    </label>
   </div>
   <p role="status" style={{fontSize:12,color:"#42694d"}}>
    {filtered.length} matching source tasks. Showing {displayed.length}
    {showAll?" (including existing provisional grades)":""}.
   </p>
   <div role="list" style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(265px,1fr))",
    gap:9}}>
    {displayed.map((task:RaasClassifiedCompletionTask)=>
     <div role="listitem" key={task.nctId+"|"+task.stage+"|"+task.metricId}
      data-raas-review-queue-task={task.nctId+"|"+task.metricId}
      style={{padding:11,border:"1px solid #bddac6",background:"white",borderRadius:8}}>
      <strong style={{fontSize:13}}>{task.stage} · {task.ticker}
       {" · "}{task.metricId}</strong>
      <p style={{fontSize:12,margin:"6px 0"}}>{task.metricName}</p>
      <p style={{fontSize:12,margin:"6px 0",fontWeight:700}}>
       {task.numericProvisionalGrade===null?"Grade N/A — not reviewed":
        "Source-accepted research grade "+task.numericProvisionalGrade+"/100"}
      </p>
      <details style={{fontSize:12}}>
       <summary style={{cursor:"pointer",fontWeight:650}}>
        Evidence and review requirements
       </summary>
       <p><strong>Required:</strong> {task.requiredSourceEvidence}</p>
       <p><strong>Comparator:</strong> {task.requiredIndependentBenchmark}</p>
       <p><strong>Critical risk:</strong> {task.criticalRisk}</p>
       <p><strong>Next:</strong> {task.nextAction}</p>
       {(publishedByMetric.get(task.nctId+"|"+task.metricId)||[]).map(lead=>
        <div key={lead.sourceUrl} data-raas-published-ungraded-lead={task.nctId+"|"+task.metricId}
         style={{padding:"8px 0",borderTop:"1px solid #d7e8dc"}}>
         <strong>Published clinical source · not a RAAS grade</strong>
         <p>{lead.reportedResult}</p>
         <p><strong>Comparator context:</strong> {lead.referenceContext}</p>
         <p><strong>Before grading:</strong> {lead.reviewNeeded}</p>
         <a href={lead.sourceUrl} target="_blank" rel="noopener noreferrer">
          Open exact-trial published evidence</a>{" · "}
         <a href={lead.referenceUrl} target="_blank" rel="noopener noreferrer">
          Open comparator or context source</a>
        </div>)}
       <p><a href={task.issuerDisclosureUrl} target="_blank"
        rel="noopener noreferrer">Issuer-source research starting point</a>
        {" · "}<a href={task.registrySourceUrl} target="_blank"
         rel="noopener noreferrer">Exact NCT registry</a></p>
       {task.reviewedPrimarySourceUrl&&<p><a href={task.reviewedPrimarySourceUrl}
        target="_blank" rel="noopener noreferrer">Reviewed primary source</a></p>}
       {task.reviewedComparatorSourceUrl&&<p><a href={task.reviewedComparatorSourceUrl}
        target="_blank" rel="noopener noreferrer">Reviewed comparator</a></p>}
      </details>
     </div>)}
   </div>
   <nav aria-label="RAAS evidence task pagination"
    style={{display:"flex",alignItems:"center",justifyContent:"space-between",
     margin:"13px 0",gap:8}}>
    <button type="button" style={buttonStyle} disabled={currentPage===0}
     onClick={()=>setPage(p=>Math.max(0,p-1))}>Previous 20</button>
    <small>Page {currentPage+1}/{pages}</small>
    <button type="button" style={buttonStyle} disabled={currentPage===pages-1}
     onClick={()=>setPage(p=>Math.min(p+1,pages-1))}>Next 20</button>
   </nav>
  </div>}
 </section>;
}
