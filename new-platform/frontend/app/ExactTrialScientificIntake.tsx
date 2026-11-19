"use client";
import {useEffect,useRef,useState} from "react";
import ScientificStepsReadiness,{type PhaseFirstIntake} from "./ScientificStepsReadiness";

import ScientificLevelsEvidence from "./ScientificLevelsEvidence";
import ScientificPopulationEvidence from "./ScientificPopulationEvidence";
import ScientificSafetyExposureEvidence from "./ScientificSafetyExposureEvidence";

const scientificLevelOptions=[
 [1,"Trial identity"],[2,"Trial design"],[3,"Statistics and efficacy"],[4,"Safety"],
 [5,"Indication-specific relevance"],[6,"Regulatory readiness"],
] as const;
const NCT=/^NCT\d{8}$/;
type Cohort="POOL"|"FOCUS"|"PAST";
type SavedVersion={assessedAt:string;modelVersion:string;evidenceHash:string};
type Assessment={id?:unknown;nctId?:unknown;levelOneIntake?:unknown;levelsTwoToSix?:unknown;levelsSevenToTwenty?:unknown;history?:unknown};
function verifiedHistory(value:unknown):SavedVersion[]|null {
 if(!Array.isArray(value)||value.length>25)return null;
 return value.every(row=>row&&typeof row.assessedAt==="string"&&Number.isFinite(Date.parse(row.assessedAt))&&
  typeof row.modelVersion==="string"&&row.modelVersion.length>0&&
  typeof row.evidenceHash==="string"&&/^[0-9a-f]{64}$/.test(row.evidenceHash))
  ? value.map(({assessedAt,modelVersion,evidenceHash})=>({assessedAt,modelVersion,evidenceHash})) : null;
}
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
 const [selectedLevel,setSelectedLevel]=useState(0);
 const [intake,setIntake]=useState<PhaseFirstIntake|null>(null);
 const [levels,setLevels]=useState<unknown>(null);
 const [extensions,setExtensions]=useState<unknown>(null);
 const [history,setHistory]=useState<SavedVersion[]|null>(null);
 const [error,setError]=useState("");
 const [busy,setBusy]=useState(false);
 const requestSequence=useRef(0);
 useEffect(()=>()=>{++requestSequence.current;},[nctId,programIdentity]);
 async function load(){
  const sequence=++requestSequence.current;
  setIntake(null);setError("");setLevels(null);setExtensions(null);setHistory(null);
  if(!NCT.test(nctId)||!programIdentity.trim()||programIdentity.length>512){
   setError("An exact NCT and program identity are required.");return;
  }
  setBusy(true);
  try{
   const res=await fetch("/api/assessments?identity="+encodeURIComponent(programIdentity),{cache:"no-store"});
   if(!res.ok)throw Error(res.status===401?"Sign in to view assessment evidence.":res.status===404?"Exact program not found in the current assessment universe.":res.status===409?"Exact program identity or evidence is not verified; refresh and check the NCT.":"Assessment unavailable.");
   const data:unknown=await res.json();
   if(!data||typeof data!=="object"||Array.isArray(data))throw Error("Invalid assessment response.");
   const record=data as Assessment;
   if(record.id!==programIdentity||record.nctId!==nctId||!validIntake(record.levelOneIntake))
    throw Error("Exact program/NCT mismatch or unverified intake; nothing displayed.");
   if(sequence===requestSequence.current)setIntake(record.levelOneIntake);
   if(sequence===requestSequence.current)setLevels(record.levelsTwoToSix);
   if(sequence===requestSequence.current)setExtensions(record.levelsSevenToTwenty);
   if(sequence===requestSequence.current)setHistory(verifiedHistory(record.history));
  }catch(e){if(sequence===requestSequence.current)setError(e instanceof Error?e.message:"Assessment unavailable.");}
  finally{if(sequence===requestSequence.current)setBusy(false);}
 }
 return <section aria-label={"Exact "+cohort+" trial scientific intake"}>
  <button type="button" disabled={busy} onClick={()=>void load()}>{busy?"Checking exact trial…":"Load exact-trial scientific intake"}</button>
  {error&&<p role="alert">{error}</p>}
  {intake&&<>
   <label>Scientific level <select value={selectedLevel} onChange={event=>setSelectedLevel(Number(event.target.value))}>
    <option value={0}>All six levels</option>
    {scientificLevelOptions.map(([number,label])=><option key={number} value={number}>Level {number} · {label}</option>)}
   </select></label>
   {(selectedLevel===0||selectedLevel===1)&&<ScientificStepsReadiness cohort={cohort} trial={{nctId,assessmentNctId:nctId,intake}}/>}
   {(selectedLevel===0||selectedLevel>1)&&<ScientificLevelsEvidence value={levels} selectedLevel={selectedLevel||undefined}/>}
  </>}
  {intake&&selectedLevel===0&&<ScientificSafetyExposureEvidence value={extensions}/>}
  {intake&&selectedLevel===0&&<ScientificPopulationEvidence value={extensions}/>}
  {intake&&history!==null&&<details>
   <summary>Saved assessment versions</summary>
   {history.length===0?<p>No saved versions for this program.</p>:<ol>{history.map((version,index)=><li key={version.assessedAt+":"+version.evidenceHash+":"+index}>
    <time dateTime={version.assessedAt}>{version.assessedAt}</time> · {version.modelVersion} · Evidence SHA-256 <code>{version.evidenceHash}</code>
   </li>)}</ol>}
  </details>}
 </section>;
}

