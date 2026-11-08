"use client";
import {useEffect,useMemo,useState} from "react";
import type {phaseFirstReport,PhaseFirstScope} from "../../lib/phase-first-report";
import {trialLifecycle,type TrialLifecycle} from "../../lib/pdufa-selected-restrictions";
import css from "./phase-first.module.css";
type Report=ReturnType<typeof phaseFirstReport>;
type Trial=Report["trials"][number];
const cols={gridTemplateColumns:"200px 170px 195px minmax(460px,1fr)",minWidth:1040} as const;

export default function PhaseFirstTable(){
 const [scope,setScope]=useState<PhaseFirstScope>("census");
 const [data,setData]=useState<Report|null>(null),[error,setError]=useState("");
 const [lifecycle,setLifecycle]=useState<TrialLifecycle|"ALL">("ACTIVE");
 const [detail,setDetail]=useState<Trial|null>(null),[detailError,setDetailError]=useState("");
 const [search,setSearch]=useState(""),[phase,setPhase]=useState("ALL"),
       [page,setPage]=useState(0),[expanded,setExpanded]=useState<string|null>(null);

 useEffect(()=>{
  const c=new AbortController();setData(null);setError("");
  fetch("/api/phase-first?scope="+scope,{signal:c.signal,cache:"no-store"})
   .then(async r=>{if(!r.ok)throw Error("Phase-first evidence unavailable");return r.json();})
   .then(r=>{if(!c.signal.aborted)setData(r);})
   .catch(e=>{if(e.name!=="AbortError")setError(e.message);});
  return ()=>c.abort();
 },[scope]);
 useEffect(()=>{
  setDetail(null);setDetailError("");
  if(!expanded)return;
  const c=new AbortController();
  fetch("/api/phase-first?scope="+scope+"&trialId="+encodeURIComponent(expanded),
      {signal:c.signal,cache:"no-store"})
   .then(async r=>{if(!r.ok)throw Error("Exact-trial evidence unavailable");return r.json();})
   .then(r=>{if(!c.signal.aborted)setDetail(r.trials[0]);})
   .catch(e=>{if(e.name!=="AbortError")setDetailError(e.message);});
  return ()=>c.abort();
 },[expanded,scope]);
 const filtered=useMemo(()=>data?.trials.filter(t=>
   (lifecycle==="ALL"||trialLifecycle(t.status)===lifecycle)&&
   (phase==="ALL"||t.phase.label===phase)&&
   [t.trialId,t.drug,t.indication,t.sponsor,t.protocol].join(" ").toLowerCase()
      .includes(search.toLowerCase()))??[],[data,phase,search,lifecycle]);
 const lifecycleCounts={ACTIVE:0,HISTORICAL:0,VERIFY:0};
 for(const t of data?.trials??[])lifecycleCounts[trialLifecycle(t.status)]++;
 const rows=filtered.slice(page*20,page*20+20);
 return <section>
  <div className={css.controls}>
   <label>Research universe
    <select value={scope} onChange={e=>{setScope(e.target.value as PhaseFirstScope);setPage(0);setPhase("ALL");setSearch("");setExpanded(null);}}>
     <option value="sinovac">Sinovac · 27 registry trials</option>
     <option value="axsome">Axsome · 28 registry trials</option>
     <option value="alkermes">Alkermes · all identified phases</option>
     <option value="census">Existing 762-trial research census</option>
    </select>
   </label>
   <label>Study status
    <select value={lifecycle} onChange={e=>{setLifecycle(e.target.value as TrialLifecycle|"ALL");setPage(0);setExpanded(null);}}>
     <option value="ACTIVE">Active studies ({lifecycleCounts.ACTIVE})</option>
     <option value="HISTORICAL">Completed / withdrawn ({lifecycleCounts.HISTORICAL})</option>
     <option value="VERIFY">Unverified / suspended ({lifecycleCounts.VERIFY})</option>
     <option value="ALL">All studies ({data?.trialCount??0})</option>
    </select>
   </label>
   <label>Phase
    <select value={phase} onChange={e=>{setPhase(e.target.value);setPage(0);}}>
     <option value="ALL">All verified phases</option>
     {Object.keys(data?.byPhase??{}).map(p=><option key={p}>{p}</option>)}
    </select>
   </label>
   <label>Find trial
    <input value={search} onChange={e=>{setSearch(e.target.value);setPage(0);}}
      placeholder="Identifier, drug, indication or sponsor"/>
   </label>
   <a href={"/api/phase-first?scope="+scope+"&format=csv"}>Download source-evidence CSV</a>
  </div>
  {error&&<p role="alert">{error}</p>}
  {!data&&!error&&<p role="status">Loading phase and source evidence…</p>}
  {data&&<>
   <div className={css.stats}>
    <p><strong>{data.trialCount}</strong> distinct registry trials</p>
    <p><strong>{data.evidenceCounts.AVAILABLE??0}</strong> source items available</p>
    <p><strong>{data.evidenceCounts.MISSING??0}</strong> missing expected sources</p>
    <p><strong>{data.evidenceCounts.CONFLICTING??0}</strong> source conflicts</p>
   </div>
   <p>{data.sourceScope} Registry association does not prove current ownership, FDA filing acceptance, eligibility or predicted approval.</p>
   {data.companyResearch?.eligibilityNote&&<p role="note">{data.companyResearch.eligibilityNote} {data.companyResearch.eligibilitySourceUrl&&<a href={data.companyResearch.eligibilitySourceUrl} target="_blank" rel="noopener noreferrer">Original eligibility evidence</a>}</p>}
   <p><strong>Phase-aware requirements only.</strong> This census reports original-source evidence, missing, pending and not-yet-expected facts. Source coverage is not a medical effectiveness score or independent FDA prediction.</p>
   {data.companyResearch&&<details><summary>Company evidence and unresolved issues</summary>
    <p>{data.companyResearch.documentsReviewed} source documents reviewed; {data.companyResearch.factsRecorded} linked facts.</p>
    <ul>{data.companyResearch.blockers.map((b,i)=><li key={i}>{"nctId" in b?b.nctId+": ":""}{b.issue}</li>)}</ul>
   </details>}
   {scope==="alkermes"&&<details><summary>Current manufacturer programs and registry scope</summary>
    <ul>{data.currentAlkermesPrograms.map(p=><li key={p.id}><strong>{p.name}</strong> — {p.phase}. <a href={p.sourceUrl} target="_blank" rel="noopener noreferrer">Manufacturer source ({p.sourceDate})</a></li>)}</ul>
    <p>Manufacturer program phases are not proof of individual registry trial phases.</p>
   </details>}
   <p className={css.scrollHint}>Select a trial to expand its source evidence horizontally. On a phone, swipe the table.</p>
   <div className={css.scroll} role="region" aria-label="Phase-first independent registry evidence" tabIndex={0}>
    <div className={css.header} style={cols}>
     <span>TRIAL</span><span>VERIFIED PHASE</span><span>SOURCE COVERAGE</span><span>EXPAND SOURCE EVIDENCE</span>
    </div>
    {rows.map(base=>{
     const open=expanded===base.trialId;
     const t=open&&detail?.trialId===base.trialId?detail:base;
     return <div className={css.row} style={cols} key={t.trialId} data-expanded={open}>
      <div><a href={t.sourceUrl} target="_blank" rel="noopener noreferrer"><strong>{t.trialId}</strong></a>
       <p>{t.drug}</p><small>{t.indication}<br/>{t.sponsor}<br/>{t.status.replaceAll("_"," ")}<br/>Snapshot {t.sourceDate}</small>
      </div>
      <div><strong>{t.phase.label}</strong><p>{t.phase.verified?"Registry verified":"No phase inferred"}</p>
       <small>Trial start {t.start?.date??"Not documented"}<br/>Phase entry {t.phaseEntryDate??"Not documented"}</small>
      </div>
      <div><strong>{t.evidenceCounts.AVAILABLE??0} available</strong>
       <p>{t.evidenceCounts.MISSING??0} missing · {t.evidenceCounts.CONFLICTING??0} conflicting</p>
       <small>{t.evidenceCounts.PENDING??0} pending · {t.evidenceCounts["NOT YET EXPECTED"]??0} not yet expected</small>
      </div>
      <div>
       <button className={css.rating} aria-expanded={open}
        aria-controls={"source-details-"+t.trialId}
        onClick={()=>setExpanded(open?null:t.trialId)}>
         {open?"Hide":"Expand"} original-source checklist {open?"◂":"▸"}
       </button>
       <div id={"source-details-"+t.trialId} hidden={!open} className={css.details}>
        {open&&!detail&&!detailError&&<p role="status">Loading complete original-source checklist…</p>}
        {open&&detailError&&<p role="alert">{detailError}</p>}
        {open&&detail?.trialId===t.trialId&&<>
         <h2>{t.trialId} · phase-aware source evidence</h2>
         <p>Source availability and unresolved issues are documentary research observations, not independent clinical scores.</p>
         <h3>Missing expected evidence / conflicts</h3>
         {t.missingExpected.length?<ul>{t.missingExpected.map(e=><li key={e.id}>{e.label} · {e.status}: {e.evidence}</li>)}</ul>:<p>No missing expected items in this dated source set.</p>}
         <h3>Pending and not yet expected</h3>
         <ul>{[...t.pending,...t.notYetExpected].map(e=><li key={e.id}>{e.label} · {e.status}: {e.evidence}</li>)}</ul>
         <details><summary>Original-source checklist ({t.evidence.length})</summary>
          {t.evidence.map(e=><p key={e.id}><strong>{e.label} · {e.status}</strong>
           <span style={{display:"block"}}>{e.evidence}</span>
           <small>Evidence date {e.evidenceDate??"not documented"} · reviewed {e.reviewedAt} · {e.searchScope}</small>
           <a href={e.sourceUrl??e.searchedSourceUrl} target="_blank" rel="noopener noreferrer">Inspect original source</a>
          </p>)}
         </details>
         {t.pipeline.companyRestriction&&<p>{t.pipeline.companyRestriction}</p>}
        </>}
       </div>
      </div>
     </div>;
    })}
   </div>
   <div className={css.controls}>
    <button disabled={page===0} onClick={()=>setPage(p=>p-1)}>Previous</button>
    <span>{filtered.length?Math.min(page*20+1,filtered.length):0}–{Math.min((page+1)*20,filtered.length)} of {filtered.length}</span>
    <button disabled={(page+1)*20>=filtered.length} onClick={()=>setPage(p=>p+1)}>Next</button>
   </div>
  </>}
 </section>;
}
