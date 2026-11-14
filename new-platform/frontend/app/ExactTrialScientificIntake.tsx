"use client";
import {useState} from "react";
import ScientificStepsReadiness,{type PhaseFirstIntake} from "./ScientificStepsReadiness";

const NCT=/^NCT\d{8}$/;
type Cohort="POOL"|"FOCUS"|"PAST";
type Assessment={id?:unknown;nctId?:unknown;levelOneIntake?:unknown};
function validIntake(value:unknown):value is PhaseFirstIntake {
 if(!value||typeof value!=="object"||Array.isArray(value))return false;
 const x=value as Record<string,unknown>;
 const endpoint=x.endpointQuality as Record<string,unknown>|undefined;
 return x.fdaPrediction==="ABSTAIN"&&x.scientificValidation==="NOT_VERIFIED"&&
  (x.executionStatus==="INTAKE_ONLY"||x.executionStatus==="BLOCKED_UNVERIFIED_PHASE")&&
  !!endpoint&&endpoint.scientificScoreStatus==="NOT_VALIDATED"&&
  Array.isArray(x.notYetExpected)&&Array.isArray(x.missingEvidence)&&
  !!x.evidenceInventory&&typeof x.evidenceInventory==="object"&&!Array.isArray(x.evidenceInventory);
}
/** Explicit exact-program selection is required: an NCT may map to several programs. */
export default function ExactTrialScientificIntake({cohort,nctId,programIdentity}:{cohort:Cohort;nctId:string;programIdentity:string}){
 const [intake,setIntake]=useState<PhaseFirstIntake|null>(null);
 const [error,setError]=useState("");
 const [busy,setBusy]=useState(false);
 async function load(){
  setIntake(null);setError("");
  if(!NCT.test(nctId)||!programIdentity.trim()||programIdentity.length>512){
   setError("An exact NCT and program identity are required.");return;
  }
  setBusy(true);
  try{
   const res=await fetch("/api/assessments?identity="+encodeURIComponent(programIdentity),{cache:"no-store"});
   if(!res.ok)throw Error(res.status===401?"Sign in to view assessment evidence.":"Assessment unavailable.");
   const data:unknown=await res.json();
   if(!data||typeof data!=="object"||Array.isArray(data))throw Error("Invalid assessment response.");
   const record=data as Assessment;
   if(record.id!==programIdentity||record.nctId!==nctId||!validIntake(record.levelOneIntake))
    throw Error("Exact program/NCT mismatch or unverified intake; nothing displayed.");
   setIntake(record.levelOneIntake);
  }catch(e){setError(e instanceof Error?e.message:"Assessment unavailable.");}
  finally{setBusy(false);}
 }
 return <section aria-label={"Exact "+cohort+" trial scientific intake"}>
  <button type="button" disabled={busy} onClick={()=>void load()}>{busy?"Checking exact trial…":"Load exact-trial scientific intake"}</button>
  {error&&<p role="alert">{error}</p>}
  {intake&&<ScientificStepsReadiness cohort={cohort} trial={{nctId,assessmentNctId:nctId,intake}}/>}
 </section>;
}

/** Manual exact-program selection until a verified NCT-to-program mapping is available. */
export function ExactTrialIntakeSelector({cohort,nctId}:{cohort:Cohort;nctId:string}){
 const [identity,setIdentity]=useState("");
 const [selected,setSelected]=useState("");
 return <div style={{marginTop:8}}>
  <label style={{display:"block",fontSize:12}}>Exact program ID (not ticker or NCT)
   <input aria-label={"Exact program ID for "+nctId} value={identity} onChange={e=>{setIdentity(e.target.value);setSelected("");}}
    maxLength={512} placeholder="Enter verified program ID" style={{display:"block",width:"100%",maxWidth:260}}/>
  </label>
  <button type="button" disabled={!identity.trim()} onClick={()=>setSelected(identity.trim())}>Select program</button>
  {selected&&<ExactTrialScientificIntake key={nctId+":"+selected} cohort={cohort} nctId={nctId} programIdentity={selected}/>}
  <p style={{fontSize:11}}>Program identity must be verified separately. No automatic NCT-to-program match is assumed.</p>
 </div>;
}