/** Manual exact-program selection until a verified NCT-to-program mapping is available. */
export function ExactTrialIntakeSelector({cohort,nctId}:{cohort:Cohort;nctId:string}){
 const [identity,setIdentity]=useState("");
 const [selected,setSelected]=useState("");
 const [matches,setMatches]=useState<string[]>([]);
 const [lookupStatus,setLookupStatus]=useState("");
 const [lookingUp,setLookingUp]=useState(false);
 const lookupSequence=useRef(0);
 useEffect(()=>{
  ++lookupSequence.current;
  setIdentity("");setSelected("");setMatches([]);setLookupStatus("");setLookingUp(false);
 },[nctId]);
 async function lookup(){
  const sequence=++lookupSequence.current;
  setSelected("");setIdentity("");setMatches([]);setLookupStatus("");
  if(!NCT.test(nctId)){setLookupStatus("Exact NCT required.");return;}
  setLookingUp(true);
  try{
   const response=await fetch("/api/assessments",{cache:"no-store"});
   if(!response.ok)throw Error("Assessment index unavailable or sign-in required.");
   const raw:unknown=await response.json();
   if(sequence!==lookupSequence.current)return;
   if(!raw||typeof raw!=="object"||Array.isArray(raw))throw Error("Invalid assessment index.");
   const data=raw as {status?:unknown;exactNctProgramMap?:unknown};
   if(data.status!=="COMPLETE"||!data.exactNctProgramMap||typeof data.exactNctProgramMap!=="object"||Array.isArray(data.exactNctProgramMap))
    throw Error("Exact identity index not ready.");
   const values=(data.exactNctProgramMap as Record<string,unknown>)[nctId];
   if(!Array.isArray(values)||!values.length){setLookupStatus("No exact program mapping found.");return;}
   if(!values.every(x=>typeof x==="string"&&x.trim()&&x.length<=512)||new Set(values).size!==values.length)
    throw Error("Malformed program identities.");
   setMatches(values as string[]);
   if(values.length===1){setIdentity(values[0]);setSelected(values[0]);setLookupStatus("Unique NCT-linked program found; review evidence below.");}
   else setLookupStatus("Multiple programs share this NCT. Select the correct program.");
  }catch(e){if(sequence===lookupSequence.current)setLookupStatus(e instanceof Error?e.message:"Identity lookup unavailable.");}
  finally{if(sequence===lookupSequence.current)setLookingUp(false);}
 }

 return <div style={{marginTop:8}}>
  <label style={{display:"block",fontSize:12}}>Exact program ID (not ticker or NCT)
   <input aria-label={"Exact program ID for "+nctId} value={identity} onChange={e=>{setIdentity(e.target.value);setSelected("");}}
    maxLength={512} placeholder="Enter verified program ID" style={{display:"block",width:"100%",maxWidth:260}}/>
  </label>
  <button type="button" disabled={lookingUp} onClick={()=>void lookup()}>{lookingUp?"Finding programs…":"Find programs for NCT"}</button>
  {lookupStatus&&<p role="status">{lookupStatus}</p>}
  {matches.length>1&&<label>Matching programs <select aria-label={"Matching programs for "+nctId} value={identity} onChange={e=>{setIdentity(e.target.value);setSelected("");}}><option value="">Choose exact program</option>{matches.map(id=><option key={id} value={id}>{id}</option>)}</select></label>}
  <button type="button" disabled={!identity.trim()} onClick={()=>setSelected(identity.trim())}>Select program</button>
  {selected&&<ExactTrialScientificIntake key={nctId+":"+selected} cohort={cohort} nctId={nctId} programIdentity={selected}/>}
  <p style={{fontSize:11}}>NCT mapping does not verify historical FDA event linkage. Multiple programs require explicit selection.</p>
 </div>;
}
