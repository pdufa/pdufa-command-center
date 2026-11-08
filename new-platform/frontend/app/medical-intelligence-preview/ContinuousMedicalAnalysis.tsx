"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type Status = "PENDING" | "RUNNING" | "COMPLETE" | "FAILED" | "STOPPED";
type StageStatus = "QUEUED" | "RUNNING" | "SOURCE_RECORDED" | "LEADS_ONLY" | "EVIDENCE_GAP" | "SOURCE_UNAVAILABLE";
type Stage = { number: number; title: string; state: StageStatus; details: Record<string, unknown> | null; finishedAt: string | null };
type Run = { runId: string; nct: string; status: Status; stageNumber: number; completedStages: number; totalStages: number;
  stopRequested: boolean; startedAt: string; updatedAt: string; stages: Stage[]; decision: "ABSTAIN"; note: string };
const complete = new Set<StageStatus>(["SOURCE_RECORDED", "LEADS_ONLY", "EVIDENCE_GAP", "SOURCE_UNAVAILABLE"]);
const muted = { color: "#50685c", fontSize: 13, lineHeight: 1.55 } as const;
const green = "#006452";

function validate(value: unknown, nct: string): Run {
  if (!value || typeof value !== "object") throw Error("Invalid saved run response");
  const obj = value as Run;
  if (obj.nct !== nct || !/^[\da-f-]{36}$/i.test(obj.runId) || obj.totalStages !== 12 ||
      !Array.isArray(obj.stages) || obj.stages.length !== 12 ||
      !["PENDING", "RUNNING", "COMPLETE", "FAILED", "STOPPED"].includes(obj.status))
    throw Error("Medical stage run identity or schema mismatch");
  return obj;
}
function friendly(value: unknown): string {
  if (typeof value === "string") return value;
  if (value === null || value === undefined) return "Not recorded";
  return JSON.stringify(value, null, 2);
}
function Detail({ name, value }: { name: string; value: unknown }) {
  const text = friendly(value);
  const isSource = /^(source|url|issuerEvidenceUrl|trialResultsUrl)$/i.test(name) &&
    /^https:\/\/[^\s]+$/.test(text);
  return <div style={{ padding: "7px 0", borderBottom: "1px solid #e5ede6" }}>
    <div style={{ fontSize: 12, fontWeight: 700, color: "#50685c" }}>{name.replace(/([A-Z])/g, " $1").replaceAll("_", " ")}</div>
    {isSource
      ? <a href={text} target="_blank" rel="noopener noreferrer" style={{ overflowWrap: "anywhere", fontSize: 13 }}>{text}</a>
      : <div style={{ fontSize: 13, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{text}</div>}
  </div>;
}
function statusText(value: StageStatus): string {
  return {
    QUEUED: "Queued", RUNNING: "Running", SOURCE_RECORDED: "Source recorded",
    LEADS_ONLY: "Research leads", EVIDENCE_GAP: "Evidence gap", SOURCE_UNAVAILABLE: "Source unavailable"
  }[value];
}

/** Durable worker lives on the backend; page navigation and polling never initiate a new job. */
export default function ContinuousMedicalAnalysis({ nct }: { nct: string }) {
  const [run, setRun] = useState<Run | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const mounted = useRef(true);
  const endpoint = "/api/medical-intelligence-preview/continuous";

  const refresh = useCallback(async (runId?: string, initial = false) => {
    try {
      const query = new URLSearchParams({ nct });
      if (runId) query.set("run", runId);
      const response = await fetch(endpoint + "?" + query.toString(), { cache: "no-store" });
      if (response.status === 404 && initial) {
        if (mounted.current) { setRun(null); setNote("No previous continuous run recorded for this trial."); setError(""); }
        return;
      }
      if (!response.ok) {
        if (mounted.current) setError(response.status === 401 ? "Sign in to view saved research runs." :
          "Continuous processing backend unavailable or not yet deployed.");
        return;
      }
      const data: unknown = await response.json();
      if (mounted.current) { setRun(validate(data, nct)); setError(""); setNote(""); }
    } catch {
      if (mounted.current) setError("Cannot read saved run status. The backend may still be processing.");
    } finally {
      if (initial && mounted.current) setLoading(false);
    }
  }, [nct]);

  useEffect(() => {
    mounted.current = true;
    void refresh(undefined, true);
    return () => { mounted.current = false; };
  }, [refresh]);

  useEffect(() => {
    if (run?.status !== "RUNNING" && run?.status !== "PENDING") return;
    const timer = setInterval(() => { void refresh(run.runId); }, 3500);
    return () => clearInterval(timer);
  }, [run?.status, run?.runId, refresh]);

  async function action(kind: "start" | "stop" | "resume") {
    if (busy) return;
    setBusy(true); setError(""); setNote("");
    try {
      const request = kind === "start"
        ? { action: "start", nct, requestKey: crypto.randomUUID() }
        : { action: kind, nct, run: run?.runId };
      const response = await fetch(endpoint, {
        method: "POST", cache: "no-store", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request)
      });
      const raw: unknown = await response.json();
      if (!response.ok) {
        const msg = raw && typeof raw === "object" && "error" in raw ? (raw as { error?: unknown }).error : null;
        throw Error(typeof msg === "string" ? msg : "Continuous run control unavailable");
      }
      const saved = validate(raw, nct);
      setRun(saved);
      setNote(kind === "start" ? "Server-side job accepted. You may close this page; progress is saved." :
        kind === "stop" ? "Stop requested. The server will stop after the current stage." :
        "Resumed from the last saved stage.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Cannot control run");
    } finally { setBusy(false); }
  }

  const percent = run ? Math.round(run.completedStages / run.totalStages * 100) : 0;
  return <section aria-label="Persistent twelve-stage medical research" style={{
    border: "1px solid #b9d5c4", background: "#fff", borderRadius: 12, padding: 17, marginTop: 16
  }}>
    <h2 style={{ margin: "0 0 8px", fontSize: 21 }}>Continuous Medical Intelligence — 12-stage run</h2>
    <p style={muted}>Press <strong>Run All 12 Stages</strong> once. The persistent worker continues from stage to stage
      even if you close this page, saves each stage, and restores progress when you return.
      The page itself never launches research automatically.</p>
    <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", margin: "14px 0" }}>
      <button type="button" onClick={() => void action("start")} disabled={busy || loading || run?.status === "RUNNING" || run?.status === "PENDING"}
        style={{ padding: "11px 16px", background: green, color: "white", border: 0, borderRadius: 8, fontWeight: 700, cursor: "pointer" }}>
        {busy ? "Processing request…" : "Run All 12 Stages"}
      </button>
      {run && (run.status === "PENDING" || run.status === "RUNNING") && <button type="button" disabled={busy || run.stopRequested}
        onClick={() => void action("stop")} style={{ padding: "11px 14px", borderRadius: 8 }}>Stop after current stage</button>}
      {run?.status === "STOPPED" && <button type="button" disabled={busy}
        onClick={() => void action("resume")} style={{ padding: "11px 14px", borderRadius: 8 }}>Resume saved run</button>}
      <button type="button" onClick={() => void refresh(run?.runId)} disabled={loading}
        style={{ padding: "11px 14px", borderRadius: 8 }}>Refresh progress</button>
      <span style={muted} role="status">{loading ? "Loading saved status…" :
        run ? run.status.replaceAll("_", " ") : "No run started"}</span>
    </div>
    {error && <p role="alert" style={{ color: "#93463b" }}>{error}</p>}
    {note && <p role="status" style={muted}>{note}</p>}
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
      <strong>{run ? run.completedStages + " / 12 stages attempted" : "0 / 12 stages attempted"}</strong>
      <strong>{percent}%</strong>
    </div>
    <div role="progressbar" aria-label="Completed source-collection stages" aria-valuemin={0} aria-valuemax={12}
      aria-valuenow={run?.completedStages || 0}
      style={{ height: 11, background: "#e8efe9", borderRadius: 999, overflow: "hidden", margin: "9px 0" }}>
      <div style={{ width: percent + "%", height: "100%", background: green }} />
    </div>
    <p style={{ ...muted, marginTop: 4 }}>This percentage measures stages attempted, <strong>not</strong> verified scientific evidence completeness or FDA approval probability.</p>
    {run && <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
      {run.stages.map(stage => <details key={stage.number} open={stage.state === "RUNNING"}
        style={{ border: "1px solid #dae5dc", borderRadius: 9, padding: "10px 12px", background: stage.state === "RUNNING" ? "#f3f9f4" : "white" }}>
        <summary style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", gap: 12, alignItems: "baseline" }}>
          <span style={{ fontWeight: 700, fontSize: 14 }}>{stage.number}. {stage.title}</span>
          <span style={{ fontSize: 12, color: complete.has(stage.state) ? green : "#52665c" }}>{statusText(stage.state)}</span>
        </summary>
        {stage.details ? <div style={{ marginTop: 10 }}>
          {Object.entries(stage.details).map(([name, value]) => <Detail key={name} name={name} value={value} />)}
          <p style={muted}>Recorded: {stage.finishedAt || "Not recorded"}</p>
        </div> : <p style={muted}>{stage.state === "RUNNING" ? "The server is collecting this stage's evidence." :
          "Not started. The persistent worker advances here automatically after prior stages."}</p>}
      </details>)}
    </div>}
    <p style={{ ...muted, marginTop: 14, marginBottom: 0 }}>
      <strong>Research boundary:</strong> These stages collect registry facts, literature leads and documented gaps.
      They do not complete the full 40 × 20 scientific assessment, independent specialist signoff, FDA CMC adjudication or a calibrated approval/CRL prediction. The final decision remains <strong>ABSTAIN</strong> until evidence supports otherwise.
    </p>
  </section>;
}
