"use client";

import {useState} from "react";
import styles from "../../evidence-gaps/EvidenceRecoveryBoardR68.module.css";
type Manifest=NonNullable<typeof import(
 "../../../../lib/focus-r92-protocol-results-crosswalk").R92_CURRENT_PROTOCOL_RESULTS_ROSTER>;
type Row=Manifest["rows"][number];
type Primary={
 key:string;title:string;timeFrame:string|null;
 description?:string|null;populationDescription?:string|null;
 sourceReportedAnalysisGroups?:number;sourceReportedDenominatorEntries?:number;
 sourceReportedPValueEntries?:number;
};
type Crosswalk={
 postedOutcomeKey:string;postedTitle:string;postedTimeFrame:string|null;
 state:string;possibleProtocolKeys:string[];interpretation:string
};
type Report={
 nct:string;ticker:string;sourceUrl?:string;
 currentProtocolPrimaryCount:number;postedRegistryPrimaryCount:number;
 priorSourceCountChanged:boolean;
 currentOriginalSourceMatchesR91Receipt:boolean;
 currentOriginalApiSha256:string;archiveOriginalSourceSha256:string;
 plannedPrimaryOutcomes:Primary[];postedPrimaryOutcomes:Primary[];
 textualCrosswalk:Crosswalk[];
 exactTitleAndTimeframeCount:number;
 exactTitleDifferentTimeframeCount:number;
 needsIndependentEndpointReviewCount:number;
 protocolPrimaryWithoutExactMatch:string[];
 retrievedAtUtc:string;
 originalProspectiveSAPAuthenticated:false;
 sourceVersionEffectiveBeforeUnblindingVerified:false;
 clinicalEndpointConsistencyIndependentlySigned:false;
 safetyInterpretationIndependentlySigned:false;
 FDAForecast:"ABSTAIN";
};
type Lookup={state:"loading"|"ok"|"error";report?:Report;error?:string};
function errName(x:unknown){
 return x&&typeof x==="object"&&"error" in x&&typeof x.error==="string"?
  x.error:"UNVERIFIED_ORIGINAL_SOURCE";
}
function stateLabel(s:string){
 switch(s){
  case "EXACT_TITLE_AND_TIME_FRAME":
   return "Exact registry title and timeframe text";
  case "EXACT_TITLE_TIME_FRAME_DIFFERS":
   return "Same registry title; timeframe text differs — review";
  case "MULTIPLE_POSSIBLE_PROTOCOL_ENTRIES":
   return "Multiple protocol entries with same text — review";
  case "LEXICAL_CANDIDATE_REQUIRES_REVIEW":
   return "Similar wording only — needs human mapping";
  default:return "No close text candidate — needs human mapping";
 }
}
export default function CurrentProtocolResultsR92Client({rows}:{rows:Row[]}){
 const [checks,setChecks]=useState<Record<string,Lookup>>({});
 const [running,setRunning]=useState(false);
 async function check(nct:string){
  setChecks(s=>({...s,[nct]:{state:"loading"}}));
  try{
   const res=await fetch(
    "/predictions/scientific-reconciliation/protocol-crosswalk/check?nct="+
     encodeURIComponent(nct),{
     cache:"no-store",headers:{"Accept":"application/json"}
    });
   const data:unknown=await res.json();
   if(!res.ok||!data||typeof data!=="object"||
      !("nct" in data)||data.nct!==nct||
      !("FDAForecast" in data)||data.FDAForecast!=="ABSTAIN"||
      !("currentOriginalApiSha256" in data)||
      typeof data.currentOriginalApiSha256!=="string"||
      !/^[a-f0-9]{64}$/u.test(data.currentOriginalApiSha256)){
    setChecks(s=>({...s,[nct]:{state:"error",error:errName(data)}}));return;
   }
   setChecks(s=>({...s,[nct]:{state:"ok",report:data as Report}}));
  }catch{
   setChecks(s=>({...s,[nct]:{state:"error",
    error:"ORIGINAL_REGISTRY_SOURCE_UNAVAILABLE_NO_TRIAL_FAILURE_INFERENCE"}}));
  }
 }
 async function checkAll(){
  if(running)return;
  setRunning(true);
  try{
   for(let i=0;i<rows.length;i+=3){
    await Promise.all(rows.slice(i,i+3).map(r=>check(r.nct)));
   }
  }finally{setRunning(false);}
 }
 const success=rows.filter(r=>checks[r.nct]?.state==="ok").length;
 const fail=rows.filter(r=>checks[r.nct]?.state==="error").length;
 const totalExact=rows.reduce((n,r)=>n+(checks[r.nct]?.report?.exactTitleAndTimeframeCount??0),0);
 const totalNeeds=rows.reduce((n,r)=>n+(checks[r.nct]?.report?.needsIndependentEndpointReviewCount??0),0);
 return <section>
  <p className={styles.notice} aria-live="polite">
   <button type="button" onClick={()=>{void checkAll();}} disabled={running}
    style={{cursor:"pointer",borderRadius:7,padding:"10px 15px",
      border:"none",background:"#145b45",color:"#fff",fontWeight:750}}>
    {running?"Comparing exact original sources…":
     "Compare all 12 current protocol and posted result records"}
   </button>
   {" · "}<strong>{success}/{rows.length}</strong> source readbacks;
   {" "}{fail} source errors;
   {" "}{totalExact} exact textual outcome-and-timeframe matches;
   {" "}{totalNeeds} wording mappings requiring review among successful
   reads. All counts refer only to public CURRENT registry wording.
  </p>
  <div className={styles.coverageGrid}>
   {rows.map(row=>{
    const x=checks[row.nct],r=x?.report;
    const byKey=new Map(r?.plannedPrimaryOutcomes.map(p=>[p.key,p])??[]);
    return <article key={row.nct} className={styles.coverageGroup}>
     <strong>{row.ticker} · {row.nct}</strong>
     <div>{row.phase} · {row.cycleIds.join(", ")}</div>
     <div>Prior posted primary entry count:
      <strong> {row.archivedPrimaryOutcomeCount}</strong></div>
     <p><button type="button" disabled={running||x?.state==="loading"}
      onClick={()=>{void check(row.nct);}}
      style={{cursor:"pointer",border:"1px solid #78a695",
       background:"#fff",color:"#145b45",borderRadius:7,padding:"8px 11px"}}>
      {x?.state==="loading"?"Reading original record…":
       "Compare current protocol and posted primary endpoints"}
     </button></p>
     {x?.state==="error"&&<p role="alert">
      No source crosswalk: {x.error}. This does not imply any clinical
      failure or missing original SAP.</p>}
     {r&&<div aria-live="polite">
      {(!r.currentOriginalSourceMatchesR91Receipt||r.priorSourceCountChanged)&&
       <p role="alert">Current original API record differs from the dated
        R91 source receipt. Investigate the data change before interpreting
        any comparison; no historical version proof is established.</p>}
      <p><strong>Current registry protocol primary entries:</strong>
       {" "}{r.currentProtocolPrimaryCount}. <strong>Posted PRIMARY entries:</strong>
       {" "}{r.postedRegistryPrimaryCount}.
       Exact title/timeframe: {r.exactTitleAndTimeframeCount};
       title with differing timeframe: {r.exactTitleDifferentTimeframeCount};
       other mappings to review: {r.needsIndependentEndpointReviewCount}.</p>
      <details className={styles.coverageDetails}>
       <summary>Original primary endpoint comparison ({r.textualCrosswalk.length} posted entries)</summary>
       {r.textualCrosswalk.map((link,i)=><div key={link.postedOutcomeKey}>
        <p><b>{i+1}. Posted: {link.postedTitle}</b>
         {" · "}Timeframe: {link.postedTimeFrame??"not listed"}</p>
        <p><strong>Source text comparison:</strong> {stateLabel(link.state)}</p>
        {link.possibleProtocolKeys.length>0&&<ul>
         {link.possibleProtocolKeys.map(key=>{
          const original=byKey.get(key);
          return <li key={key}>
           <b>Protocol current listing:</b> {original?.title??"not available"}
           {" · "}Timeframe: {original?.timeFrame??"not listed"}
           {original?.description&&<div>{original.description}</div>}
          </li>;
         })}
        </ul>}
        {link.possibleProtocolKeys.length===0&&<p>
         No automated text correspondence. Recover original SAP version and
         independently map the endpoint; no result is automatically failed.</p>}
       </div>)}
       <p><b>Protocol entries without an exact textual match:</b>
        {" "}{r.protocolPrimaryWithoutExactMatch.length}.
        These are research leads only, not proof of endpoint switching.</p>
      </details>
      <details className={styles.coverageDetails}>
       <summary>Posted source analysis-population and comparison metadata</summary>
       {r.postedPrimaryOutcomes.map(v=><p key={v.key}>
        <b>{v.title}</b> — {v.populationDescription??"population not described"};
        {" "}{v.sourceReportedAnalysisGroups??0} analysis group(s),
        {" "}{v.sourceReportedDenominatorEntries??0} denominator field(s),
        {" "}{v.sourceReportedPValueEntries??0} literal reported p-value field(s).
        None independently verified against the final signed SAP.
       </p>)}
      </details>
      <small>Exact current API response SHA-256:
       <code>{r.currentOriginalApiSha256}</code>.
       Retrieved {r.retrievedAtUtc}. Prospective SAP signature: NOT VERIFIED.
       Qualified review: NOT SIGNED. FDA Forecast: ABSTAIN.</small>
     </div>}
     <p><a target="_blank" rel="noopener noreferrer" href={row.sourceUrl}>
      Open exact ClinicalTrials.gov registry source
     </a></p>
    </article>;
   })}
  </div>
 </section>;
}
