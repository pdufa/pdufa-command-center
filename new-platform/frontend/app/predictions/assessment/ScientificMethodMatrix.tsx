"use client";
import {useEffect, useRef, useState} from "react";
import type {AssessmentReview, CatalogMatrix, Evidence, MethodReview, ReviewMatrix} from "../../../lib/medical-review-matrix";
import ScientificInstallationStatus from "./ScientificInstallationStatus";
import PhaseVerificationPanel from "./PhaseVerificationPanel";

const panel = {border: "1px solid #a8c9bc", borderRadius: 9, padding: 14, margin: "12px 0"} as const;
function SourceLinks({sources}: {sources: Evidence[]}) {
  return <ul>{sources.map((source, i) => {
    let url: URL;
    try {url = new URL(source.sourceUrl);} catch {return <li key={i}>Invalid source URL withheld</li>;}
    return <li key={i}>{url.protocol === "https:" && !url.username && !url.password ?
      <a href={url.href} target="_blank" rel="noopener noreferrer">{url.href}</a> : "Unsafe source URL withheld"}
      {source.stageDocumentSha256 ? <div style={{fontSize: 11, overflowWrap: "anywhere"}}>Captured stage SHA-256: {source.stageDocumentSha256}</div> : null}</li>;
  })}</ul>;
}
function MethodEvidence({method}: {method: MethodReview}) {
  return <div>
    <p>Status: <strong>{method.status}</strong> · Grade: {method.grade === null ? "Unscored" : method.grade + " / 5"}</p>
    <p>Source evidence attached to the review: {method.sourceEvidence.length ? method.sourceEvidence.length + " captured references" : "No captured review evidence"}</p>
    {method.rationale ? <p>{method.rationale}</p> : null}
    {method.reviewerId ? <p>Reviewer: {method.reviewerId} · Reviewed: {method.reviewedAt} · Revision: {method.revision}</p> : null}
    <SourceLinks sources={method.sourceEvidence} />
    <details style={panel}><summary>Evidence gaps · {method.evidenceGaps.length} recorded</summary>
      <p>Recorded gaps remain visible until independently adjudicated. An absent future-phase result is not a failed current-phase test.</p>
      {method.evidenceGaps.length ? <ul>{method.evidenceGaps.map((g, i) => <li key={i}><strong>{g.gap_code}</strong>: {g.evidence_note} ({g.recorded_at})</li>)}</ul> : <p>No gap event recorded. This does not establish complete evidence.</p>}
    </details>
    <details style={panel}><summary>Previous versus current reviews · {method.history.length} revisions</summary>
      <p>Earlier phases, retractions and superseded grades are history. They do not count toward the current grade.</p>
      {method.history.map((r, i) => <article key={r.review_event_id || i} style={panel}>
        <strong>{r.verified_phase} · revision {r.revision} · {r.disposition} · {r.grade === null ? "Unscored" : r.grade + " / 5"}</strong>
        <p>{r.rationale}</p><p>{r.reviewer_id} · {r.evidence_reviewed_at}</p><SourceLinks sources={r.evidence} />
      </article>)}
    </details>
  </div>;
}

