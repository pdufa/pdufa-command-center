"use client";

import {useEffect, useState} from "react";

/** v1.1 planning inventory: these are eight segment-level controls, NOT 650 enumerated fields. */
const SEGMENTS = [
  {id:"BIO",title:"Disease Biology & Medical Rationale",planned:45,critical:false},
  {id:"MOA",title:"Therapeutic Strategy & Mechanism of Action",planned:65,critical:false},
  {id:"TRIAL",title:"Clinical Trial Design & Execution",planned:80,critical:true},
  {id:"EFFICACY",title:"Clinical Efficacy & Statistical Evidence",planned:110,critical:true},
  {id:"SAFETY",title:"Safety & Benefit–Risk",planned:85,critical:true},
  {id:"CMC",title:"Regulatory & Manufacturing (CMC)",planned:100,critical:true},
  {id:"PRECEDENT",title:"Historical FDA Comparisons & Precedents",planned:75,critical:false},
  {id:"VALIDATION",title:"Prediction, Uncertainty & Evidence Validation",planned:90,critical:true},
] as const;
type Setting = {included:boolean;mandatory:boolean};
type Settings = Record<string,Setting>;
const defaults = ():Settings => Object.fromEntries(SEGMENTS.map(s=>[s.id,{included:true,mandatory:s.critical}]));
const storageKey=(trialKey:string)=>"pdufa-research-v1.1-segments:"+trialKey;
export default function EvidenceSegmentControls({trialKey}:{trialKey:string}) {
  const [settings,setSettings]=useState<Settings>(defaults);
  const [loaded,setLoaded]=useState(false);
  useEffect(()=>{
    setLoaded(false);
    let next=defaults();
    try {
      const raw=window.localStorage.getItem(storageKey(trialKey));
      if(raw) {
        const saved=JSON.parse(raw) as Settings;
        for(const s of SEGMENTS) {
          if(typeof saved?.[s.id]?.included==="boolean" && typeof saved?.[s.id]?.mandatory==="boolean")
            next[s.id]={included:saved[s.id].included,mandatory:saved[s.id].mandatory};
        }
      }
    } catch { /* Storage unavailable: use safe defaults. */ }
    setSettings(next);setLoaded(true);
  },[trialKey]);
  useEffect(()=>{if(!loaded)return;try{window.localStorage.setItem(storageKey(trialKey),JSON.stringify(settings));}catch{/* Local persistence is best-effort. */}},[settings,loaded,trialKey]);
  const update=(id:string,patch:Partial<Setting>)=>setSettings(prev=>({...prev,[id]:{...prev[id],...patch}}));
  const excludedCritical=SEGMENTS.filter(s=>s.critical && !settings[s.id]?.included);
  const enabled=SEGMENTS.filter(s=>settings[s.id]?.included).length;
  return <section style={{border:"2px solid #8a9d8e",padding:16,marginTop:18,background:"#fff"}} aria-label="Requirements v1.1 evidence segment controls">
    <h3>Scientific evidence controls · Requirements v1.1</h3>
    <p><strong>Planning inventory:</strong> 8 segments / 650 proposed field slots. Individual fields have not yet been enumerated or deduplicated. Segment switches are research-only and do not change Pipeline, GEM JR, GEM, WT or FS/FA restrictions.</p>
    <p>Segments included: {enabled}/8 · Independently verified fields: 0 · Missing field count: unknown until catalog and ingestion are complete.</p>
    {excludedCritical.length>0 && <p role="alert" style={{border:"2px solid #a11",background:"#fff1f1",padding:12}}>
      CRITICAL EVIDENCE OVERRIDE: {excludedCritical.map(s=>s.title).join("; ")} excluded. Readiness is BLOCKED; no decision may be issued. This choice is recorded in browser storage only, not a server audit trail.
    </p>}
    <div style={{display:"flex",gap:8,flexWrap:"wrap"}}>
      <button type="button" onClick={()=>setSettings(prev=>Object.fromEntries(SEGMENTS.map(s=>[s.id,{...prev[s.id],included:true}])))}>Select All</button>
      <button type="button" onClick={()=>setSettings(prev=>Object.fromEntries(SEGMENTS.map(s=>[s.id,{...prev[s.id],included:false}])))}>Deselect All</button>
      <button type="button" onClick={()=>setSettings(defaults())}>Restore Defaults</button>
    </div>
    {SEGMENTS.map(s=><details key={s.id} style={{border:"1px solid #ddd",marginTop:10,padding:12}}>
      <summary><strong>{s.title}</strong> · {s.planned} planned slots · {settings[s.id]?.included?"ON":"OFF"} · Verified 0 / Missing unknown</summary>
      <p>{s.critical?"Critical evidence category: exclusion blocks readiness.":"Noncritical segment: applicability must still be assessed."}</p>
      <label style={{marginRight:20}}><input type="checkbox" checked={!!settings[s.id]?.included} onChange={e=>update(s.id,{included:e.target.checked})}/> Include segment</label>
      <label><input type="checkbox" checked={!!settings[s.id]?.mandatory} onChange={e=>update(s.id,{mandatory:e.target.checked})}/> Mandatory for review</label>
      <p>Field-level weights, source citations, applicability, timestamps, and status: NOT YET IMPLEMENTED. No evidence is scored here.</p>
    </details>)}
    <p><strong>Evidence readiness:</strong> NOT READY · <strong>FDA decision:</strong> ABSTAIN · <strong>Extension risk:</strong> NOT ASSESSED</p>
    <p>Selections are saved locally on this browser for this program; they are not synced across devices or written to the scientific audit log.</p>
  </section>;
}
