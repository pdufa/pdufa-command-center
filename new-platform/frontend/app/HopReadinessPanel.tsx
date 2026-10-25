"use client";

import { useEffect, useState } from "react";
import type { HopSourceReadiness } from "../lib/hop-readiness";

function formatCount(value: number | null): string {
  return value === null ? "Not verified" : value.toLocaleString("en-US");
}

export default function HopReadinessPanel() {
  const [report, setReport] = useState<HopSourceReadiness | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setReport(null);
    fetch("/api/hop/readiness", {
      cache: "no-store",
      signal: AbortSignal.any([controller.signal, AbortSignal.timeout(32000)]),
    }).then(async response => {
      if (!response.ok) throw new Error("Historical source verification unavailable");
      return response.json() as Promise<HopSourceReadiness>;
    }).then(data => {
      if (!controller.signal.aborted) {
        if (data.status !== "RESEARCH_ONLY" || data.modelValidated !== false || data.predictionAvailable !== false) {
          throw new Error("Historical source readiness was not confirmed");
        }
        setReport(data);
      }
    }).catch(() => {
      if (!controller.signal.aborted) setError("Could not verify the source audit. Counts and predictions are withheld.");
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [revision]);

  return <section className="panel" aria-label="HOP verified source progress">
    <h3>Historical FDA source progress</h3>
    <p className="subtle">Read-only source audit. The FDA archives below are research inputs, not a complete or representative set of FDA decisions.</p>
    <button type="button" className="secondary" onClick={() => setRevision(v => v + 1)} disabled={loading}>
      {loading ? "Checking historical sources…" : "Recheck source status"}
    </button>
    {error ? <p role="alert">{error}</p> : loading ? <p role="status">Checking the authenticated research audit…</p> : report ? <>
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit, minmax(165px, 1fr))",gap:10,margin:"12px 0"}}>
        <div className="panel"><strong>Published FDA letter records</strong><p>{formatCount(report.publishedLetters)}</p><small>Source export: {report.publishedLetterExportDate || "Not verified"} · Quarantined</small></div>
        <div className="panel"><strong>Drugs@FDA application records</strong><p>{formatCount(report.approvedApplications)}</p><small>Source export: {report.approvedRegistryExportDate || "Not verified"} · Approval-centric registry</small></div>
        <div className="panel"><strong>Independently model-eligible review cycles</strong><p>{formatCount(report.modelEligibleReviewCycles)}</p><small>Complete outcome cohort not verified</small></div>
      </div>
      <p role="status"><strong>Prediction availability: NOT VALIDATED.</strong> No calibrated approval probability can be displayed. {report.stagedHistoricalCases !== null ? formatCount(report.stagedHistoricalCases) + " curated historical example(s) remain in staging only." : ""}</p>
      <details>
        <summary>Show evidence review and remaining verification requirements</summary>
        <p>Published-letter PDF review worklist: {formatCount(report.sourcePageReviewRows)} source references. Independently verified review-cycle outcomes from this worklist: {formatCount(report.independentlyVerifiedReviewCycles)}.</p>
        <p>Before HOP may generate probabilities, reviewers must reconcile a complete NDA/BLA decision denominator, identify separate review cycles, verify predecision trial and FDA evidence dates, link exact indications and sponsors, and pass chronological out-of-sample calibration tests.</p>
        <p>Research sources: <a href="https://open.fda.gov/apis/transparency/completeresponseletters/" target="_blank" rel="noopener noreferrer">FDA published letters</a> and <a href="https://open.fda.gov/apis/drug/drugsfda/" target="_blank" rel="noopener noreferrer">Drugs@FDA</a>.</p>
      </details>
      <p className="subtle">Audit checked: {new Date(report.checkedAt).toLocaleString()}. This read did not run an FDA collection scan or modify trial scores, FS/FA presets, or watch/trade labels.</p>
    </> : null}
  </section>;
}
