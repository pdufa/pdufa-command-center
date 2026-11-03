"use client";
import {useEffect,useRef,useState} from "react";
import type {RegistryBenefitResearch} from "../lib/registry-benefit-research";
import {auditLiveRegistryForRaas,type RaasLiveRegistryAudit}
 from "../lib/raas-live-registry-audit";
import {observedSeriousEventRate} from "../lib/registry-observation-math";
/** A direct user-initiated scan, so opening 50 spreadsheet rows does not
 * silently make 50 upstream requests to ClinicalTrials.gov. */
export default function RaasLiveRegistryEvidence({nctId,stage}:{nctId:string;stage:"pre"|"post"}){
 const [result,setResult]=useState<RegistryBenefitResearch|null>(null);
 const [audit,setAudit]=useState<RaasLiveRegistryAudit|null>(null);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState<string|null>(null);
 const abort=useRef<AbortController|null>(null);
 useEffect(()=>()=>abort.current?.abort(),[]);
 const scan=()=>{
  abort.current?.abort();
  const ctl=new AbortController();abort.current=ctl;
  setBusy(true);setError(null);
  void fetch("/api/tools-trial-evidence?nct="+encodeURIComponent(nctId),
   {cache:"no-store",signal:ctl.signal})
   .then(async response=>{
    if(!response.ok)throw Error(response.status===401?
     "Sign in to the PDUFA dashboard to read this exact-NCT registry source.":
     "Primary registry unavailable for this trial; no values or scores inferred.");
    const raw=await response.json() as RegistryBenefitResearch;
    const verified=auditLiveRegistryForRaas(raw,nctId,stage);
    return {raw,verified};
   })
   .then(({raw,verified})=>{if(!ctl.signal.aborted){setResult(raw);setAudit(verified);}})
   .catch(()=>{if(!ctl.signal.aborted){
    setResult(null);setAudit(null);
    setError("Registry data unavailable or unverified. No RAAS rating inferred.");
   }})
   .finally(()=>{if(!ctl.signal.aborted)setBusy(false);});
 };
 return <section data-raas-live-registry={nctId} style={{
  border:"1px solid #b5cfbd",borderRadius:8,padding:10,background:"#fff",
  display:"flex",flexDirection:"column",gap:8,fontSize:12}}>
  <strong>Scan this trial's live ClinicalTrials.gov evidence</strong>
  <p style={{margin:0}}>Fetch primary endpoint, secondary endpoint, and serious
   adverse-event observations for exactly {nctId}. This is source research,
   not an approved RAAS grade or stock forecast.</p>
  <button type="button" disabled={busy} onClick={scan}
    style={{padding:10,minHeight:44,alignSelf:"flex-start",fontWeight:750,
      border:"1px solid #52866a",borderRadius:6,color:"#17462d",background:"#e9f5ed"}}>
   {busy?"Checking primary registry…":audit?"Refresh exact-NCT registry scan":"Scan registry evidence now"}
  </button>
  {error&&<p role="alert" style={{margin:0}}>{error}</p>}
  {audit&&result&&<div data-raas-live-result={audit.status} style={{display:"flex",flexDirection:"column",gap:8}}>
    <p style={{margin:0}}><strong>{audit.status==="REGISTRY_POSTED_UNGRADED"?
     "Posted results located — ungraded":"Protocol only — no registry outcome results posted"}</strong>
     {" · "}Registry phases: {result.registeredPhases.join(", ")||"Not recorded"}
     {" · "}Retrieved: {audit.retrievedAt}
     {" · "}Source last updated: {audit.sourceUpdated??"Not recorded"}</p>
    <p style={{margin:0}}><strong>Outcome inventory:</strong> {audit.primaryOutcomes} primary outcomes
     ({audit.primaryMeasurements} reported measurements, {audit.primaryWithAnalysis} with
     analyses), {audit.secondaryOutcomes} other outcomes ({audit.secondaryMeasurements}
     {" "}measurements), {audit.seriousAdverseEventTerms} SAE terms
     ({audit.seriousAdverseEventArms} valid group counts).</p>
    <p style={{margin:0}}><strong>RAAS research leads (not metric grades):</strong>
     {" "}{audit.preliminaryMetricLeads.length?audit.preliminaryMetricLeads.join(", "):
      "No metric-specific outcome source leads can be assigned from this packet."}</p>
    <a href={audit.sourceUrl} target="_blank" rel="noopener noreferrer">
      Open exact trial source and reported statistical analyses
    </a>
    {result.primary.slice(0,5).map((outcome,i)=><details key={"p"+i}>
      <summary style={{cursor:"pointer",fontWeight:700}}>
       Primary endpoint {i+1}: {outcome.title} ({outcome.measurements.length} measurements)
      </summary>
      <p>Time frame: {outcome.timeFrame??"Not given"} · Unit: {outcome.unit??"Not given"}
       {" · "}Analysis reported: {outcome.analysisReported?"Yes":"No"}</p>
      {outcome.measurements.slice(0,10).map((m,j)=><p key={j}>
       {m.group}: {m.value}{m.spread?" · spread "+m.spread:""}
      </p>)}
    </details>)}
    {result.secondary.length>0&&<details>
      <summary style={{cursor:"pointer",fontWeight:700}}>
       Other reported endpoints ({result.secondary.length})
      </summary>
      {result.secondary.slice(0,5).map((o,i)=><p key={i}>{o.title} · {o.measurements.length} measurements
      {" · "}{o.timeFrame??"Time not stated"}</p>)}
    </details>}
    {result.seriousAdverseEvents.length>0&&<details>
      <summary style={{cursor:"pointer",fontWeight:700}}>
       Serious adverse-event terms ({result.seriousAdverseEvents.length})
      </summary>
      {result.seriousAdverseEvents.slice(0,8).map((e,i)=><div key={i}>
       <strong>{e.term}</strong>
       {e.groups.slice(0,6).map((g,j)=><p key={j}>
        {g.group}: {g.affected}/{g.atRisk} affected ·
        {" "}{observedSeriousEventRate(g.affected,g.atRisk)??"Unknown"}% observed
       </p>)}
      </div>)}
    </details>}
    {audit.limitations.map((note,i)=><p key={i} style={{margin:0,color:"#725d35"}}>
      {note}
    </p>)}
    {result.truncatedEvidence.outcomes||result.truncatedEvidence.seriousEvents?
     <p>Source results were truncated for display. Use the ClinicalTrials.gov link for complete tables.</p>:null}
  </div>}
 </section>;
}
