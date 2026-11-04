"use client";
import {useEffect,useRef,useState} from "react";
import {createPortal} from "react-dom";
import type {ReadoutRow} from "../lib/phase3-public-readout";
import {loadRegistryEvidenceIndex,registryTrialFor,
 type RegistryTrialEvidence} from "../lib/raas-registry-evidence";

/** Opens primary source evidence for every research NCT, including trials
 * whose TOP/BOTTOM stage remains unverified. Nothing here assigns a score. */
export default function RaasRegistryEvidenceButton({row}:{row:ReadoutRow}){
 const [open,setOpen]=useState(false);
 const [loading,setLoading]=useState(false);
 const [evidence,setEvidence]=useState<RegistryTrialEvidence|null>(null);
 const [sourceAsOf,setSourceAsOf]=useState("");
 const trigger=useRef<HTMLButtonElement>(null);
 useEffect(()=>{
  if(!open)return;
  let active=true;
  setLoading(true);
  void loadRegistryEvidenceIndex().then(index=>{
   if(!active)return;
   setEvidence(registryTrialFor(index,{nctId:row.nctId,ticker:row.ticker}));
   setSourceAsOf(index?.sourceAsOf||"");
   setLoading(false);
  });
  const onKey=(ev:KeyboardEvent)=>{if(ev.key==="Escape")setOpen(false);};
  document.addEventListener("keydown",onKey);
  return ()=>{
   active=false;
   document.removeEventListener("keydown",onKey);
   trigger.current?.focus();
  };
 },[open,row.nctId,row.ticker]);
 return <>
  <button ref={trigger} type="button" aria-expanded={open}
   data-raas-registry-evidence-button={row.nctId}
   onClick={()=>setOpen(v=>!v)}
   style={{padding:"7px 9px",border:"1px solid #8ca5bc",
    borderRadius:7,background:"#eef4fb",color:"#173f5e",cursor:"pointer",fontWeight:700}}>
   Registry facts ▸
  </button>
  {open&&createPortal(
   <div role="presentation" onClick={ev=>{if(ev.target===ev.currentTarget)setOpen(false);}}
    style={{position:"fixed",inset:0,zIndex:1300,background:"rgba(9,25,43,.65)",
     display:"flex",justifyContent:"flex-end",padding:12}}>
    <section role="dialog" aria-modal="true"
     aria-label={"Primary registry evidence for "+row.ticker+" "+row.nctId}
     data-raas-registry-evidence={row.nctId}
     style={{width:"min(730px,96vw)",height:"100%",overflowY:"auto",color:"#173f5e",
      background:"#fff",padding:18,borderRadius:12}}>
     <header style={{display:"flex",alignItems:"start",justifyContent:"space-between",gap:12}}>
      <div>
       <strong style={{fontSize:18}}>{row.ticker} · {row.nctId}</strong>
       <p style={{margin:"4px 0"}}>Public ClinicalTrials.gov evidence — not a numeric RAAS grade</p>
      </div>
      <button type="button" onClick={()=>setOpen(false)}>Close ✕</button>
     </header>
     {loading?<p role="status">Loading the verified source inventory…</p>:
      !evidence?<p role="alert">This trial has no matching published source inventory available in this dashboard snapshot.
       Its missing evidence remains N/A; no score is inferred.</p>:
      <>
       <p><strong>Source inventory collected:</strong> {sourceAsOf||evidence.retrievedAt}.
        <strong> Registry status:</strong> {evidence.registryStatus||"Not reported"}.
        <strong> Stage classification:</strong> separate issuer/FDA evidence required.</p>
       <p><a href={evidence.sourceUrl} target="_blank" rel="noopener noreferrer">
        Open exact NCT primary registry and original result tables</a></p>
       <div role="status" style={{display:"flex",gap:14,flexWrap:"wrap",
        padding:10,border:"1px solid #c4d7eb",borderRadius:8}}>
        <span><strong>{evidence.primaryDefinitions.length}</strong> listed primary endpoints</span>
        <span><strong>{evidence.postedPrimaryOutcomeCount}</strong> posted primary outcomes</span>
        <span><strong>{evidence.primaryResults.reduce((n,x)=>n+x.analysisCount,0)}</strong> primary analyses (indexed)</span>
        <span><strong>{evidence.seriousAdverseEventTermCount}</strong> serious-event terms</span>
       </div>
       <p><strong>Official results:</strong> {evidence.postedResults?
        "Registry-posted results present; require metric-specific review before scoring":
        "Not posted in the source snapshot — protocol information only"}.
        {" "}First result publication: {evidence.resultsFirstPosted||"Not verified"}.</p>
       <p><strong>Registered interventions:</strong> {evidence.registeredInterventions.length?
        evidence.registeredInterventions.join(", "):"Not in this source snapshot — program-specific attribution requires review"}.</p>
       <details open>
        <summary style={{fontWeight:700,cursor:"pointer"}}>Registered primary outcome definitions</summary>
        {evidence.primaryDefinitions.length?evidence.primaryDefinitions.map((x,i)=>
         <p key={i}>{x.measure} · {x.timeFrame||"Time frame missing"}</p>):
         <p>Primary endpoint details not recorded in this compact source.</p>}
       </details>
       {evidence.postedResults&&<details>
        <summary style={{fontWeight:700,cursor:"pointer"}}>Posted primary outcome analyses</summary>
        {evidence.primaryResults.length?evidence.primaryResults.map((x,i)=>
         <div key={i} style={{borderTop:"1px solid #dee7ef",padding:10}}>
          <strong>{x.title||"Untitled primary endpoint"}</strong>
          <p>Time frame: {x.timeFrame||"Not specified"} · Unit: {x.unit||"Not specified"}</p>
          <p>Reported analysis entries: {x.analysisCount}.
           {" "}Reported p-values: {x.pValues.length?x.pValues.join(", "):"Not displayed"}</p>
          <p>A p-value alone is not an effect size or clinically meaningful RAAS grade.</p>
         </div>):
         <p>Registry marks results posted, but primary outcome detail is not available in this summary.</p>}
       </details>}
       <p><strong>Source hash:</strong> <code>{evidence.sourceHash.slice(0,18)}…</code>
        {" "}· <strong>Retrieved:</strong> {evidence.retrievedAt}</p>
       <p><strong>Still needed:</strong> independent comparator analysis, confidence intervals,
        medical relevance, SEC financial data, FDA status and risk review as applicable.
        Neither this report nor its source date is a historical RAAS prediction.</p>
      </>}
    </section>
   </div>,document.body)}
 </>;
}
