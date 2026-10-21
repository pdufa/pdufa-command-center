"use client";

import { useEffect, useState } from "react";
import type { Candidate } from "./Workspace";
import { DESIGNATION_COLUMNS, designationLabel, resolveTrialDesignations,
  type DesignationEvidence, type DesignationIndex, type DesignationKey, type TrialDesignations } from "../lib/trial-designations";

export function useTrialDesignations() {
  const [index, setIndex] = useState<DesignationIndex | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true); setError("");
      try {
        const response = await fetch("/api/trial-designations", { cache: "no-store", signal: controller.signal });
        if (!response.ok) throw new Error("Saved FDA designation details are unavailable.");
        const data = await response.json() as DesignationIndex;
        if (data.schemaVersion !== 1 || !data.programs || !data.trialEvents ||
            Array.isArray(data.programs) || Array.isArray(data.trialEvents)) throw new Error("Saved FDA designation details could not be validated.");
        if (!controller.signal.aborted) setIndex(data);
      } catch (cause) {
        if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "Unable to load FDA designation details.");
      } finally { if (!controller.signal.aborted) setLoading(false); }
    }
    void load();
    return () => controller.abort();
  }, [attempt]);
  return { index, loading, error, retry: () => setAttempt(value => value + 1) };
}

function EvidenceDetails({ value, kind }: { value: DesignationEvidence; kind: DesignationKey }) {
  return <dl className="trial-designation-evidence">
    <div><dt>Evidence</dt><dd>{value.verification === "FDA_VERIFIED" ? "FDA document linked" : "Saved source record; current status needs verification"}</dd></div>
    <div><dt>{kind === "accelerated_approval" ? "Approval date" : "Designation date"}</dt><dd>{value.designationDate || "Not recorded"}</dd></div>
    <div><dt>Last verified</dt><dd>{value.checkedAt || "Not recorded"}</dd></div>
    <div><dt>Source</dt><dd>{value.source ? <a href={value.source} target="_blank" rel="noopener noreferrer">Open supporting source ↗</a> : "Not linked"}</dd></div>
    {value.note && <div><dt>Source note</dt><dd>{value.note}</dd></div>}
  </dl>;
}

export function TrialDesignationCell({ value, kind, loading = false, unavailable = false }: {
  value: DesignationEvidence; kind: DesignationKey; loading?: boolean; unavailable?: boolean;
}) {
  const known = value.status !== "UNKNOWN";
  return <td className="trial-designation-cell" data-designation={kind}>
    <strong className={known ? "trial-designation-reported" : "subtle"} title={value.note}>
      {known ? designationLabel(value, kind) : loading ? "Loading…" : unavailable ? "Unavailable" : "Not verified"}
    </strong>
    {known && <details className="trial-designation-details"><summary>{DESIGNATION_COLUMNS.find(item => item.key === kind)?.label} details</summary>
      <EvidenceDetails value={value} kind={kind} />
    </details>}
  </td>;
}

export function TrialDesignationCells({ row, index, loading, error }: {
  row: Candidate; index: DesignationIndex | null; loading: boolean; error: string;
}) {
  const values = resolveTrialDesignations(row, index);
  return <>{DESIGNATION_COLUMNS.map(({ key }) => <TrialDesignationCell key={key} kind={key} value={values[key]}
    loading={loading} unavailable={!!error && !index} />)}</>;
}

export function TrialDesignationPanel({ row, values, loading, error, retry }: {
  row: Candidate; values: TrialDesignations; loading: boolean; error: string; retry: () => void;
}) {
  return <section className="trial-designation-panel" aria-label="FDA designations and programs">
    <div className="sectionhead"><h3>FDA designations and programs</h3>
      {error && <button type="button" className="secondary" onClick={retry}>Retry designation details</button>}</div>
    <p className="subtle small">Evidence for {row.drug || row.nctId || row.programId || row.ticker}. Missing evidence remains Not verified. Accelerated Approval is an approval pathway.</p>
    {error && <p role="status" className="subtle">{error}</p>}
    <div className="trial-designation-grid">{DESIGNATION_COLUMNS.map(({ key, label }) => <article key={key}>
      <h4>{label}</h4><strong>{values[key].status !== "UNKNOWN" ? designationLabel(values[key], key) : loading ? "Loading…" : "Not verified"}</strong>
      {values[key].status !== "UNKNOWN" ? <EvidenceDetails value={values[key]} kind={key} /> : <p className="subtle small">{values[key].note}</p>}
    </article>)}</div>
  </section>;
}
