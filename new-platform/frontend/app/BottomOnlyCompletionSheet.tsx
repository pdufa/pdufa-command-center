"use client";
import {useEffect,useMemo,useState} from "react";
import type {bottomOnlyReport,bottomOnlySummary} from "../lib/bottom-only-completion";
import css from "./TopOnlyCompletionSheet.module.css";
type Trial=ReturnType<typeof bottomOnlyReport>["trials"][number];
type Summary=ReturnType<typeof bottomOnlySummary>;
type Data=Omit<ReturnType<typeof bottomOnlyReport>,"trials"|"headers">&{rows:Summary[]};
type HistoryItem={eventId:string;recordedAt:string;eventType?:string;outcome?:string;readoutEvidenceUrl?:string;clinicalFullScore?:number|null;clinicalScoredFactors?:number;metricGrades?:{id:string;grade:number|null;sourceUrl?:string|null;observedResult?:string|null}[];note?:string;reason?:string;scoreVersion?:string;stage?:string;legacyScore?:number|null;legacyScoreKind?:string};
const show=(n:number|null)=>n===null?"Not scored":n.toFixed(1)+" / 100";
const readable=(s:string)=>s.replaceAll("_"," ");
/** Used inside the existing active roster. Membership is supplied by that page,
 * never inferred from a company or a historical FOCUS classification. */
