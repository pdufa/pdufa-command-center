"use client";

import { useRef, useState } from "react";
import type { TrialEvidence } from "../../lib/medical-intelligence-preview";
import type { RegistryResultReport } from "../../lib/medical-intelligence-registry-results";

type RunResult = {
  nct: string;
  status: "SOURCE_RETRIEVED_REQUIRES_REVIEW";
  retrievedAt: string;
  sourceUrl: string;
  evidence: TrialEvidence;
  results: RegistryResultReport;
  scope: string;
  decision: "INSUFFICIENT_EVIDENCE";
};
const muted = { fontSize: 13, lineHeight: 1.55, color: "#52665c" } as const;

export default function OnDemandRegistryResearch({ nct }: { nct: string }) {
  const [status, setStatus] = useState<"IDLE" | "RUNNING" | "DONE" | "ERROR">("IDLE");
  const [error, setError] = useState("");
  const [data, setData] = useState<RunResult | null>(null);
  const active = useRef<AbortController | null>(null);

  async function run() {
    if (status === "RUNNING") return;
    const controller = new AbortController();
    active.current = controller;
    setError("");
    setData(null);
    setStatus("RUNNING");
    try {
      const response = await fetch("/api/medical-intelligence-preview/run", {
        method: "POST", cache: "no-store", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nct }), signal: controller.signal
      });
      const raw: unknown = await response.json();
      if (!response.ok) {
        const problem = raw && typeof raw === "object" && "error" in raw ? (raw as { error?: unknown }).error : null;
        throw Error(typeof problem === "string" ? problem : "Source check failed");
      }
      const result = raw as RunResult;
      if (result.nct !== nct || result.evidence?.nct !== nct || result.results?.nct !== nct ||
          result.status !== "SOURCE_RETRIEVED_REQUIRES_REVIEW")
        throw Error("Registry trial identity mismatch");
      setData(result);
      setStatus("DONE");
    } catch (cause) {
      if (controller.signal.aborted) setStatus("IDLE");
      else {
        setError(cause instanceof Error ? cause.message : "Unable to retrieve the clinical study");
        setStatus("ERROR");
      }
    } finally {
      if (active.current === controller) active.current = null;
    }
  }

  return <section aria-label="Manually started external evidence collection"
    style={{ background: "#fff", border: "1px solid #cbdad0", borderRadius: 12, padding: 18, marginTop: 16 }}>
    <h2 style={{ margin: "0 0 8px", fontSize: 20 }}>External evidence research</h2>
    <p style={muted}>Opening this page only shows saved research. <strong>Nothing is collected externally until you press Run.</strong></p>
    <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center" }}>
      <button type="button" onClick={run} disabled={status === "RUNNING"}
        style={{ border: 0, borderRadius: 8, background: "#005e52", color: "white",
          padding: "12px 18px", fontWeight: 700, cursor: status === "RUNNING" ? "wait" : "pointer" }}>
        {status === "RUNNING" ? "Retrieving official source…" : "Run External Source Check"}
      </button>
      {status === "RUNNING" && <button type="button" onClick={() => active.current?.abort()}>Cancel</button>}
      <span role="status" aria-live="polite" style={muted}>
        {status === "IDLE" ? "Not started" : status === "RUNNING" ? "Running at your request" :
          status === "DONE" ? "Source retrieved — review pending" : "Source check failed"}
      </span>
    </div>
    {error && <p role="alert" style={{ color: "#8d352e" }}>{error}</p>}
    <p style={{ ...muted, marginBottom: data ? 12 : 0 }}>
      Currently runs an exact-NCT ClinicalTrials.gov lookup for <strong>{nct}</strong>. Other FDA, SEC,
      company, PubMed, manufacturing and subspecialty sources still require separate investigation.
    </p>
    {data && <div style={{ display: "grid", gap: 12 }}>
      <div style={{ padding: 12, background: "#f5faf6", borderRadius: 8 }}>
        <strong>{data.evidence.title || nct}</strong>
        <p style={muted}>Retrieved: {data.retrievedAt} (UTC) · <a href={data.sourceUrl} target="_blank" rel="noopener noreferrer">Official registry source</a></p>
        <p style={muted}>{data.evidence.conditions.join("; ") || "Condition unavailable"} · {data.evidence.phases.join(", ") || "Phase unavailable"} · {data.evidence.status || "Status unavailable"}</p>
        <p style={muted}>Enrollment: {data.evidence.enrollment ?? "Unavailable"} · Masking: {data.evidence.masking || "Unavailable"} · Allocation: {data.evidence.allocation || "Unavailable"}</p>
      </div>
      <div style={{ display: "flex", gap: 18, flexWrap: "wrap", fontSize: 14 }}>
        <span><strong>{data.evidence.primaryEndpoints.length}</strong> primary endpoints</span>
        <span><strong>{data.results.outcomes.length}</strong> posted outcomes</span>
        <span><strong>{data.results.outcomes.reduce((sum, x) => sum + x.analyses.length, 0)}</strong> statistical comparisons</span>
        <span><strong>{data.results.events.length}</strong> adverse-event groups</span>
      </div>
      <details>
        <summary style={{ fontWeight: 700, cursor: "pointer" }}>Trial endpoints</summary>
        <strong>Primary</strong>
        <ol>{data.evidence.primaryEndpoints.map((x, i) => <li key={i}>{x}</li>)}</ol>
        <strong>Secondary</strong>
        <ol>{data.evidence.secondaryEndpoints.map((x, i) => <li key={i}>{x}</li>)}</ol>
      </details>
      <details>
        <summary style={{ fontWeight: 700, cursor: "pointer" }}>Registry p-values and confidence intervals</summary>
        {!data.results.outcomes.length && <p style={muted}>No registry outcome table retrieved; missing data do not prove an endpoint failed.</p>}
        {data.results.outcomes.map((outcome, i) => <div key={i} style={{ borderTop: "1px solid #cbdad0", padding: "9px 0", fontSize: 13 }}>
          <strong>{outcome.type}: {outcome.title}</strong>
          {outcome.analyses.map((a, j) => <p key={j}>
            {a.comparisons.join(" versus ") || "Comparison not specified"} · Reported p: {a.reportedPValue || "Not provided"} ·
            CI: {a.confidenceInterval || "Not provided"} · Method: {a.method || "Not provided"}
          </p>)}
        </div>)}
      </details>
      <details>
        <summary style={{ fontWeight: 700, cursor: "pointer" }}>Adverse-event counts by treatment group</summary>
        {data.results.events.map((g, i) => <p style={muted} key={g.id || i}>
          <strong>{g.title}</strong> — Serious {g.seriousAffected ?? "?"}/{g.seriousAtRisk ?? "?"};
          Other {g.otherAffected ?? "?"}/{g.otherAtRisk ?? "?"};
          Deaths {g.deathAffected ?? "?"}/{g.deathAtRisk ?? "?"}
        </p>)}
      </details>
      <p style={{ ...muted, marginBottom: 0 }}><strong>Research boundary:</strong> {data.scope}
        No prediction was generated or saved by this action.</p>
    </div>}
  </section>;
}
