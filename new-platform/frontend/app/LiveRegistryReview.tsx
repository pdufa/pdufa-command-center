"use client";

import { useState } from "react";
import styles from "./FunnelWorkspace.module.css";
import type { RegistryReview } from "../lib/pipeline-live-registry";

export default function LiveRegistryReview({nctId}:{nctId:string}){
 const [value,setValue]=useState<RegistryReview|null>(null);
 const [working,setWorking]=useState(false);
 const [error,setError]=useState("");
 const check=async()=>{
  if(working)return;
  setWorking(true);setError("");
  try{
   const resp=await fetch("/api/phase3-trial?nct="+encodeURIComponent(nctId),{cache:"no-store"});
   if(!resp.ok)throw Error(resp.status===401?"Sign into the dashboard first.":"Current ClinicalTrials.gov record unavailable.");
   const raw:unknown=await resp.json();
   const r=raw as RegistryReview;
   if(!r||r.nctId!==nctId||r.qualification!=="NEEDS_REVIEW"||r.sourceUrl!=="https://clinicaltrials.gov/study/"+nctId)
    throw Error("The external registry response did not match this trial.");
   setValue(r);
  }catch(e){setValue(null);setError(e instanceof Error?e.message:"Registry lookup unavailable");}
  finally{setWorking(false)}
 };
 return <details className={styles.dossierSection}>
  <summary><strong>Current ClinicalTrials.gov registry check</strong><span>On demand · source-linked</span></summary>
  <div className={styles.dossierEvidence}>
   <p className={styles.muted}>Refresh the official study record for this exact NCT. This does not verify a pivotal readout, regulatory approval, market cap, or PDUFA date.</p>
   <button type="button" disabled={working} onClick={()=>void check()}>{working?"Checking registry…":"Check official registry now"}</button>
   {error&&<p role="alert" className={styles.error}>{error} No Pipeline eligibility changed.</p>}
   {value&&<div aria-label={"Registry facts for "+nctId}>
    <p><strong>Registry qualification:</strong> NEEDS REVIEW — {value.registryAssessment.replaceAll("_"," ")}</p>
    <p><strong>Trial title:</strong> {value.title||"Not recorded"}</p>
    <p><strong>Registered phase:</strong> {value.phases.join(", ")||"Not recorded"} · <strong>Status:</strong> {value.registryStatus||"Not recorded"}</p>
    <p><strong>Lead sponsor:</strong> {value.leadSponsor||"Not recorded"}</p>
    <p><strong>Registered conditions:</strong> {value.conditions.join("; ")||"Not recorded"}</p>
    <p><strong>Registered interventions:</strong> {value.interventions.join("; ")||"Not recorded"}</p>
    <p><strong>Primary completion:</strong> {value.primaryCompletionDate||"Not recorded"} · <strong>Last update posted:</strong> {value.lastUpdatePosted||"Not recorded"}</p>
    <p><strong>Enrollment:</strong> {value.enrollment===null?"Not recorded":value.enrollment} · <strong>Registry results posted:</strong> {value.resultsPosted?"Yes":"Not confirmed"}</p>
    <p><strong>Checked:</strong> {value.verifiedAt} · <a href={value.sourceUrl} target="_blank" rel="noopener noreferrer">View original study on ClinicalTrials.gov</a></p>
    <p><a href={"/api/phase3-trial?nct="+encodeURIComponent(nctId)+"&format=csv"} download={"pdufa-registry-evidence-"+nctId+".csv"}>Download this trial’s registry evidence for Google Sheets review</a></p>
    <p className={styles.muted}>The CSV makes a fresh official registry request. Import into tab 20 Registry Evidence Intake; it does not verify the proposed drug, pivotal results, PDUFA, or market cap. Reviewer approval is required.</p>
    <details><summary>What must still be verified?</summary><ul>{value.remainingChecks.map(x=><li key={x}>{x}</li>)}</ul></details>
   </div>}
  </div>
 </details>;
}
