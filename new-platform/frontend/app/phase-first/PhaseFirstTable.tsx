"use client";
import {useEffect,useMemo,useState} from "react";
import type {phaseFirstReport,PhaseFirstScope} from "../../lib/phase-first-report";
import css from "./phase-first.module.css";
import {trialLifecycle,type TrialLifecycle} from "../../lib/pdufa-selected-restrictions";
type Report=ReturnType<typeof phaseFirstReport>;
export default function PhaseFirstTable(){
 const [scope,setScope]=useState<PhaseFirstScope>("census"),[data,setData]=useState<Report|null>(null),[error,setError]=useState("");
 const [lifecycle,setLifecycle]=useState<TrialLifecycle|"ALL">("ACTIVE");
 const [detail,setDetail]=useState<Report["trials"][number]|null>(null),[detailError,setDetailError]=useState("");
 const [search,setSearch]=useState(""),[phase,setPhase]=useState("ALL"),[page,setPage]=useState(0),[expanded,setExpanded]=useState<string|null>(null);
 useEffect(()=>{const c=new AbortController();setData(null);setError("");fetch('/api/phase-first?scope='+scope,{signal:c.signal}).then(async r=>{if(!r.ok)throw Error("Phase-first source data unavailable");return r.json();}).then(r=>{if(!c.signal.aborted)setData(r);}).catch(e=>{if(e.name!=="AbortError")setError(e.message);});return ()=>c.abort();},[scope]);
 useEffect(()=>{setDetail(null);setDetailError("");if(!expanded)return;const c=new AbortController();fetch('/api/phase-first?scope='+scope+'&trialId='+encodeURIComponent(expanded),{signal:c.signal}).then(async r=>{if(!r.ok)throw Error('Trial evidence unavailable');return r.json();}).then(r=>{if(!c.signal.aborted)setDetail(r.trials[0]);}).catch(e=>{if(e.name!=="AbortError")setDetailError(e.message);});return ()=>c.abort();},[expanded,scope]);
 const filtered=useMemo(()=>data?.trials.filter(t=>(lifecycle==="ALL"||trialLifecycle(t.status)===lifecycle)&&(phase==="ALL"||t.phase.label===phase)&&[t.trialId,t.drug,t.indication,t.sponsor,t.protocol].join(' ').toLowerCase().includes(search.toLowerCase()))??[],[data,phase,search,lifecycle]);
 const lifecycleCounts={ACTIVE:0,HISTORICAL:0,VERIFY:0};
 for(const t of data?.trials??[])lifecycleCounts[trialLifecycle(t.status)]++;
 const rows=filtered.slice(page*20,page*20+20);
 return <section>
  <div className={css.controls}>
   <label>Research universe <select value={scope} onChange={e=>{setScope(e.target.value as typeof scope);setPage(0);setPhase("ALL");setSearch("");setExpanded(null);}}><option value="sinovac">Sinovac · 27 census trials</option><option value="axsome">Axsome · 28 census trials</option><option value="alkermes">Alkermes · all identified phases</option><option value="census">Existing 762-trial research census</option></select></label>
   <label>Study status <select value={lifecycle} onChange={e=>{setLifecycle(e.target.value as TrialLifecycle|"ALL");setPage(0);setExpanded(null);}}><option value="ACTIVE">Active studies ({lifecycleCounts.ACTIVE})</option><option value="HISTORICAL">Completed / terminated / withdrawn ({lifecycleCounts.HISTORICAL})</option><option value="VERIFY">Unverified / suspended ({lifecycleCounts.VERIFY})</option><option value="ALL">All studies ({data?.trialCount??0})</option></select></label>
   <label>Phase <select value={phase} onChange={e=>{setPhase(e.target.value);setPage(0);}}><option value="ALL">All verified phases</option>{Object.keys(data?.byPhase??{}).map(p=><option key={p}>{p}</option>)}</select></label>
   <label>Find trial <input value={search} onChange={e=>{setSearch(e.target.value);setPage(0);}} placeholder="Identifier, drug, indication or sponsor"/></label>
   <a href={'/api/phase-first?scope='+scope+'&format=csv'}>Download source evidence CSV</a>
  </div>
  {error&&<p role="alert">{error}</p>}{!data&&!error&&<p role="status">Loading source-verified phases…</p>}
  {data&&<>
   <div className={css.stats}>
    <p><strong>{data.trialCount}</strong> distinct trials</p><p>Phase-appropriate source evidence</p>
   </div>
   <p>{data.sourceScope} Registry association does not establish current ownership. Phase-entry dates are shown only when documented; study start is kept separate.</p>
   {data.companyResearch?.eligibilityNote&&<p role="note"><strong>{data.companyResearch.eligibilityNote}</strong> {data.companyResearch.eligibilitySourceUrl&&<a href={data.companyResearch.eligibilitySourceUrl} target="_blank" rel="noopener noreferrer">Original eligibility evidence</a>}</p>}
   <p><strong>Evidence classifications:</strong> {Object.entries(data.evidenceCounts).map(([s,n])=>s+': '+n).join(' · ')}.</p>
   <p><strong>Active Phase View is a filter, not a deletion.</strong> Original trial research remains preserved; retired ratings are isolated in the read-only historical archive. Completed studies with ongoing FDA applications belong in separate PDUFA monitoring. <a href="/restrictions">View 23 selected restrictions and audit counts</a>.</p>
   <p><strong>Coverage is not efficacy.</strong> Pending results and later-stage requirements are excluded from evidence completeness. Documentation coverage does not measure efficacy or approval likelihood; missing data remain missing.</p>
   {data.companyResearch&&<details><summary>Company research coverage and unresolved issues</summary><p>{data.companyResearch.documentsReviewed} source documents reviewed; {data.companyResearch.factsRecorded} linked facts. These include supporting facts already known elsewhere; they are not all newly recovered facts.</p><ul>{data.companyResearch.blockers.map((b,i)=><li key={i}>{"nctId" in b?b.nctId+": ":""}{b.issue}</li>)}</ul></details>}
   {scope==="alkermes"&&<details><summary>Current manufacturer programs and registry scope</summary><ul>{data.currentAlkermesPrograms.map(p=><li key={p.id}><strong>{p.name}</strong> — {p.phase}. <a href={p.sourceUrl} target="_blank" rel="noopener noreferrer">Manufacturer source ({p.sourceDate})</a></li>)}</ul><p>Individual-trial phases below remain independent of these program descriptions. Historical and collaborator studies remain labeled by their registered sponsor.</p></details>}
   <p className={css.scrollHint}>Select a trial to expand its source evidence to the right. On a phone, swipe the table horizontally.</p>
   <div className={css.scroll} role="region" aria-label="Phase-first trial source evidence; horizontal scrolling" tabIndex={0}>
    <div className={css.header}><span>TRIAL</span><span>PHASE</span><span>SOURCE DETAILS</span><span>DOCUMENTATION</span><span>REGULATORY STATUS</span><span>SOURCE CONFIDENCE</span><span>EXPANDED EVIDENCE</span></div>
    {rows.map(base=>{const open=expanded===base.trialId;const t=open&&detail?.trialId===base.trialId?detail:base;return <div className={css.row} data-expanded={open} key={t.trialId}>
     <div><a href={t.sourceUrl} target="_blank" rel="noopener noreferrer"><strong>{t.trialId}</strong></a><p>{t.drug}</p><small>{t.indication}<br/>{t.sponsor}<br/>{t.status.replaceAll('_',' ')}<br/>Source: {t.sourceDate}</small></div>
     <div><strong>{t.phase.label}</strong><p>{t.phase.verified?"Registry verified":"No phase inferred"}</p><small>Trial start: {t.start?.date??"Not documented"}<br/>Phase-entry date: {t.phaseEntryDate??"Not documented"}</small></div>
     <div><button className={css.rating} aria-expanded={open} aria-controls={'details-'+t.trialId} onClick={()=>setExpanded(open?null:t.trialId)}>{open?'Close evidence ◂':'Open evidence ▸'}</button></div>
     <div><strong>{t.evidenceCompleteness===null?'Not assessable':t.evidenceCompleteness+'%'}</strong><p>Source documentation completeness</p></div>
     <div><p>{t.fdaPrediction.status}</p></div>
     <div><strong>{t.evidenceConfidence}</strong><p>Source evidence confidence</p><small>Not an FDA prediction or approval probability.</small></div>
     <div id={'details-'+t.trialId} hidden={!open} className={css.details}>
      {open&&!detail&&!detailError&&<p role="status">Loading exact-trial source observations…</p>}{open&&detailError&&<p role="alert">{detailError}</p>}
      {open&&detail?.trialId===t.trialId&&<>
       <h2>{t.trialId} · clinical source evidence</h2><p>{t.fdaPrediction.reason}</p>
       <h3>Missing expected evidence / conflicts</h3>{t.missingExpected.length?<ul>{t.missingExpected.map(e=><li key={e.id}><strong>{e.label} · {e.status}</strong>: {e.evidence}</li>)}</ul>:<p>No missing expected evidence in this reviewed source set.</p>}
       <h3>Not yet expected</h3><ul>{t.notYetExpected.map(e=><li key={e.id}>{e.label}: {e.evidence}</li>)}</ul>
       <h3>Pending</h3><ul>{t.pending.map(e=><li key={e.id}>{e.label}: {e.evidence}</li>)}</ul>
       <details><summary>Complete phase-specific evidence checklist</summary>{t.evidence.map(e=><p key={e.id}><strong>{e.label} — {e.status}</strong><br/>{e.evidence}<br/><small>Confidence {e.confidence}; expected at {e.expectedAt}; date kind {e.dateKind}. {e.searchScope} Reviewed {e.reviewedAt}.</small>{!e.sourceUrl&&<a href={e.searchedSourceUrl} target="_blank" rel="noopener noreferrer">Reviewed registry source</a>}{e.sourceUrl&&<> <a href={e.sourceUrl} target="_blank" rel="noopener noreferrer">Source ({e.evidenceDate??'date not documented'})</a></>}</p>)}</details>

       <p><a href={'/api/phase-first/history?trialId='+t.trialId} target="_blank" rel="noopener noreferrer">Read-only historical observations</a></p>
       {t.pipeline.companyRestriction&&<p><strong>{t.pipeline.companyRestriction}</strong></p>}
       <p>{t.pipeline.restrictions}</p>
      </>}
     </div>
    </div>;})}
   </div>
   <div className={css.controls}><button disabled={page===0} onClick={()=>setPage(p=>p-1)}>Previous</button><span>{filtered.length?Math.min(page*20+1,filtered.length):0}–{Math.min((page+1)*20,filtered.length)} of {filtered.length}</span><button disabled={(page+1)*20>=filtered.length} onClick={()=>setPage(p=>p+1)}>Next</button></div>
   <p><a href="/focus">FOCUS candidates</a> · <a href="/predictions">Independent FDA application investigations</a></p>
  </>}
 </section>;
}