export function BottomClinicalRating({nctId,score,graded}:{nctId:string;score:number|null;graded:number}){
 const [open,setOpen]=useState(false),[trial,setTrial]=useState<Trial|null>(null);
 const [events,setEvents]=useState<HistoryItem[]>([]),[error,setError]=useState("");
 useEffect(()=>{
  if(!open)return;
  const controller=new AbortController();
  fetch('/api/p3-post-data-research?nctId='+nctId,{signal:controller.signal})
   .then(async response=>{if(!response.ok)throw Error('Exact-NCT evidence unavailable');return response.json();})
   .then(data=>{setTrial(data.trial);setEvents(data.history??[]);setError('');})
   .catch(e=>{if(e.name!=='AbortError')setError(e.message);});
  return()=>controller.abort();
 },[open,nctId]);
 return <div data-clinical-nct={nctId}>
  <button type="button" aria-expanded={open} aria-controls={'clinical-'+nctId} onClick={()=>setOpen(!open)}>{show(score)} · {graded}/5 {open?'◂':'▸'}</button>
  {open&&<div id={'clinical-'+nctId} role="region" aria-label={'Clinical evidence and history for '+nctId} tabIndex={0} style={{width:960,maxWidth:'80vw',overflowX:'auto'}}>
   <p>Five clinical factors, 20% each. Research rating; missing grades remain unscored.</p>
   {error&&<p role="alert">{error}</p>}{!trial&&!error&&<p role="status">Loading evidence…</p>}
   {trial?.nctId===nctId&&<>
    <div style={{display:'flex',gap:16,width:1500}}>{trial.clinicalFactors.map(f=><article key={f.id} style={{width:280,flexShrink:0}}>
     <strong>{f.name}: {show(f.grade)}</strong><p>{readable(f.evidenceState)}</p>
     <p>{f.observedResult??f.blocker}</p><p>Benchmark: {f.benchmarkContext??f.requiredEvidence}</p>
     <p>Uncertainty: {f.uncertaintyReview??f.criticalRisk}</p><p>{f.criticalRiskReview}</p>
     {f.sourceUrl&&<a href={f.sourceUrl} target="_blank" rel="noopener noreferrer">Evidence</a>}
     {f.benchmarkSourceUrl&&<> · <a href={f.benchmarkSourceUrl} target="_blank" rel="noopener noreferrer">Benchmark</a></>}
    </article>)}</div>
    <p>Source-backed questions: {trial.sourceBackedQuestions}/30 ({trial.evidenceCompletenessPercent}%).</p>
    <details><summary>Exact-NCT score history ({events.length})</summary>{events.map(e=><article key={e.eventId}><strong>{e.recordedAt} · {e.eventType} · {e.stage} · {e.scoreVersion}</strong><p>{e.reason??e.note}</p>{e.clinicalScoredFactors!==undefined&&<p>{e.clinicalScoredFactors}/5 · {show(e.clinicalFullScore??null)}</p>}{e.legacyScoreKind&&<p>Archived {e.stage} history · {e.legacyScoreKind}: {show(e.legacyScore??null)}</p>}<details><summary>Saved factor grades and evidence</summary>{e.metricGrades?.map(g=><p key={g.id}>{g.id}: {show(g.grade)} · {g.observedResult}{g.sourceUrl&&<> · <a href={g.sourceUrl} target="_blank" rel="noopener noreferrer">Saved source</a></>}</p>)}</details></article>)}</details>
    <a href={'/api/p3-post-data-research?nctId='+nctId}>Complete research fields, provenance and audit</a>
   </>}
  </div>}
 </div>;
}
export default function BottomOnlyCompletionSheet({query}:{query:string}){
 const [data,setData]=useState<Data|null>(null),[error,setError]=useState("");
 const [selected,setSelected]=useState<string|null>(null),[detail,setDetail]=useState<Trial|null>(null);
 const [history,setHistory]=useState<HistoryItem[]>([]),[detailError,setDetailError]=useState("");
 const [sort,setSort]=useState("ticker"),[filter,setFilter]=useState("all"),[page,setPage]=useState(0);
 useEffect(()=>{const c=new AbortController();fetch("/api/p3-post-data-research",{signal:c.signal}).then(async r=>{if(!r.ok)throw Error("FOCUS evidence ledger unavailable");return r.json();}).then(d=>{if(!c.signal.aborted)setData(d);}).catch(e=>{if(e.name!=="AbortError")setError(e.message)});return()=>c.abort()},[]);
 useEffect(()=>{setDetail(null);setDetailError("");setHistory([]);if(!selected)return;const c=new AbortController();
  fetch("/api/p3-post-data-research?nctId="+selected,{signal:c.signal}).then(async r=>{if(!r.ok)throw Error("Exact FOCUS trial unavailable");return r.json();})
  .then(d=>{if(!c.signal.aborted){setDetail(d.trial);setHistory(Array.isArray(d.history)?d.history:[])}}).catch(e=>{if(e.name!=="AbortError")setDetailError(e.message)});
  return()=>c.abort()},[selected]);
 const rows=useMemo(()=>{const q=query.toLowerCase().trim();return (data?.rows??[])
   .filter(r=>[r.nctId,r.ticker,r.company,r.drug,r.indication,r.readoutOutcome].join(" ").toLowerCase().includes(q))
   .filter(r=>filter==="all"||filter==="scored"&&r.clinicalFullScore!==null||filter==="missing"&&r.sourceGaps>0)
   .sort((a,b)=>sort==="score"?(b.clinicalFullScore??-1)-(a.clinicalFullScore??-1):
    sort==="evidence"?b.evidenceCompletenessPercent-a.evidenceCompletenessPercent:
    sort==="nct"?a.nctId.localeCompare(b.nctId):a.ticker.localeCompare(b.ticker)||a.nctId.localeCompare(b.nctId));},[data,query,filter,sort]);
 const current=Math.min(page,Math.max(0,Math.ceil(rows.length/25)-1));
 return <section className={css.root} aria-label="FOCUS-only post-readout research and scores" data-bottom-only="true">
  <h2>FOCUS · Phase 3 post-data</h2>
  <p>The preserved FOCUS research cohort has publicly posted or issuer-reported Phase 3 findings. Active eligibility is maintained separately by the canonical Sheets roster. A reported primary endpoint is not an FDA approval, and a qualitative source fact is not a numerical grade.</p>
  {error&&<p role="alert">{error}</p>}{!data&&!error&&<p role="status">Loading FOCUS-only research…</p>}
  {data&&<><p><strong>{data.trialCount} preserved FOCUS research trials · {data.allFieldsAccounted}/{data.trialCount} with all 190 fields accounted for · {data.allMetricsEvaluated}/{data.trialCount} with 30 metric dispositions</strong></p>
   <p><strong>{data.completeClinicalOverallScores} complete five-factor research scores</strong> · {data.activeFactorsScored}/{data.activeFactorCount} individual factor grades · {data.completeThirtyMetricOverallScores} complete historical 30-metric scores · {data.sourceBackedQuestionCount}/{data.totalQuestionCount} question evidence slots accounted by sources. Every unavailable fact stays marked as missing or pending.</p>
   <div className={css.controls}><label>Sort <select value={sort} onChange={e=>setSort(e.target.value)}><option value="ticker">Ticker</option><option value="nct">NCT ID</option><option value="score">Completed clinical score</option><option value="evidence">Question evidence coverage</option></select></label>
    <label>Filter <select value={filter} onChange={e=>{setFilter(e.target.value);setPage(0)}}><option value="all">All FOCUS trials</option><option value="scored">Complete five-factor scores</option><option value="missing">Source gaps</option></select></label>
    <a href="/api/p3-post-data-research?format=csv">FOCUS 190-column CSV</a>
    <a href="/api/p3-post-data-research?format=metrics">FOCUS ratings CSV</a>
    <a href="/api/p3-post-data-research?format=facts">Reviewed evidence CSV</a>
    <a href="/api/p3-post-data-research?format=rating-evidence">Clinical rating evidence packets CSV</a></div>
   <p>Click a score caret to open the evidence ingredients horizontally to the right. Swipe horizontally on iPhone to read the expanded panel.</p>
   <div className={css.scroll} role="region" tabIndex={0} aria-label="FOCUS post-readout trial scores with horizontal evidence expansion">
    <div className={css.header}><span>TRIAL</span><span>READOUT</span><span>190 FIELDS</span><span>CLINICAL 5-FACTOR</span><span>ORIGINAL 30-METRIC</span><span>EVIDENCE</span><span>EXPANDED FINDINGS AND HISTORY</span></div>
    {rows.slice(current*25,current*25+25).map(t=>{const open=selected===t.nctId;return <div key={t.nctId} className={css.row} data-bottom-nct={t.nctId} data-expanded={open}>
     <div><a href={"https://clinicaltrials.gov/study/"+t.nctId} target="_blank" rel="noopener noreferrer"><strong>{t.ticker} · {t.nctId}</strong></a><p>{t.drug}</p><small>{t.indication}</small></div>
     <div>{readable(t.readoutOutcome)}<small>{t.readoutSourceDate??"Readout date not established"}</small></div>
     <div>{t.fieldsAccounted}/190<small>{t.metricsEvaluated}/30 dispositions</small></div>
     <div><button type="button" className={css.rating} aria-expanded={open} aria-controls={"bottom-detail-"+t.nctId} onClick={()=>setSelected(open?null:t.nctId)}>{show(t.clinicalFullScore)} {open?"◂":"▸"}</button><small>{t.clinicalScoredFactors}/5 factors graded</small></div>
     <div>{show(t.legacyThirtyMetricFullScore)}<small>Archived 30-metric formula</small></div>
     <div>{t.evidenceCompletenessPercent}%<small>{t.sourceGaps} question gaps</small></div>
     <div className={css.detail} id={"bottom-detail-"+t.nctId} hidden={!open}>
      {open&&!detail&&!detailError&&<p role="status">Loading exact-NCT findings…</p>}{open&&detailError&&<p role="alert">{detailError}</p>}
      {open&&detail?.nctId===t.nctId&&<><h3>{detail.nctId} · post-data clinical ratings</h3>
       <p><strong>Observed readout:</strong> {readable(detail.readoutOutcome)}. This is historical clinical evidence, not a retrospective prediction. <strong>Five-factor score:</strong> {show(detail.clinicalFullScore)}. Missing factor grades are never scored as zero or assigned a partial mean.</p>
       {detail.readoutEvidenceUrl&&<p><a href={detail.readoutEvidenceUrl} target="_blank" rel="noopener noreferrer">Open original observed Phase 3 readout</a></p>}
       {detail.endpointRationale&&<p><strong>Endpoint evidence:</strong> {detail.endpointRationale}</p>}
       <div className={css.rail}>{detail.clinicalFactors.map(f=><article key={f.id}><strong>{f.name}</strong><p>{show(f.grade)}</p><small>Weight 20% · {readable(f.evidenceState)}</small>
        <p><strong>Observed:</strong> {f.observedResult??"Rubric-ready assessment not completed"}</p><p><strong>Benchmark:</strong> {f.benchmarkContext??f.requiredEvidence}</p>
        <p><strong>Uncertainty:</strong> {f.uncertaintyReview??f.criticalRisk}</p><p>{f.criticalRiskReview}</p>
        <p><strong>Evidence to assess:</strong> {f.reviewEvidenceCount} exact-trial source observations · {readable(f.ratingReadiness)}</p>
        <details><summary>Expand source evidence for this factor ({f.reviewEvidenceCount})</summary>{f.reviewEvidence.map((x,i)=><article key={x.question+"-"+i}><strong>Q{x.question} · {readable(x.classification)}</strong><p>{x.evidence}</p><small>{x.criticalLimit}</small><p><a href={x.sourceUrl} target="_blank" rel="noopener noreferrer">Open source ({x.sourceDate??"date not established"})</a></p></article>)}</details>
        {f.sourceUrl&&<p><a href={f.sourceUrl} target="_blank" rel="noopener noreferrer">Reviewed evidence</a></p>}
        {f.benchmarkSourceUrl&&<p><a href={f.benchmarkSourceUrl} target="_blank" rel="noopener noreferrer">Comparison benchmark</a></p>}
       </article>)}</div>
       <details><summary>All 30 metric dispositions ({detail.metrics.length})</summary>{detail.metrics.map(m=><article key={m.id}><h4>{m.id}: {m.name}</h4><p>{show(m.score)} · {readable(m.state)} · active clinical weight {m.activeClinicalWeightPercent}%</p>
        <p>{m.definition}</p><p>{m.observedResult??m.blocker}</p>{m.sourceUrl&&<a href={m.sourceUrl} target="_blank" rel="noopener noreferrer">Research source</a>}</article>)}</details>
       <details><summary>All 190 data fields, missing-status labels and provenance</summary><div className={css.fields}>{detail.fields.map(f=><article key={f.column}><strong>{f.column}. {f.name} · {readable(f.state)}</strong><p>{f.value??f.exportValue}</p><small>{f.note}</small>{f.sourceUrl&&<p><a href={f.sourceUrl} target="_blank" rel="noopener noreferrer">Source or saved classification provenance</a></p>}</article>)}</div></details>
       <details><summary>30 question evidence statuses</summary>{detail.questions.map(q=><article key={q.number}><strong>Q{q.number} · {readable(q.state)}</strong><p>{q.explanation||"No source-review finding yet."}</p>{q.criticalLimit&&<p>Limitation: {q.criticalLimit}</p>}{q.sourceUrl&&<a href={q.sourceUrl} target="_blank" rel="noopener noreferrer">Source</a>}</article>)}</details>
       <details><summary>Additional reviewed readout, safety and follow-up evidence ({detail.additionalReviewedFacts.length})</summary>{detail.additionalReviewedFacts.map((f,i)=><article key={i}><strong>Q{f.question}: {readable(f.classification)}</strong><p>{f.evidence}</p><p>{f.criticalLimit}</p><a href={f.sourceUrl} target="_blank" rel="noopener noreferrer">Evidence ({f.sourceDate})</a></article>)}</details>
       <details><summary>History · original FOCUS snapshots ({history.length})</summary>{history.map(h=><article key={h.eventId}><strong>{h.recordedAt} · {h.eventType??"SNAPSHOT"}</strong><p>{h.outcome??""} · {h.note??""}</p>{h.clinicalScoredFactors!==undefined&&<p>{h.clinicalScoredFactors}/5 factors · {show(h.clinicalFullScore??null)}</p>}</article>)}</details>
       <details><summary>Exact remaining evidence and grading blockers ({detail.blockers.length})</summary><ul>{detail.blockers.map((b,i)=><li key={i}>{b}</li>)}</ul></details>
       <p><a href={detail.historyLinks.raas}>Preserved shared RAAS history</a> · <a href={"/api/p3-post-data-research?nctId="+detail.nctId}>Exact FOCUS JSON and saved audit trail</a></p>
      </>}
     </div>
    </div>})}
   </div><div className={css.controls}><button disabled={current===0} onClick={()=>setPage(current-1)}>Previous FOCUS page</button><span>{rows.length} matching FOCUS records</span><button disabled={(current+1)*25>=rows.length} onClick={()=>setPage(current+1)}>Next FOCUS page</button></div></>}
 </section>;
}
