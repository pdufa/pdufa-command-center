"use client";

import {useEffect, useState} from "react";

type Field = {id:string;segment:string;status:string;latest_provenance_review?:string|null;independently_verified:boolean};
type EvidenceSummary = {program_id:string;integrity:string;readiness:string;decision:string;defined_fields:number;independently_verified:number;fields:Field[];warning?:string};

/** Read-only integration boundary. No credentials or untrusted identity assertions are sent. */
export default function ResearchEvidenceStatus({programId}:{programId:string}) {
  const [summary,setSummary]=useState<EvidenceSummary|null>(null);
  const [state,setState]=useState("CHECKING");
  useEffect(()=>{
    const controller=new AbortController();
    setSummary(null);setState("CHECKING");
    // Same-origin proxy must be connected to an authenticated, program-scoped backend.
    fetch("/api/research-evidence?program_id="+encodeURIComponent(programId),
      {cache:"no-store",credentials:"same-origin",signal:controller.signal})
      .then(async response=>{
        if(!response.ok) throw new Error("Evidence service unavailable or access denied");
        return response.json() as Promise<EvidenceSummary>;
      })
      .then(data=>{
        if(controller.signal.aborted)return;
        if(data.program_id!==programId || !Array.isArray(data.fields) ||
           data.integrity!=="CHECKED_LOCAL_CHAIN_ONLY")throw new Error("Evidence integrity or identity not established");
        setSummary(data);setState("AVAILABLE_RESEARCH_ONLY");
      })
      .catch(()=>{if(!controller.signal.aborted)setState("UNAVAILABLE");});
    return ()=>controller.abort();
  },[programId]);
  return <section aria-label="Stored research evidence status" style={{border:"2px solid #b37d35",padding:14,margin:"12px 0",background:"#fff8e9"}}>
    <h3>Stored evidence status · research only</h3>
    {state==="CHECKING" && <p role="status">Checking authorized evidence service…</p>}
    {state==="UNAVAILABLE" && <p role="alert">Evidence service unavailable or access not authorized. No stored evidence is asserted. Readiness: NOT READY · Decision: ABSTAIN.</p>}
    {summary && <div>
      <p>Program: {summary.program_id} · Defined draft fields: {summary.defined_fields} · Independently verified: {summary.independently_verified}</p>
      <p>Local audit chain: {summary.integrity} · Readiness: NOT READY · Decision: ABSTAIN</p>
      <details><summary>Show stored field-level receipt statuses</summary>
        <ul>{summary.fields.map(f=><li key={f.id}>{f.id} ({f.segment}): {f.status} · Provenance review: {f.latest_provenance_review||"NONE"} · Independently verified: NO</li>)}</ul>
      </details>
      <p>{summary.warning||"Local audit checks do not establish scientific verification."}</p>
    </div>}
    <p>This display cannot start predictions or change evidence review decisions.</p>
  </section>;
}
