"use client";

import { useEffect, useState } from "react";
import { evidenceSource, researchReadiness, type ResearchReadiness, type ResearchStage } from "../lib/research-readiness";

type MarketEnrichment = {
  programId: string;
  exactKey: string;
  ticker: string;
  status: string;
  feed?: string;
  asOf?: string | null;
  latestDailyClose?: number | null;
  latestIexVolume?: number | null;
  coverage?: string;
  orderExecutionEnabled?: boolean;
  marketEvidenceReview?: { status: string; observations: {metric: string; value: number; unit: string}[]; recommendation: null; };
  marketSignals?: {
    status: string;
    validBars: number;
    return20Pct: number | null;
    averageVolume20: number | null;
    volumeRatio20: number | null;
  };
};

export default function ProgramMarketEnrichment({ programId, exactKey, stage }: { programId: string; exactKey: string; stage: ResearchStage }) {
  const [data, setData] = useState<MarketEnrichment | null>(null);
  const [error, setError] = useState("");
  const [review, setReview] = useState<ResearchReadiness | null>(null);
  const [reviewError, setReviewError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    setError("");
    setReview(null);
    setReviewError("");
    fetch("/api/program-market-enrichment/" + encodeURIComponent(programId), {
      cache: "no-store", signal: controller.signal,
    }).then(async response => {
      if (!response.ok) throw new Error("Market enrichment unavailable (" + response.status + ")");
      return response.json() as Promise<MarketEnrichment>;
    }).then(value => {
      if (controller.signal.aborted) return;
      if (value.programId !== programId || value.exactKey !== exactKey) {
        setError("Program identity mismatch — market data withheld");
        return;
      }
      setData(value);
    }).catch(() => {
      if (!controller.signal.aborted) setError("Market enrichment unavailable; no values inferred");
    });
    const query = new URLSearchParams({ stage, identity: exactKey });
    fetch("/api/review/program-decision-readiness/" + encodeURIComponent(programId) + "?" + query, {
      cache: "no-store", signal: controller.signal,
    }).then(async response => {
      if (!response.ok) throw new Error("Review unavailable");
      return researchReadiness(await response.json(), programId, exactKey, stage);
    }).then(value => {
      if (!controller.signal.aborted) setReview(value);
    }).catch(() => {
      if (!controller.signal.aborted) setReviewError("Research readiness is unavailable for this deployment.");
    });
    return () => controller.abort();
  }, [programId, exactKey, stage]);

  const currentData = data?.programId === programId && data.exactKey === exactKey ? data : null;
  const currentReview = review?.programId === programId && review.exactKey === exactKey && review.stage === stage ? review : null;
  const authFailed = currentData?.status === "ALPACA_AUTH_FAILED" || currentReview?.marketDataStatus === "ALPACA_AUTH_FAILED";

  return <div className="program-market-enrichment" aria-label="Alpaca read-only market enrichment">
    <strong>Alpaca market snapshot · Research only</strong>
    {authFailed && <p role="status">Alpaca rejected the configured API credentials. Update the Alpaca key pair to load market evidence.</p>}
    {error ? <p role="status">{error}</p> : !currentData ? <p role="status">Loading verified market snapshot…</p>
      : currentData.status !== "OK" ? <p role="status">Market snapshot unavailable ({currentData.status}). No price or volume inferred.</p>
      : <p>Daily close: {typeof currentData.latestDailyClose === "number" ? "$" + currentData.latestDailyClose.toFixed(2) : "Unavailable"}
          {" · "}IEX volume: {typeof currentData.latestIexVolume === "number" ? currentData.latestIexVolume.toLocaleString() : "Unavailable"}
          {" · "}As of: {currentData.asOf || "Unknown"}
          {" · "}Feed: {currentData.feed || "Unknown"}</p>}
    {currentData?.status === "OK" && <div aria-label="Research-only market signals">
      <strong>20-bar market signals · Not a trade recommendation</strong>
      {currentData.marketSignals?.status === "OK" ? <p>
        Price movement: {currentData.marketSignals.return20Pct?.toFixed(2) ?? "Unavailable"}%
        {" · "}Latest / average IEX volume: {currentData.marketSignals.volumeRatio20?.toFixed(2) ?? "Unavailable"}×
        {" · "}Valid bars: {currentData.marketSignals.validBars}
      </p> : <p role="status">Insufficient validated history for market signals.</p>}
    </div>}
    {currentData?.status === "OK" && <div aria-label="Program market evidence review">
      <strong>GEM research evidence · Separate from the 21 assessment scores</strong>
      {currentData.marketEvidenceReview?.status === "RESEARCH_ONLY" && currentData.marketEvidenceReview.observations.length === 2
        ? <p>20-bar change: {currentData.marketEvidenceReview.observations[0].value.toFixed(2)}%
            {" · "}Relative IEX volume: {currentData.marketEvidenceReview.observations[1].value.toFixed(2)}×</p>
        : <p role="status">Market evidence incomplete; no assessment or trade rating inferred.</p>}
    </div>}
    <div aria-label="Investment research readiness">
      <strong>{stage === "GEM_JR" ? "GEM JR" : "GEM"} research readiness: {currentReview
        ? currentReview.decisionReadiness.status === "READY_FOR_HUMAN_RESEARCH_REVIEW" ? "Ready for human review" : "Not ready"
        : "Awaiting evidence review"}</strong>
      {reviewError ? <p role="status">{reviewError}</p> : !currentReview ? <p role="status">Loading exact-program research evidence…</p> : <>
        <p>Assessment: {currentReview.assessmentEvidence.status.replaceAll("_", " ")}</p>
        {currentReview.decisionReadiness.missingRequirements.length > 0 && <p>Required evidence: {currentReview.decisionReadiness.missingRequirements.join("; ")}.</p>}
        <ul>{currentReview.riskEvidenceReview.checks.map(check => <li key={check.id}>
          <strong>{check.label}: {check.status.replaceAll("_", " ")}</strong>
          <p>{check.reason}</p>
          {(check.sourceDate || check.checkedAt) && <small>Source date: {check.sourceDate || "Unknown"} · Reviewed: {check.checkedAt || "Unknown"} </small>}
          {evidenceSource(check.source) && <a href={evidenceSource(check.source)} target="_blank" rel="noopener noreferrer">Primary source ↗</a>}
        </li>)}</ul>
        {currentReview.riskEvidenceReview.riskFlags.length > 0 && <p>Recorded risks: {currentReview.riskEvidenceReview.riskFlags.join("; ")}</p>}
        {currentReview.sourceEvidence && <details>
          <summary>Clinical &amp; financing source facts</summary>
          <p>Source observations support review. Clinical interpretation and financing clearance still require review.</p>
          {(["clinical", "financial"] as const).map(kind => {
            const group = currentReview.sourceEvidence![kind];
            return <section key={kind} aria-label={kind === "clinical" ? "Exact trial registry facts" : "Company financial source facts"}>
              <h4>{kind === "clinical" ? "Exact trial registry" : "Company financials · " + currentReview.sourceEvidence!.ticker}</h4>
              <p>{group.status.replaceAll("_", " ")} · {group.note}</p>
              <ul>{group.facts.map((item, index) => <li key={item.label + index}>
                <strong>{item.label}: {item.value}</strong> · {item.status}
                <p>Source date: {item.sourceDate || "Not recorded"} · Checked: {item.checkedAt || "Not recorded"}{" "}
                  {evidenceSource(item.source) && <a href={evidenceSource(item.source)} target="_blank" rel="noopener noreferrer">Source ↗</a>}
                </p>
              </li>)}</ul>
            </section>;
          })}
        </details>}
      </>}
      <small>Research review retains the existing assessment scores. No trade recommendation is generated.</small>
    </div>
    <small>IEX volume is single-exchange coverage, not consolidated market volume. No trades or restrictions are changed.</small>
  </div>;
}
