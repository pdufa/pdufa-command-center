"use client";
import {useEffect, useRef, useState} from "react";
import type {AssessmentReview, CatalogMatrix, Evidence, MethodReview, ReviewMatrix} from "../../../lib/medical-review-matrix";
import ScientificInstallationStatus from "./ScientificInstallationStatus";
import PhaseVerificationPanel from "./PhaseVerificationPanel";
import PilotPredictionWorkup from "./PilotPredictionWorkup";
import LivePredictionMonitor from "./LivePredictionMonitor";
import {buildClinicalReviewRegisterCsv} from "../../../lib/medical-review-register";

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
  const [refreshing, setRefreshing] = useState(false);
  const [lastCheckedAt, setLastCheckedAt] = useState<string|null>(null);
  const [lastChange, setLastChange] = useState<string|null>(null);
  const refreshRef = useRef<(()=>void)|null>(null);
  const lastSnapshotRef = useRef<ReviewMatrix|null>(null);
  const [showAllScores, setShowAllScores] = useState(false);
  const [loadingAllScores, setLoadingAllScores] = useState(false);
  const [scoreLoadProgress, setScoreLoadProgress] = useState(0);
  const [exportError, setExportError] = useState("");
  const pending = useRef(new Set<number>());
  const firstAssessment = useRef<HTMLDetailsElement|null>(null);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => {
    setReview(null); setCatalog(null); setDetails({}); setErrors({}); setError(""); setLoading(true);
    setRefreshing(false); setLastCheckedAt(null); setLastChange(null); lastSnapshotRef.current=null;
    setShowAllScores(false); setLoadingAllScores(false); setScoreLoadProgress(0); setExportError(""); pending.current.clear();
    const abort = new AbortController(); controller.current = abort;
    let inFlight = false;
    let disposed = false;
    async function poll() {
      if (inFlight || disposed || abort.signal.aborted) return;
      inFlight = true;
      setRefreshing(true);
      try {
        const response = await fetch("/api/predictions/medical-matrix?nct=" + encodeURIComponent(nct),
          {cache:"no-store",signal:abort.signal});
        const data = await response.json();
        if (!response.ok) throw Error(data.error || "Isolated review ledger unavailable");
        // This endpoint performs authenticated, independent backend response checks.
        // It provides reviewer records, NOT an active prediction-job feed.
        const nextReview = data.review as ReviewMatrix;
        const nextCatalog = data.catalog as CatalogMatrix;
        if (!nextReview || nextReview.nct !== nct || nextReview.totalPositions !== 800 ||
            !nextCatalog || nextCatalog.nct !== nct || !Array.isArray(nextReview.assessments) ||
            nextReview.assessments.length !== 40 ||
            nextReview.counts.SCORED + nextReview.counts.NOT_APPLICABLE > 800)
          throw Error("Invalid current review snapshot");
        const prev = lastSnapshotRef.current;
        if (prev) {
          const changedPhase = prev.phaseEventId !== nextReview.phaseEventId;
          const delta = nextReview.counts.SCORED - prev.counts.SCORED;
          const exclusions = nextReview.counts.NOT_APPLICABLE - prev.counts.NOT_APPLICABLE;
          const reviewDelta = nextReview.historicalReviewEvents - prev.historicalReviewEvents;
          const gapDelta = nextReview.recordedGapEvents - prev.recordedGapEvents;
          if (changedPhase || reviewDelta || gapDelta || delta || exclusions) {
            const parts = [
              changedPhase ? "verified phase event changed" : "",
              delta ? (delta > 0 ? "+" : "") + delta + " graded methods" : "",
              exclusions ? (exclusions > 0 ? "+" : "") + exclusions + " exclusions" : "",
              gapDelta ? (gapDelta > 0 ? "+" : "") + gapDelta + " evidence gaps" : "",
              !delta && !exclusions && reviewDelta ? "review ledger updated" : ""
            ].filter(Boolean);
            setLastChange(parts.join(" · "));
            // Cached method details must not appear current after a real phase/review event.
            setDetails({}); setErrors({}); setShowAllScores(false); setScoreLoadProgress(0);
          }
        }
        lastSnapshotRef.current=nextReview;
        if (disposed || abort.signal.aborted) return;
        setReview(nextReview); setCatalog(nextCatalog); setError("");
        setLastCheckedAt(new Date().toISOString());
      } catch (e) {
        if (!disposed && !abort.signal.aborted)
          setError(e instanceof Error ? e.message : "Isolated review ledger unavailable");
      } finally {
        inFlight=false;
        if (!disposed && !abort.signal.aborted) {
          setLoading(false); setRefreshing(false);
        }
      }
    }
    refreshRef.current = () => {void poll();};
    void poll();
    // Poll only while open/visible; a returning tab refreshes immediately.
    // This avoids excess backend reads and does not invent background processing.
    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") void poll();
    }, 15000);
    const onVisibility=()=>{if (document.visibilityState==="visible") void poll();};
    document.addEventListener("visibilitychange",onVisibility);
    return () => {
      disposed=true; window.clearInterval(interval);
      document.removeEventListener("visibilitychange",onVisibility);
      refreshRef.current=null; abort.abort();
    };
  }, [nct]);
  async function loadAssessment(index: number) {
    if (details[index] || pending.current.has(index)) return;
    pending.current.add(index); setErrors(previous => ({...previous, [index]: ""}));
    try {
      const response = await fetch("/api/predictions/medical-matrix?nct=" + encodeURIComponent(nct) + "&assessmentIndex=" + index,
        {cache: "no-store", signal: controller.current?.signal});
      const data = await response.json();
      // Check against the most recently refreshed ledger, not an older render
      // captured before a poll. A phase/review change invalidates old method details.
      const current = lastSnapshotRef.current;
      if (!response.ok || !current ||
          data.review?.phaseEventId !== current.phaseEventId ||
          data.review?.historicalReviewEvents !== current.historicalReviewEvents ||
          data.review?.recordedGapEvents !== current.recordedGapEvents ||
          JSON.stringify(data.review?.assessments) !== JSON.stringify(current.assessments))
        throw Error("Evidence changed or is unavailable. Reload the method evidence before comparing reviews.");
      setDetails(previous => ({...previous, [index]: data.review.selectedAssessment}));
    } catch (e) {
      if (!controller.current?.signal.aborted) setErrors(previous => ({...previous, [index]: e instanceof Error ? e.message : "Method evidence unavailable"}));
    } finally {pending.current.delete(index);}
  }
  async function openAllScores() {
    if (showAllScores) {setShowAllScores(false); return;}
    setShowAllScores(true); setExportError("");
    if (loadingAllScores) return;
    setLoadingAllScores(true);
    try {
      // The read-only backend serves one assessment per request. Use bounded concurrency,
      // and never infer a grade from a catalog position or absent review record.
      for (let start = 1; start <= 40; start += 4) {
        await Promise.all(Array.from({length: Math.min(4, 41 - start)}, (_, offset) =>
          loadAssessment(start + offset)));
        if (controller.current?.signal.aborted) break;
        setScoreLoadProgress(Math.min(40, start + 3));
      }
    } finally {setLoadingAllScores(false);}
  }
  function exportClinicalRegister(){
    if (!review || !catalog || error || loadingAllScores) return;
    setExportError("");
    try {
      const csv=buildClinicalReviewRegisterCsv(catalog,review,details);
      const url=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));
      const anchor=document.createElement("a");
      anchor.href=url;
      anchor.download="MAIN-independent-method-review-"+nct+".csv";
      document.body.appendChild(anchor);anchor.click();anchor.remove();
      window.setTimeout(()=>URL.revokeObjectURL(url),1000);
    } catch(e) {
      setExportError(e instanceof Error?e.message:"Method register export could not be verified");
    }
  }
  function openFirstMethods(){
    const row=firstAssessment.current;
    if(!row)return;
    row.open=true;
    row.scrollIntoView({behavior:"smooth",block:"start"});
  }
  return <section style={{...panel, background: "#f5faf7"}} aria-label={"Scientific method matrix for " + nct}>
    <h2>Scientific assessment matrix · {nct}</h2>
    <LivePredictionMonitor nct={nct} review={review} loading={loading}
      refreshing={refreshing} unavailable={!!error} lastCheckedAt={lastCheckedAt}
      lastChange={lastChange} refresh={() => refreshRef.current?.()} />
    <PilotPredictionWorkup nct={nct} />
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
    {error ? <p role="alert">{error} Live source verification failed; cached results are withheld until a successful refresh.</p> : null}
    {review && catalog && !error ? <div id="live-scientific-review-ledger">
      <p>Current verified phase: <strong>{review.verifiedPhase ?? "NOT VERIFIED"}</strong> · Registry-reported: {catalog.registry.reportedPhases.join(" / ") || "Unknown"} ({catalog.phaseBasis})</p>
      <p>Recorded current-phase method grades: <strong>{review.counts.SCORED} / 800</strong> · Explicit exclusions: {review.counts.NOT_APPLICABLE} · Remaining: {800 - review.counts.SCORED - review.counts.NOT_APPLICABLE}</p>
      <progress aria-label="Recorded current-phase method review positions" max={800} value={review.counts.SCORED + review.counts.NOT_APPLICABLE} />
      <p>Historical review events: {review.historicalReviewEvents} · Recorded gap events: {review.recordedGapEvents}</p>
      <section style={{...panel, background: "#edf6f1"}} aria-label="All 800 scientific method score positions">
        <h3>All 800 individual scientific scores</h3>
        <p><strong>{review.counts.SCORED} / 800</strong> current-phase evidence-backed grades.
          Unreviewed, unverified, retracted and stale methods have no numeric grade; not-applicable methods are excluded.</p>
        <button type="button" onClick={() => void openAllScores()}
          style={{padding: "12px 14px", border: "1px solid #218169", background: "#dbf7e9",
            color: "#154c3f", borderRadius: 9, fontWeight: 800}}>
          {showAllScores ? "Hide complete score register" : "Open all 800 score positions"}
        </button>
        {showAllScores ? <div>
          <p role="status">{loadingAllScores
            ? "Loading method records: " + scoreLoadProgress + " / 40 assessments checked"
            : "Records loaded for " + Object.keys(details).length + " / 40 assessments. Blank values are not zero."}</p>
          {catalog.assessments.map(assessment => {
            const loaded = details[assessment.assessmentIndex];
            return <section key={assessment.assessmentIndex} style={{margin: "12px 0",
              border: "1px solid #a8c9bc", borderRadius: 9, padding: 10}}>
              <strong>Assessment {assessment.assessmentIndex}: {assessment.label}</strong>
              <div style={{display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(78px, 1fr))",
                gap: 5, marginTop: 8}}>
                {assessment.methods.map(method => {
                  const record = loaded?.methods?.[method.methodIndex - 1];
                  const score = !record ? "…" : record.grade !== null ? record.grade + "/5" :
                    record.status === "NOT_APPLICABLE" ? "N/A" :
                    record.status === "VERIFY_PHASE" ? "VERIFY" :
                    record.status === "STALE_PHASE" ? "STALE" :
                    record.status === "RETRACTED" ? "RETRACT" : "N/R";
                  return <a key={method.methodIndex}
                    href={"#scientific-method-" + assessment.assessmentIndex + "-" + method.methodIndex}
                    aria-label={"Assessment " + assessment.assessmentIndex + ", method " + method.methodIndex +
                      ", " + method.method + ": " + (record?.status ?? "NOT_LOADED") +
                      ", grade " + (record?.grade === null || !record ? "not scored" : record.grade + " out of 5")}
                    onClick={() => {
                      const section = document.getElementById(assessment.assessmentIndex === 1 ? "first-scientific-assessment" :
                        "scientific-assessment-" + assessment.assessmentIndex);
                      if (section instanceof HTMLDetailsElement) section.open = true;
                      const item = document.getElementById("scientific-method-" +
                        assessment.assessmentIndex + "-" + method.methodIndex);
                      if (item instanceof HTMLDetailsElement) item.open = true;
                    }}
                    title={method.method + " · " + (record?.status ?? "NOT_LOADED")}
                    style={{display: "block", padding: "8px 4px", border: "1px solid #b4cfc2",
                      borderRadius: 6, textAlign: "center", color: "#154c3f", textDecoration: "none",
                      background: record?.grade !== null && record?.grade !== undefined ? "#d8efe2" : "#ffffff"}}>
                    <span style={{display: "block", fontSize: 11}}>M{method.methodIndex}</span>
                    <strong>{score}</strong>
                  </a>;
                })}
              </div>
              {errors[assessment.assessmentIndex] ?
                <p role="alert">Assessment records unavailable: {errors[assessment.assessmentIndex]}</p> : null}
            </section>;
          })}
          <button type="button" onClick={exportClinicalRegister}
            disabled={loadingAllScores || Object.keys(details).length!==40 || Object.values(errors).some(Boolean)}
            style={{padding:"10px 13px",border:"1px solid #218169",background:"#dbf7e9",
              color:"#154c3f",borderRadius:8,fontWeight:800,margin:"8px 0"}}>
            Export all 800 reviewer method records (CSV)
          </button>
          <p style={{fontSize:12,margin:"4px 0"}}>Available only after all 40 authenticated assessment records load.
            Exports independently recorded current grades, reviewer references, sources and evidence gaps;
            blank grades remain blank. This does not run scoring or issue an FDA forecast.</p>
          {exportError ? <p role="alert">Export blocked: {exportError}</p> : null}
          <p>Legend: N/R = not reviewed; N/A = explicitly not applicable; VERIFY = phase unverified;
             STALE = earlier-phase review; RETRACT = grade retracted; … = review not loaded.
             A score of 0/5 is a genuine reviewer grade, never a missing-data substitute.</p>
        </div> : null}
      </section>

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
          id={i===0 ? "first-scientific-assessment" : "scientific-assessment-" + assessment.assessmentIndex}
          style={{...panel,scrollMarginTop:90}} onToggle={event => {if (event.currentTarget.open) void loadAssessment(assessment.assessmentIndex);}}> 
          <summary><strong>Layer {assessment.layerId} · {assessment.assessmentId} {assessment.label}</strong> · {row.status} · {row.reviewedMethods} scored / 20 · {row.scoreOutOf100 === null ? "Unscored" : row.scoreOutOf100 + " / 100 evidence strength"}</summary>
          <p>{assessment.objective}</p>
          <p>Priority: {assessment.methods[0]?.priorityTier} · {assessment.methods[0]?.phaseApplicability}. Investigation order is not an observed risk.</p>
          <p>{row.pendingMethods} pending · {row.excludedMethods} explicitly excluded</p>
          {errors[assessment.assessmentIndex] ? <p role="alert">{errors[assessment.assessmentIndex]} <button type="button" onClick={() => void loadAssessment(assessment.assessmentIndex)}>Retry evidence</button></p> : null}
          {!detail && !errors[assessment.assessmentIndex] ? <p role="status">Loading 20 method records…</p> : null}
          {assessment.methods.map(method => <details key={method.methodIndex}
            id={"scientific-method-" + assessment.assessmentIndex + "-" + method.methodIndex} style={panel}>
            <summary>Method {method.methodIndex}: {method.method} · {detail?.methods?.[method.methodIndex - 1]?.status ?? "Evidence not loaded"} · Priority {method.priorityRank ?? "Verify phase"}</summary>
            <p>{method.methodDescription}</p><p>Required sources: {method.requiredSources}</p>
            {detail?.methods?.[method.methodIndex - 1] ? <MethodEvidence method={detail.methods[method.methodIndex - 1]} /> : <p>Method evidence not loaded. No score assigned.</p>}
          </details>)}
        </details>;
      })}
    </div> : null}
  </section>;
}
