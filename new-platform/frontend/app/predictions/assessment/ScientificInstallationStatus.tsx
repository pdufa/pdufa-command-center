"use client";
import {useEffect, useState} from "react";
import type {MedicalInstallationSnapshot} from "../../../lib/medical-installation-status";

const panel = {border: "1px solid #a8c9bc", borderRadius: 9, padding: 14, margin: "12px 0"} as const;
const quantity = (value: number | null) => value === null ? "Not verified" : String(value);
export default function ScientificInstallationStatus() {
  const [snapshot, setSnapshot] = useState<MedicalInstallationSnapshot | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const abort = new AbortController();
    fetch("/api/predictions/medical-installation", {cache: "no-store", signal: abort.signal})
      .then(async response => {
        const value = await response.json();
        if (!response.ok) throw Error(value.error || "Installation observations unavailable");
        if (!abort.signal.aborted) setSnapshot(value as MedicalInstallationSnapshot);
      }).catch(e => {if (!abort.signal.aborted) setError(e instanceof Error ? e.message : "Installation observations unavailable");});
    return () => abort.abort();
  }, []);
  const installation = snapshot?.installation;
  const current = installation?.tasks.find(task => task.id === installation.currentTaskId);
  return <section style={{...panel, background: "white"}} aria-label="MAIN scientific installation status">
    <h3>MAIN scientific installation status</h3>
    <p>Progress follows the current task and observed ledger counts. Methodology positions and retrieved sources do not count as independently graded scientific tests.</p>
    {error ? <p role="alert">{error} No completion count is inferred.</p> : null}
    {!snapshot && !error ? <p role="status">Loading isolated installation observations…</p> : null}
    {snapshot && installation ? <div>
      <p>Observed: {snapshot.observedAt} · State: <strong>{installation.state}</strong></p>
      {installation.reason ? <p>{installation.reason}</p> : null}
      {current ? <p>Current task: <strong>{current.id} · {current.title}</strong> · {current.status}<br />
        Completed: {quantity(current.completed)} · Remaining: {quantity(current.remaining)}<br />
        Next action / dependency: {current.dependency ?? "Acceptance condition observed"}</p> : <p>Current task is not observable from the isolated ledger.</p>}
      {installation.counts ? <p>Attached completed source runs: {installation.counts.sourceCompleteTrials} / {installation.counts.canonicalTrials} · Verified current phases: {installation.counts.phaseVerifiedTrials} / {installation.counts.canonicalTrials}<br />
        Recorded current-phase grades: {installation.counts.recordedCurrentPhaseGrades} · Excluded methods: {installation.counts.excludedMethods} · Pending observed methods: {installation.counts.pendingObservedMethods} · Unobserved positions: {installation.counts.unobservedMethodPositions}<br />
        Historical review events: {installation.counts.historicalReviewEvents} · Recorded gap events: {installation.counts.recordedGapEvents} · Independently signed clinical reviews: {quantity(installation.counts.independentlySignedClinicalReviews)}</p> : <p>Ledger counts are unavailable.</p>}
      <details style={panel}><summary>Installation tasks and unresolved dependencies · {installation.tasks.length} observed</summary>
        {installation.tasks.map(task => <article key={task.id} style={panel}>
          <strong>{task.id} · {task.title} · {task.status}</strong>
          <p>Completed: {quantity(task.completed)} · Remaining: {quantity(task.remaining)}</p>
          {task.dependency ? <p>Dependency: {task.dependency}</p> : null}
          <p>Evidence: {task.evidence}</p>
        </article>)}
      </details>
      <details style={panel}><summary>Status definitions, source freshness and evidence expiry</summary>
        <dl>{Object.entries(installation.definitions).map(([term, meaning]) => <div key={term}><dt><strong>{term}</strong></dt><dd>{meaning}</dd></div>)}</dl>
        {installation.sourceCollectionDates ? <p>Oldest source collection: {installation.sourceCollectionDates.oldest ?? "Unknown"} · Newest source collection: {installation.sourceCollectionDates.newest ?? "Unknown"} · Freshness validation: {installation.sourceCollectionDates.freshnessValidation}</p> : null}
      </details>
      <p>APPROVAL: ABSTAIN · CRL: ABSTAIN · REVIEW_DELAY: ABSTAIN · CERTAINTY: NOT_VALIDATED</p>
    </div> : null}
  </section>;
}
