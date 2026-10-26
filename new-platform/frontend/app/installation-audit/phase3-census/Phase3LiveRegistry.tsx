"use client";

import { useEffect, useRef, useState } from "react";
import type { RegistryResearchRecord } from "../../../lib/phase3-live-registry";

type ResearchFetchState = {data: RegistryResearchRecord|null; error:string; loading:boolean};

/**
 * One browser-triggered authenticated GET for an EXACT census NCT.
 * Never saves observations, qualifies Pipeline, infers FDA review cycles,
 * or overwrites the historical source census.
 */
export default function Phase3LiveRegistry({
  nctId, datedStatus, censusLeadCompany,
}: {nctId:string; datedStatus:string; censusLeadCompany:string}) {
  const [state,setState]=useState<ResearchFetchState>({data:null,error:"",loading:false});
  const abort=useRef<AbortController|null>(null);
  useEffect(()=>{
    abort.current?.abort();
    setState({data:null,error:"",loading:false});
    return ()=>abort.current?.abort();
  },[nctId]);

  async function inspectOriginalRegistry() {
    abort.current?.abort();
    const controller=new AbortController();
    abort.current=controller;
    setState({data:null,error:"",loading:true});
    try {
      const res=await fetch("/api/phase3-registry?exact_nct="+encodeURIComponent(nctId),{
        cache:"no-store",signal:controller.signal,
      });
      if(!res.ok) throw new Error(res.status===401
        ? "Sign in to the PDUFA dashboard to inspect the current registry source."
        : "Exact-NCT registry source is unavailable or invalid. No new evidence is accepted.");
      const data:RegistryResearchRecord=await res.json();
      if(controller.signal.aborted)return;
      if(data.nctId!==nctId || data.verifiedUsFdaPdufa!==false
          || data.verifiedCommercialDevelopment!==false
          || data.verifiedPipelineQualification!==false
          || data.qualifiedPipelineTotal!==null || data.approvalProbability!==null) {
        throw new Error("Source integrity refused.");
      }
      setState({data,error:"",loading:false});
    } catch(e) {
      if(controller.signal.aborted)return;
      setState({data:null,error:e instanceof Error && e.message.startsWith("Sign in")
        ? e.message : "Registry read-only lookup failed; no source or Pipeline outcome was verified.",
        loading:false});
    }
  }

  const entry=state.data;
  return <section aria-label={"Current official registry source for "+nctId}
    style={{padding:12,background:"#fff",border:"1px solid #cbd5e1",borderRadius:8,marginTop:15}}>
    <h4>Inspect current original trial registry source</h4>
    <p>This lookup reads the current public ClinicalTrials.gov record for
      this exact NCT and shows its study title, registered drug/interventions,
      conditions, lead sponsor, phase and status. These are <strong>registry
      statements, not independently corroborated current company programs,
      FDA authorizations, PDUFA dates or Pipeline passes.</strong></p>
    <button type="button" onClick={()=>void inspectOriginalRegistry()} disabled={state.loading}>
      {state.loading?"Checking original registry…":"Read current ClinicalTrials.gov source"}
    </button>
    {state.error && <p role="alert">{state.error}</p>}
    {entry && <div role="status">
      <p><strong>{entry.nctId}: {entry.title}</strong></p>
      <p>Current recorded status: <strong>{entry.registryOverallStatus}</strong>
        {" "}· Dated census status: {datedStatus}
        {entry.registryOverallStatus!==datedStatus
          ? " — status differs from the dated census; resolve the discrepancy before assessing eligibility."
          : " — matches dated status text; still requires source and date checks."}</p>
      <p>Lead sponsor as currently registered: <strong>{entry.registryLeadSponsor??"Not supplied"}</strong>
        {" "}· Dated exact-matched listed company: <strong>{censusLeadCompany}</strong>.
        Registration does not establish present intellectual-property or development rights.</p>
      <p>Phases: {entry.reportedPhases.join(", ")||"Not reported"}.
        {" "}{entry.phase3CurrentlyReported
          ? "The current registration includes Phase 3."
          : "The current registration does not establish Phase 3; verify differences before use."}</p>
      <p>Registered conditions: {entry.conditions.join("; ")||"Not reported"}.</p>
      <p>Registered interventions: {entry.interventions.map(item=>item.type+": "+item.name).join("; ")||"Not reported"}.</p>
      <p>Registry record last posted update: {entry.sourceUpdated??"Not reported"}
        {" "}· This lookup: {entry.queriedAt}.</p>
      <p><a href={entry.recordUrl} target="_blank" rel="noopener noreferrer">Open the exact original ClinicalTrials.gov study</a>
        {" "}· <a href={entry.apiRecordUrl} target="_blank" rel="noopener noreferrer">Open raw registry API record</a>.</p>
      <p><strong>FDA pathway/PDUFA: NOT VERIFIED.</strong>
        {" "}Drug names and registry status cannot establish an FDA action cycle,
        formal regulatory designation, pending PDUFA date or approval prediction.</p>
    </div>}
    <p><small>Additional independent research:
      {" "}<a href="https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm" target="_blank" rel="noopener noreferrer">FDA Drugs@FDA database</a>
      {" "}· <a href="https://www.sec.gov/edgar/search/" target="_blank" rel="noopener noreferrer">SEC EDGAR company filings</a>.
      These are search starting points, NOT established trial-to-FDA or sponsor-rights matches.</small></p>
  </section>;
}
