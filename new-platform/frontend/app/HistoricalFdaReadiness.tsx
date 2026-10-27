"use client";
import { useEffect, useState } from "react";

type Status = { status: string; reason?: string; run_id?: number; run_created_at?: string; artifact_url?: string; candidate_count?: number | null; with_source_documents?: number | null; without_source_documents?: number | null; with_action_descriptions?: number | null; readiness?: string };

export default function HistoricalFdaReadiness() {
  const [data, setData] = useState<Status | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/historical-fda-status", { signal: controller.signal, cache: "no-store" })
      .then(r => r.json()).then(setData).catch(() => setData({ status: "UNAVAILABLE", reason: "Status request failed" }));
    return () => controller.abort();
  }, []);
  return <section className="panel"><details>
    <summary><strong>Historical FDA evidence and prediction readiness</strong></summary>
    <p><strong>Research artifact:</strong> {data === null ? "Checking…" : data.status === "INGESTION_REPORTED" ? "Ingestion report received (unverified candidates)" : "Unavailable"}</p>
    {data?.status === "INGESTION_REPORTED" && <p><strong>Staged submissions:</strong> {data.candidate_count ?? "Unavailable"} · <strong>With source documents:</strong> {data.with_source_documents ?? "Unavailable"} · <strong>Without source documents:</strong> {data.without_source_documents ?? "Unavailable"} · <strong>With action descriptions:</strong> {data.with_action_descriptions ?? "Unavailable"} · <strong>Readiness:</strong> {data.readiness ?? "SOURCE_REVIEW_REQUIRED"}</p>}
    {data?.reason && <p className="subtle">{data.reason}</p>}
    {data?.run_id && <p>Workflow run: {data.run_id}{data.run_created_at ? ` · ${data.run_created_at}` : ""}</p>}
    {data?.artifact_url && <p><a href={data.artifact_url} target="_blank" rel="noopener noreferrer">View historical FDA ingestion artifact</a></p>}
    <p><strong>Verified historical PASS/FAIL labels:</strong> Not established from this artifact.</p>
    <p><strong>Prediction validation:</strong> NOT VALIDATED FOR TRADING.</p>
    <p className="subtle">A published artifact is not evidence of independently verified FDA decisions or predictive accuracy.</p>
  </details></section>;
}