export default function ScientificMethodMatrix({nct}: {nct: string}) {
  const [review, setReview] = useState<ReviewMatrix | null>(null);
  const [catalog, setCatalog] = useState<CatalogMatrix | null>(null);
  const [details, setDetails] = useState<Record<number, AssessmentReview>>({});
  const [errors, setErrors] = useState<Record<number, string>>({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const pending = useRef(new Set<number>());
  const firstAssessment = useRef<HTMLDetailsElement|null>(null);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => {
    const abort = new AbortController(); controller.current = abort;
    fetch("/api/predictions/medical-matrix?nct=" + encodeURIComponent(nct), {cache: "no-store", signal: abort.signal})
      .then(async response => {
        const data = await response.json();
        if (!response.ok) throw Error(data.error || "Scientific review ledger unavailable");
        setReview(data.review); setCatalog(data.catalog);
      }).catch(e => {if (!abort.signal.aborted) setError(e instanceof Error ? e.message : "Scientific review ledger unavailable");})
      .finally(() => {if (!abort.signal.aborted) setLoading(false);});
    return () => abort.abort();
  }, [nct]);
  async function loadAssessment(index: number) {
    if (details[index] || pending.current.has(index)) return;
    pending.current.add(index); setErrors(previous => ({...previous, [index]: ""}));
    try {
      const response = await fetch("/api/predictions/medical-matrix?nct=" + encodeURIComponent(nct) + "&assessmentIndex=" + index,
        {cache: "no-store", signal: controller.current?.signal});
      const data = await response.json();
      if (!response.ok || data.review?.phaseEventId !== review?.phaseEventId ||
          data.review?.historicalReviewEvents !== review?.historicalReviewEvents ||
          data.review?.recordedGapEvents !== review?.recordedGapEvents ||
          JSON.stringify(data.review?.assessments) !== JSON.stringify(review?.assessments))
        throw Error("Evidence changed or is unavailable. Reload the page before comparing reviews.");
      setDetails(previous => ({...previous, [index]: data.review.selectedAssessment}));
    } catch (e) {
      if (!controller.current?.signal.aborted) setErrors(previous => ({...previous, [index]: e instanceof Error ? e.message : "Method evidence unavailable"}));
    } finally {pending.current.delete(index);}
  }
  function openFirstMethods(){
    const row=firstAssessment.current;
    if(!row)return;
    row.open=true;
    row.scrollIntoView({behavior:"smooth",block:"start"});
  }
  return <section style={{...panel, background: "#f5faf7"}} aria-label={"Scientific method matrix for " + nct}>
    <h2>Scientific assessment matrix · {nct}</h2>
    <button type="button" onClick={openFirstMethods} disabled={!review||!catalog}
      style={{padding:"12px 14px",borderRadius:9,border:"1px solid #218169",background:"#dbf7e9",color:"#154c3f",fontWeight:800,marginBottom:8}}>
      Open Assessment 1 → 20 scientific methods
    </button>
    <ScientificInstallationStatus />
    <PhaseVerificationPanel nct={nct} />
    <p>8 subject layers · 40 assessments · 20 methods per assessment. Source collection and methodology slots do not count as independently graded scientific tests.</p>
    <details style={panel}><summary>Status, freshness and dependency definitions</summary>
      <p>Unreviewed means no recorded current-phase grade. Provisional means a partial assessment; complete means every applicable method has a recorded reviewer event. Independent source verification, reviewer authorization and clinical validation remain separate release requirements. Not applicable is an explicit reviewer exclusion. Stale phase means an earlier phase event requires fresh review. A grade is evidence strength, never an FDA probability.</p>
      <p>Sources retain their review dates and captured-stage receipts. This view has no automated expiry clearance; source freshness, amendments, contradictory evidence and unresolved dependencies require independent re-review. No recorded gap is not proof that evidence is complete.</p>
    </details>
    {loading ? <p role="status">Loading the isolated review ledger…</p> : null}
    {error ? <p role="alert">{error} No completion count or grade is inferred.</p> : null}
    {review && catalog ? <div>
      <p>Current verified phase: <strong>{review.verifiedPhase ?? "NOT VERIFIED"}</strong> · Registry-reported: {catalog.registry.reportedPhases.join(" / ") || "Unknown"} ({catalog.phaseBasis})</p>
      <p>Recorded current-phase method grades: <strong>{review.counts.SCORED} / 800</strong> · Explicit exclusions: {review.counts.NOT_APPLICABLE} · Remaining: {800 - review.counts.SCORED - review.counts.NOT_APPLICABLE}</p>
      <progress aria-label="Recorded current-phase method review positions" max={800} value={review.counts.SCORED + review.counts.NOT_APPLICABLE} />
      <p>Historical review events: {review.historicalReviewEvents} · Recorded gap events: {review.recordedGapEvents}</p>
      {review.gradingPolicy ? <details style={panel}><summary>Scientific grading rubric · {review.gradingPolicy.status}</summary>
        <p>{review.gradingPolicy.version} · {review.gradingPolicy.normalization.formula}</p>
        <ul>{review.gradingPolicy.anchors.map(anchor => <li key={anchor.grade}>{anchor.grade} / 5: {anchor.meaning}</li>)}</ul>
        <p>Historical events certified against this policy: {review.gradingPolicy.historicalEventsCertifiedAgainstPolicy ? "Yes" : "No"}. Clinical validation and authorized review remain separate requirements.</p>
      </details> : null}
      <p>APPROVAL: ABSTAIN · CRL: ABSTAIN · REVIEW_DELAY: ABSTAIN · CERTAINTY: NOT_VALIDATED</p>
      <details style={panel}><summary>Verified phase history · {review.phaseHistory.length} events</summary>
        <ul>{review.phaseHistory.map((p, i) => <li key={i}>{p.verified_phase} · {p.reviewer_id} · {p.verified_at}</li>)}</ul>
        <p>Previously completed phases require their own source verification and are not inferred from the current phase.</p>
      </details>
      {catalog.assessments.map((assessment, i) => {
        const row = review.assessments[i], detail = details[assessment.assessmentIndex];
        return <details key={assessment.assessmentIndex} ref={i===0?firstAssessment:undefined}
          id={i===0?"first-scientific-assessment":undefined}
          style={{...panel,scrollMarginTop:90}} onToggle={event => {if (event.currentTarget.open) void loadAssessment(assessment.assessmentIndex);}}> 
          <summary><strong>Layer {assessment.layerId} · {assessment.assessmentId} {assessment.label}</strong> · {row.status} · {row.reviewedMethods} scored / 20 · {row.scoreOutOf100 === null ? "Unscored" : row.scoreOutOf100 + " / 100 evidence strength"}</summary>
          <p>{assessment.objective}</p>
          <p>Priority: {assessment.methods[0]?.priorityTier} · {assessment.methods[0]?.phaseApplicability}. Investigation order is not an observed risk.</p>
          <p>{row.pendingMethods} pending · {row.excludedMethods} explicitly excluded</p>
          {errors[assessment.assessmentIndex] ? <p role="alert">{errors[assessment.assessmentIndex]} <button type="button" onClick={() => void loadAssessment(assessment.assessmentIndex)}>Retry evidence</button></p> : null}
          {!detail && !errors[assessment.assessmentIndex] ? <p role="status">Loading 20 method records…</p> : null}
          {assessment.methods.map(method => <details key={method.methodIndex} style={panel}>
            <summary>Method {method.methodIndex}: {method.method} · {detail?.methods?.[method.methodIndex - 1]?.status ?? "Evidence not loaded"} · Priority {method.priorityRank ?? "Verify phase"}</summary>
            <p>{method.methodDescription}</p><p>Required sources: {method.requiredSources}</p>
            {detail?.methods?.[method.methodIndex - 1] ? <MethodEvidence method={detail.methods[method.methodIndex - 1]} /> : <p>Method evidence not loaded. No score assigned.</p>}
          </details>)}
        </details>;
      })}
    </div> : null}
  </section>;
}
