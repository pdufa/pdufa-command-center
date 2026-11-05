"use client";
import {useEffect,useMemo,useState} from "react";
import Link from "next/link";
import {loadRegistryEvidenceIndex} from "../../lib/raas-registry-evidence";
import {buildTrialEvidenceBacklog,type EvidenceBacklogPriority,
 type TrialEvidenceBacklog,type EvidenceBacklogStage}
 from "../../lib/raas-trial-evidence-backlog";

const priorities:Record<EvidenceBacklogPriority,string>={
 FDA_ACCEPTED_PHASE3:"FDA-accepted Phase 3 · verify action",
 CURRENT_PHASE3_TOP:"Current Phase 3 TOP · source missing metrics",
 DATED_READOUT_EVIDENCE:"Dated readout evidence · contextual",
 REGISTRY_COMPARATIVE_RESULTS:"Registry results with comparative analysis",
 REGISTRY_RESULTS_OTHER:"Posted results · more analysis needed",
 REGISTRY_PROTOCOL_ONLY:"Protocol only · no posted results"
};
const stageLabel:Record<EvidenceBacklogStage,string>={
 pre:"TOP evidence documented as of snapshot",
 post:"BOTTOM results documented as of snapshot",
 unverified:"Readout stage not independently verified"
};
const base={
 border:"1px solid #cbdcce",borderRadius:7,padding:"9px 10px",
 background:"#fff",color:"#1c5037",fontSize:12
};
const count=25;
export default function EvidenceBacklogClient(){
 const [backlog,setBacklog]=useState<TrialEvidenceBacklog|null>(null);
 const [error,setError]=useState("");
 const [q,setQ]=useState("");
 const [priority,setPriority]=useState<"all"|EvidenceBacklogPriority>("all");
 const [stage,setStage]=useState<"all"|EvidenceBacklogStage>("all");
 const [results,setResults]=useState<"all"|"posted"|"protocol"|"comparison">("all");
 const [reviewed,setReviewed]=useState<"all"|"has"|"none">("all");
 const [page,setPage]=useState(0);
 useEffect(()=>{
  let alive=true;
  void loadRegistryEvidenceIndex().then(index=>{
   if(!alive)return;
   if(!index){setError("The exact 762-NCT registry index is unavailable. The evidence backlog cannot be verified.");return;}
   try{setBacklog(buildTrialEvidenceBacklog(index));}
   catch(e){setError(e instanceof Error?e.message:"Evidence sources failed verification");}
  });return ()=>{alive=false;};
 },[]);
 const filtered=useMemo(()=>{
  const text=q.toLowerCase().trim();
  return (backlog?.items??[]).filter(x=>
   (priority==="all"||x.priority===priority)&&
   (stage==="all"||x.stage===stage)&&
   (results==="all"||(results==="posted"&&x.postedResults)||
    (results==="protocol"&&!x.postedResults)||
    (results==="comparison"&&x.hasPrimaryComparisons))&&
   (reviewed==="all"||(x.reviewedTop+x.reviewedBottom>0)===(reviewed==="has"))&&
   (!text||[
    x.nctId,x.ticker,x.trialName||"",...x.conditions,...x.interventions,
    x.applicationKey||""
   ].some(v=>v.toLowerCase().includes(text))));
 },[backlog,q,priority,stage,results,reviewed]);
 const pages=Math.max(1,Math.ceil(filtered.length/count));
 const current=Math.min(page,pages-1);
 const shown=filtered.slice(current*count,(current+1)*count);
 const reset=()=>setPage(0);
 if(error)return <p role="alert" style={{padding:15,border:"1px solid #bca38a"}}>{error}</p>;
 if(!backlog)return <p role="status">Loading and checking 762 registered trial records…</p>;
 return <div data-raas-research-backlog="762-actual-registry-records">
  <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(145px,1fr))",
   gap:10,margin:"20px 0"}}>
   {[
    [backlog.totalTrials,"Registry trials · not Pipeline qualified"],
    [backlog.trialsWithAnyProvisionalMetrics,"Trials with any provisional metric reviews"],
    [backlog.provisionalMetricReviews,"Individually reviewed provisional metrics"],
    [backlog.postedResults,"Trials with posted registry results"],
    [backlog.unverifiedStages,"Readout stages still unverified"],
    [backlog.independentReviewedMetrics,"Certified independent metric reviews"]
   ].map(([v,label])=><div key={label} style={{...base,padding:14,background:"#f5faf6"}}>
    <strong style={{display:"block",fontSize:25}}>{v}</strong>
    <span style={{fontSize:11,lineHeight:1.5}}>{label}</span>
   </div>)}
  </div>
  <p style={{fontSize:12,lineHeight:1.65,color:"#3f6149"}}>
   Registry snapshot {backlog.sourceAsOf}; provisional review source {backlog.reviewSourceAsOf}.
   These are observed research records, not verified current PDUFA candidate eligibility,
   FDA odds, or a complete 30/30 RAAS score. For unverified stages, both TOP and BOTTOM
   missing-metric lists are potential worklists only; neither is assigned as the
   required stage. The two stages must never be combined into a 60-point rating.
  </p>
  <div style={{display:"flex",gap:8,flexWrap:"wrap",alignItems:"end",margin:"18px 0"}}>
   <label style={{display:"grid",gap:5,fontSize:12,fontWeight:700}}>
    Find NCT / ticker / indication
    <input value={q} maxLength={100} placeholder="NCT, ticker, therapy, disease"
     aria-label="Search all registry trial evidence gaps"
     onChange={e=>{setQ(e.target.value);reset();}}
     style={{...base,minWidth:180}}/>
   </label>
   <label style={{display:"grid",gap:5,fontSize:12,fontWeight:700}}>
    Work priority
    <select value={priority} aria-label="Filter evidence priorities"
     onChange={e=>{setPriority(e.target.value as typeof priority);reset();}} style={base}>
     <option value="all">All priorities</option>
     {Object.entries(priorities).map(([id,label])=><option key={id} value={id}>{label}</option>)}
    </select>
   </label>
   <label style={{display:"grid",gap:5,fontSize:12,fontWeight:700}}>
    Documented readout
    <select value={stage} aria-label="Filter documented readout stages"
     onChange={e=>{setStage(e.target.value as typeof stage);reset();}} style={base}>
     <option value="all">All readout states</option>
     <option value="pre">TOP source</option>
     <option value="post">BOTTOM source</option>
     <option value="unverified">Unverified</option>
    </select>
   </label>
   <label style={{display:"grid",gap:5,fontSize:12,fontWeight:700}}>
    Source availability
    <select value={results} aria-label="Filter registry result evidence"
     onChange={e=>{setResults(e.target.value as typeof results);reset();}} style={base}>
     <option value="all">All registry records</option>
     <option value="comparison">Has comparative primary analysis</option>
     <option value="posted">Posted results</option>
     <option value="protocol">Protocol only</option>
    </select>
   </label>
   <label style={{display:"grid",gap:5,fontSize:12,fontWeight:700}}>
    Provisional reviews
    <select value={reviewed} aria-label="Filter provisional metric reviews"
     onChange={e=>{setReviewed(e.target.value as typeof reviewed);reset();}} style={base}>
     <option value="all">All trial reviews</option>
     <option value="has">At least one review</option>
     <option value="none">No metric reviews</option>
    </select>
   </label>
   <button type="button" style={base} onClick={()=>{
    setQ("");setPriority("all");setStage("all");setResults("all");setReviewed("all");reset();
   }}>Clear selections</button>
   <a href="/api/raas-evidence-backlog" download style={{...base,fontWeight:700}}>
    Export 762-trial evidence gaps (CSV)
   </a>
  </div>
  <p role="status" style={{fontSize:12,color:"#3c6249"}}>
   {filtered.length.toLocaleString()} trial records · showing {filtered.length?current*count+1:0}–
   {Math.min((current+1)*count,filtered.length)} · sources only
  </p>
  <div style={{display:"grid",gap:9}}>
   {shown.map(x=><details key={x.nctId}
    data-raas-evidence-backlog-nct={x.nctId}
    style={{border:"1px solid #cbdccf",borderRadius:10,background:"#fff",overflow:"hidden"}}>
    <summary style={{listStyle:"none",cursor:"pointer",padding:13,background:"#f7faf8",
     display:"flex",flexWrap:"wrap",gap:12,alignItems:"center",justifyContent:"space-between"}}>
     <span style={{flex:"1 1 180px",display:"grid",gap:4}}>
      <strong>{x.ticker} · {x.nctId}</strong>
      <small>{x.trialName?x.trialName+" · ":""}{x.conditions.slice(0,2).join(", ")||"Registered indication unavailable"}</small>
      <small>{priorities[x.priority]}</small>
     </span>
     <span style={{flex:"1 1 180px",display:"grid",gap:4}}>
      <strong>{x.stage==="unverified"?"Stage unverified":x.stage==="pre"?"TOP research":"BOTTOM research"}</strong>
      <small>Provisional TOP {x.reviewedTop}/30 · BOTTOM {x.reviewedBottom}/30</small>
      <small>{x.postedResults?"Registry results posted":"Protocol only"} ·
       {x.hasPrimaryComparisons?" comparison source available":" no comparative primary analysis"}</small>
     </span>
     <strong style={{fontSize:12,flex:"0 1 130px"}}>View required evidence ▸</strong>
    </summary>
    <div style={{padding:14,display:"grid",gap:9,fontSize:12,lineHeight:1.6,color:"#355841"}}>
     <p style={{margin:0}}><strong>Next assessment:</strong> {x.nextEvidenceAction}</p>
     <p style={{margin:0}}><strong>Readout classification:</strong> {stageLabel[x.stage]}.
      {x.stageEvidenceDate?" Last direct evidence "+x.stageEvidenceDate+".":""}
      {" "}A study's registry status or posted results alone does not verify when
      the public Phase 3 announcement occurred.</p>
     <p style={{margin:0}}><strong>Registry:</strong> {x.registeredStatus}
      {" "}· phases {x.registeredPhases.join(", ")||"not specified"}
      {" "}· source updated {x.sourceDate}.
      {" "}Primary outcome records {x.postedPrimaryOutcomeCount}
      {" "}· primary between-arm comparison {x.hasPrimaryComparisons?"yes":"not in saved source"}
      {" "}· primary CI {x.hasConfidenceIntervals?"yes":"not in saved source"}
      {" "}· SAE denominators {x.hasSeriousEventDenominators?"yes":"not in saved source"}.</p>
     <p style={{margin:0}}><strong>Drug/intervention:</strong>
      {" "}{x.interventions.slice(0,5).join("; ")||"No intervention listed in saved source"}.</p>
     {x.acceptedPdufaGoal&&<p style={{margin:0}}>
      <strong>Documented FDA application research:</strong> {x.applicationKey},
      {" "}goal {x.acceptedPdufaGoal} as of the saved sponsor snapshot.
      Reverify FDA deadline and status; no FDA outcome or approval odds inferred.</p>}
     <p style={{margin:0}}><strong>Unreviewed potential metric IDs:</strong>
      {" "}TOP {x.missingTopMetricIds.length}/30
      {" "}({x.missingTopMetricIds.slice(0,7).join(", ")}{x.missingTopMetricIds.length>7?", …":""});
      {" "}BOTTOM {x.missingBottomMetricIds.length}/30
      {" "}({x.missingBottomMetricIds.slice(0,7).join(", ")}{x.missingBottomMetricIds.length>7?", …":""}).
      {x.stage==="unverified"?" Both stages are research-only placeholders until direct readout evidence is checked.":""}
      {x.ambiguousProgramReviews?" Multiple program identities exist; reviewed counts withheld to avoid mixing drugs.":""}
     </p>
     <div style={{display:"flex",gap:13,flexWrap:"wrap"}}>
      <a href={x.sourceUrl} target="_blank" rel="noopener noreferrer">Exact registry trial</a>
      {x.stageSourceUrl&&<a href={x.stageSourceUrl} target="_blank" rel="noopener noreferrer">Dated stage source</a>}
      <Link href="/raas-review-queue">Source-reviewed metric packets</Link>
      <Link href="/raas-worklist">60-metric source requirements</Link>
     </div>
     <p style={{margin:0,fontSize:11,color:"#6b705b"}}>
      The individual primary evidence lead is not a validated efficacy grade,
      regulatory classification, or independently calibrated investment prediction.
     </p>
    </div>
   </details>)}
   {!shown.length&&<p>No trial records match these filters.</p>}
  </div>
  <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",
   flexWrap:"wrap",gap:12,marginTop:16,fontSize:12}}>
   <button disabled={current===0} type="button" style={base}
    onClick={()=>setPage(p=>Math.max(0,p-1))}>Previous 25</button>
   <span>Page {current+1} of {pages}</span>
   <button disabled={current>=pages-1} type="button" style={base}
    onClick={()=>setPage(p=>Math.min(pages-1,p+1))}>Next 25</button>
  </div>
 </div>;
}
