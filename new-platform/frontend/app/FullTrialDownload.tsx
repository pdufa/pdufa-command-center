"use client";

import { useCallback, useEffect, useState } from "react";

type DownloadStatus = {
  status: string; target: number; downloaded: number; complete: boolean;
  statisticalAnalyses?: number; reportedPValues?: number; missing?: number;
  updatedAt?: string; completedAt?: string; exportReady?: boolean; error?: string;
};

export default function FullTrialDownload() {
  const [status, setStatus] = useState<DownloadStatus | null>(null);
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(false);

  const reload = useCallback(async (signal?: AbortSignal) => {
    try {
      const response = await fetch("/api/full-trials", { cache: "no-store", signal });
      if (!response.ok) throw new Error("Full-record download status is temporarily unavailable.");
      const value = await response.json() as DownloadStatus;
      if (!signal?.aborted) { setStatus(value); setError(""); }
    } catch (cause) {
      if (!signal?.aborted) setError(cause instanceof Error ? cause.message : "Unable to read download status.");
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void reload(controller.signal);
    return () => { controller.abort(); };
  }, [reload]);

  async function collect(refresh = false) {
    setStarting(true);
    setError("");
    try {
      const response = await fetch("/api/full-trials", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh }),
      });
      if (!response.ok) throw new Error("Unable to start the full-record download. Try again.");
      setStatus(await response.json());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to start download.");
    } finally { setStarting(false); }
  }

  const busy = starting || status?.status === "RUNNING" || status?.status === "PENDING";
  return <section className="panel" aria-label="All-phase trial data download">
    <div className="sectionhead"><div><h3>ALL-PHASE DATA DOWNLOAD</h3>
      <p className="subtle">Complete ClinicalTrials.gov records for every tracked trial. Stage, date and market-cap filters do not restrict this download.</p></div>
      <div className="pipeline-actions">
        {status?.complete && status.exportReady ? <>
          <a className="streamlit-fallback" href="/api/full-trials/download">DOWNLOAD ALL FIELDS · ZIP</a>
          <button type="button" className="secondary" disabled={starting} onClick={() => void collect(true)}>Update from registry</button>
        </> : <button type="button" disabled={busy || !status || Boolean(status.complete && !status.exportReady)} onClick={() => void collect()}>
          {status?.complete ? "Preparing complete ZIP…" : busy ? "Downloading complete records…" : status?.status === "PARTIAL" ? "RESUME MISSING RECORDS" : "COLLECT ALL FIELDS"}
        </button>}
      </div>
    </div>
    <p role="status" aria-live="polite">{status ?
      `${status.downloaded.toLocaleString("en-US")} / ${status.target.toLocaleString("en-US")} full trial records · ${status.status.replaceAll("_", " ")}` : "Loading full-record download status…"}
      {status && status.statisticalAnalyses !== undefined ? ` · ${status.statisticalAnalyses.toLocaleString("en-US")} statistical analyses · ${(status.reportedPValues || 0).toLocaleString("en-US")} reported p-values` : ""}
    </p>
    <p className="subtle">ZIP includes trials.csv, statistical_analyses.csv, full_studies.jsonl, record checksums and a coverage manifest. Reported p-values retain their endpoints and comparison groups. Missing p-values remain marked as not reported.</p>
    {(error || status?.error) && <p role="alert" className="error">{error || status?.error}</p>}
  </section>;
}
