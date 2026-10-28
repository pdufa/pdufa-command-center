"use client";
import {useEffect,useState} from "react";
import {validatePeakResearchView,type PeakResearchView} from "../lib/peak-research-view";
export default function PeakResearchPanel(){
 const [open,setOpen]=useState(false),[report,setReport]=useState<PeakResearchView|null>(null),[error,setError]=useState("");
 useEffect(()=>{
  if(!open)return;
  const controller=new AbortController();setReport(null);setError("");
  fetch("/api/phase3-research/peak-register",{cache:"no-store",signal:AbortSignal.any([controller.signal,AbortSignal.timeout(50000)])})
   .then(async response=>{if(!response.ok)throw new Error("unavailable");return validatePeakResearchView(await response.json());})
   .then(data=>{if(!controller.signal.aborted)setReport(data);})
   .catch(()=>{if(!controller.signal.aborted)setError("Current PEAK research could not be verified. Counts and conclusions are withheld.");});
  return()=>controller.abort();
 },[open]);
 const r=report?.researchRegister;
 const source=(id:string)=>r?.sources.find(s=>s.id===id);
 return <section className="panel" aria-label="PEAK scientific research and OUTCOME readiness">
  <h3>PEAK · current scientific research</h3>
  <p>NCT05208047 · Bezuclastinib plus sunitinib · GIST after imatinib. Source research remains separate from independent certification.</p>
  <details onToggle={event=>setOpen(event.currentTarget.open)}><summary>Evidence register, timeline and decision readiness</summary>
   {error?<p role="alert">{error}</p>:!report?<p role="status">Reading the authenticated research register…</p>:<>
    <p>As of {report.asOf} · Independently certified: <strong>{report.science40.independentlyReviewedAssessments}/40</strong> · Curated source leads: {report.science40.sourceLeadsDiscovered}.</p>
    <p>Research readiness: <strong>{report.science40.readinessGrade}</strong>. Decision readiness: <strong>{report.outcome.decisionReadinessGrade}</strong>. FDA probability and confidence: unavailable; prediction model not validated.</p>
    <p>Independently reviewed investigation-depth levels: {report.science40.reviewedDepthLevels.length}/20.</p>
    {r?<>
     <p>{r.summary.questionRecords} question records; {r.summary.questionsWithSourceObservations} have unadjudicated source observations. Missing required document families: {r.summary.missingRequiredDocumentFamilies}. Independently adjudicated historical cycles: {r.summary.independentlyAdjudicatedHistoricalCycles}.</p>
     <details><summary>Phase 3 to PDUFA timeline · source basis</summary><ol>{r.timeline.map((t,i)=><li key={i}>{t.date} · {t.event} · {t.basis.replaceAll("_"," ")}</li>)}</ol><p>The November 30 target and Priority Review are sponsor reported; an original FDA assignment letter has not been examined.</p></details>
     <details><summary>All 40 questions across eight domains</summary>{r.questions.map(q=><details key={q.id}><summary>{q.id} · {q.layerName} · {q.question}</summary><p>{q.researchObservation}</p><p>Research status: {q.reviewStatus.replaceAll("_"," ")}; independent review pending. No investigation-depth level is certified.</p><ul>{q.uncertainties.map((x,i)=><li key={i}>{x}</li>)}</ul>{q.sourceIds.map(id=>{const s=source(id);return s?<p key={id}><a href={s.url} target="_blank" rel="noopener noreferrer">{id}</a> · Published {s.publishedAt||"date unknown"} · Observed {s.observedOn} · {s.accessStatus.replaceAll("_"," ")}. Original document bytes/hash unavailable.</p>:null;})}</details>)}</details>
     <details><summary>Required documents and critical concerns</summary><ul>{r.requiredDocuments.map(d=><li key={d.id}>{d.name} · {d.status}</li>)}</ul><ul>{r.criticalConcerns.map((x,i)=><li key={i}>{x}</li>)}</ul></details>
     <details><summary>Apparent discrepancies and source explanations</summary>{r.evidenceDiscrepancies.map(d=><article key={d.id}><p>{d.observation}</p><small>{d.status.replaceAll("_"," ")}</small></article>)}</details>
     <details><summary>Selected historical approval and nonapproval context</summary><p>Selected examples are excluded from training and validation. Review cycles remain unresolved.</p>{r.historicalContexts.map(h=><article key={h.id}><h4>{h.drug} · {h.applicationId}</h4><p>{h.actionClaim.replaceAll("_"," ")} · Review cycle: not adjudicated. Model eligible: no.</p><ul>{h.differences.map((x,i)=><li key={i}>{x}</li>)}</ul>{h.sourceIds.map(id=>{const s=source(id);return s?<p key={id}><a href={s.url} target="_blank" rel="noopener noreferrer">{id}</a></p>:null;})}</article>)}</details>
    </>:<p>This research register is unavailable at the selected cutoff.</p>}
    <p>No list membership, FS/FA preset, scanner schedule, spreadsheet or trading permission is changed by this view.</p>
   </>}
  </details>
 </section>;
}
