"use client";
import {useEffect,useState} from "react";
import type {RegistryBenefitResearch,RegistryOutcome} from "../lib/registry-benefit-research";
import css from "./ToolsBenefitMatrix.module.css";

/** Automatic single-study source lookup on trial change. Raw observed results
 * are shown as source material; NOT auto-graded therapy advantages.
 */
export default function RegistryBenefitEvidence({nctId,assessment}:{nctId:string;assessment:number}){
  const [data,setData]=useState<RegistryBenefitResearch|null>(null);
  const [failure,setFailure]=useState("");
  const [loading,setLoading]=useState(false);
  const [attempt,setAttempt]=useState(0);
  useEffect(()=>{
    if(!/^NCT\d{8}$/.test(nctId))return;
    const controller=new AbortController();
    setData(null);setFailure("");setLoading(true);
    void fetch("/api/registry-benefit-research?nct="+encodeURIComponent(nctId),{
      cache:"no-store",signal:controller.signal
    }).then(async res=>{
      if(!res.ok)throw Error("Official ClinicalTrials.gov evidence is unavailable");
      const result=await res.json() as RegistryBenefitResearch;
      if(result.nctId!==nctId||result.benefitRank!==null||result.comparisonVerified!==false
        ||result.fdaDecisionVerified!==false)throw Error("Registry study identity/evidence gate failed");
      return result;
    }).then(result=>{if(!controller.signal.aborted)setData(result);})
      .catch(()=>{if(!controller.signal.aborted)setFailure("Independent registry evidence could not be retrieved. Do not infer benefit or zero events.");})
      .finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return ()=>controller.abort();
  },[nctId,attempt]);
  const clinical=[3,4,5,6].includes(assessment);
  const safety=assessment===8;
  const interventions=assessment===7;
  const showClinical=clinical&&data&&data.primary.length>0;
  function Outcomes({items}:{items:RegistryOutcome[]}){
    return <div className={css.registryOutcomes}>{items.slice(0,10).map((item,i)=><div key={i} className={css.registryOutcome}>
      <strong>{item.title}</strong>
      <p>Registry category: {item.type} · Follow-up: {item.timeFrame||"Not recorded"} · Unit: {item.unit||"Not recorded"}</p>
      {item.measurements.length?<ul>{item.measurements.slice(0,30).map((m,j)=>
        <li key={j}>{m.group}: {m.value}{m.spread?" · "+m.spread:""}</li>)}</ul>
        :<p>No numerical arm-level measurements extracted.</p>}
      <p>Registry statistical analysis posted: {item.analysisReported?"Yes — requires separate review":"Not recorded"}</p>
    </div>)}</div>;
  }
  return <details className={css.registry} aria-label={"Independent ClinicalTrials.gov source evidence "+nctId}>
    <summary>Official registry evidence · {loading?"checking…":failure?"unavailable":data?.resultsPosted?"posted results":"registration data"}</summary>
    <div className={css.registryBody}>
      <p><strong>NCT identity:</strong> {nctId} · Independent primary-source lookup occurs when you select a trial.</p>
      {loading&&<p role="status">Reading posted results from ClinicalTrials.gov…</p>}
      {failure&&<div role="alert"><p>{failure}</p><button type="button" onClick={()=>setAttempt(v=>v+1)}>Retry source check</button></div>}
      {data&&<>
        <p><a href={data.sourceUrl} target="_blank" rel="noopener noreferrer">Open exact ClinicalTrials.gov study</a> · Checked {data.retrievedAt.slice(0,10)} · Registry updated {data.sourceUpdated||"Not reported"}</p>
        <p><strong>Source state:</strong> {data.resultsPosted?"Results posted in registry":"Study record only — results not posted"} · Registered stage: {data.registeredPhases.join(", ")||"Not recorded"} · {data.registryStatus||"Status not recorded"}</p>
        {clinical&&<>
          <p><strong>Outcome-measure source for assessment #{assessment}:</strong> outcome values may assist research, but do not by themselves prove superiority, survival advantage, quality of life or comparative clinical benefit.</p>
          {showClinical?<Outcomes items={data.primary}/>:
            <p>No posted numerical primary outcomes are available in this response.</p>}
          {data.secondary.length>0&&<details><summary>Secondary/other registry outcomes ({data.secondary.length})</summary>
            <Outcomes items={data.secondary}/></details>}
        </>}
        {safety&&<>
          <p><strong>Serious adverse event source:</strong> registry event rates are descriptive, not an exposure-adjusted or independently verified safety advantage.</p>
          {data.seriousAdverseEvents.length?<ul>{data.seriousAdverseEvents.slice(0,30).map((event,i)=>
            <li key={i}><strong>{event.term}</strong> {event.groups.map(g=>g.group+": "+g.affected+"/"+g.atRisk).join(" · ")||"No reliable group denominators"}</li>)}</ul>:
            <p>Serious adverse-event table unavailable; this does not mean zero serious events.</p>}
        </>}
        {interventions&&<>
          <p><strong>Registered interventions:</strong> {data.interventions.join("; ")||"Not recorded"}. Route, convenience and standard-of-care comparison require separate documentation.</p>
        </>}
        {!clinical&&!safety&&!interventions&&<>
          <p>ClinicalTrials.gov does not independently establish this assessment's economic, market, regulatory or comparative conclusion. Relevant source collection and analyst review remain required.</p>
          <p>Registered conditions: {data.conditionNames.join("; ")||"Not recorded"} · Lead sponsor: {data.sponsor||"Not recorded"}</p>
        </>}
        <p className={css.registryWarning}>Source evidence only. No FDA decision, investment conclusion, clinically meaningful advantage or top-to-bottom ranking has been established by this automatic lookup.</p>
      </>}
    </div>
  </details>;
}
