"use client";

import { useEffect, useState } from "react";

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

export default function ProgramMarketEnrichment({ programId, exactKey }: { programId: string; exactKey: string }) {
  const [data, setData] = useState<MarketEnrichment | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    setError("");
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
    return () => controller.abort();
  }, [programId, exactKey]);

  return <div className="program-market-enrichment" aria-label="Alpaca read-only market enrichment">
    <strong>Alpaca market snapshot · Research only</strong>
    {error ? <p role="status">{error}</p> : !data ? <p role="status">Loading verified market snapshot…</p>
      : data.status !== "OK" ? <p role="status">Market snapshot unavailable ({data.status}). No price or volume inferred.</p>
      : <p>Daily close: {typeof data.latestDailyClose === "number" ? "$" + data.latestDailyClose.toFixed(2) : "Unavailable"}
          {" · "}IEX volume: {typeof data.latestIexVolume === "number" ? data.latestIexVolume.toLocaleString() : "Unavailable"}
          {" · "}As of: {data.asOf || "Unknown"}
          {" · "}Feed: {data.feed || "Unknown"}</p>}
    {data?.status === "OK" && <div aria-label="Research-only market signals">
      <strong>20-bar market signals · Not a trade recommendation</strong>
      {data.marketSignals?.status === "OK" ? <p>
        Price movement: {data.marketSignals.return20Pct?.toFixed(2) ?? "Unavailable"}%
        {" · "}Latest / average IEX volume: {data.marketSignals.volumeRatio20?.toFixed(2) ?? "Unavailable"}×
        {" · "}Valid bars: {data.marketSignals.validBars}
      </p> : <p role="status">Insufficient validated history for market signals.</p>}
    </div>}
    {data?.status === "OK" && <div aria-label="Program market evidence review">
      <strong>GEM research evidence · Separate from the 21 assessment scores</strong>
      {data.marketEvidenceReview?.status === "RESEARCH_ONLY" && data.marketEvidenceReview.observations.length === 2
        ? <p>20-bar change: {data.marketEvidenceReview.observations[0].value.toFixed(2)}%
            {" · "}Relative IEX volume: {data.marketEvidenceReview.observations[1].value.toFixed(2)}×</p>
        : <p role="status">Market evidence incomplete; no assessment or trade rating inferred.</p>}
    </div>}
    <small>IEX volume is single-exchange coverage, not consolidated market volume. No trades or restrictions are changed.</small>
  </div>;
}
