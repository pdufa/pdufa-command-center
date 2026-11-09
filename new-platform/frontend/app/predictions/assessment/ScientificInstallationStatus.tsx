"use client";
import {useEffect, useRef, useState} from "react";
import {MAIN_RESEARCH_CHECKPOINT, researchCheckpointEvidenceUrl,
  type MedicalInstallationSnapshot} from "../../../lib/medical-installation-status";

const panel = {border: "1px solid #a8c9bc", borderRadius: 9, padding: 14, margin: "12px 0"} as const;
const quantity = (value: number | null) => value === null ? "Not verified" : String(value);
export default function ScientificInstallationStatus() {
  const [snapshot, setSnapshot] = useState<MedicalInstallationSnapshot | null>(null);
  const [error, setError] = useState("");
  const tasksSection = useRef<HTMLDetailsElement>(null);
  const researchSection = useRef<HTMLDetailsElement>(null);
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
  function locateCurrentTask() {
    if (!current || !tasksSection.current) return;
    tasksSection.current.open = true;
    const target = document.getElementById("medical-installation-task-" + current.id);
    if (!target) return;
    target.focus({preventScroll: true});
    target.scrollIntoView({behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "center"});
  }
  function locateResearchTask() {
    if (!researchSection.current) return;
    researchSection.current.open = true;
    const target = document.getElementById(MAIN_RESEARCH_CHECKPOINT.currentTaskId);
    if (!target) return;
    target.focus({preventScroll: true});
    target.scrollIntoView({behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "center"});
  }
  return <section style={{...panel, background: "white"}} aria-label="MAIN scientific installation status">
    <h3>MAIN scientific installation status</h3>
    <p>Progress follows the current task and observed ledger counts. Methodology positions and retrieved sources do not count as independently graded scientific tests.</p>
    <div style={{...panel, background: "#102e45", color: "#d5f6f0", overflowWrap: "anywhere"}}
      aria-label="Dated Revision 36 source research checkpoint">
      <h4 style={{margin: "0 0 8px"}}>Revision {MAIN_RESEARCH_CHECKPOINT.revision} · ACACIA-HCM source research checkpoint</h4>
      <p>{MAIN_RESEARCH_CHECKPOINT.nct} · observed {MAIN_RESEARCH_CHECKPOINT.observedAt}<br />
        Continues commit <code>{MAIN_RESEARCH_CHECKPOINT.baseCommit}</code>.</p>
      <p>Active documentary task: <strong>{MAIN_RESEARCH_CHECKPOINT.currentTaskId}</strong>. No clinical task is advanced by this research receipt.</p>
      <p>{MAIN_RESEARCH_CHECKPOINT.candidateMethodPositions} existing source-lead positions · {MAIN_RESEARCH_CHECKPOINT.unexaminedMethodPositions} unexamined positions · {MAIN_RESEARCH_CHECKPOINT.officialMethodGrades}/800 official method grades. No new independently completed assessments.</p>
      <button type="button" onClick={locateResearchTask} aria-label="Locate Revision 36 source task"
        style={{minHeight: 44, padding: "10px 14px", border: "1px solid #75cbbc", borderRadius: 8,
          background: "#164451", color: "#d5f6f0", fontWeight: 750}}>Locate active source task</button>
      <details ref={researchSection} style={{marginTop: 12}}>
        <summary style={{cursor: "pointer", minHeight: 44}}>Completed documentary checks, active work and dependencies</summary>
        {MAIN_RESEARCH_CHECKPOINT.tasks.map(task => <div key={task.id} id={task.id} tabIndex={-1}
          aria-current={task.id === MAIN_RESEARCH_CHECKPOINT.currentTaskId ? "step" : undefined}
          style={{borderTop: "1px solid #477079", padding: "12px 0", scrollMarginTop: 24}}>
          <strong>{task.id} · {task.status} · {task.title}</strong>
          <p>{task.acceptance}</p>
          {task.evidencePath ? <a href={researchCheckpointEvidenceUrl(task.evidencePath)} target="_blank"
            rel="noopener noreferrer" style={{color: "#a6f0e5"}}>Inspect acceptance evidence and limitations</a> : null}
        </div>)}
      </details>
      <details style={{marginTop: 12}}><summary style={{cursor: "pointer", minHeight: 44}}>What this checkpoint verifies and when evidence expires</summary>
        <p>VERIFIED refers only to the named documentary acceptance condition. ACTIVE means source investigation remains in progress. BLOCKED identifies an unmet review or evidence dependency. PENDING means the acceptance observation has not been recorded.</p>
        <p>Registry submission dates and public posting dates have different meanings. Source retrieval dates do not renew evidence validity. A later registry update or conflicting source requires another traceable examination; no universal expiry or automatic grade renewal is assumed.</p>
        <p>This dated checkpoint preserves the prior failed-access receipts and does not replace live deployment, PostgreSQL or assessment-ledger observations below.</p>
      </details>
      <p>APPROVAL: ABSTAIN · CRL: ABSTAIN · REVIEW_DELAY: ABSTAIN · CERTAINTY: NOT_VALIDATED · ACCURACY: NOT_CALIBRATED</p>
    </div>
    <button type="button" onClick={locateCurrentTask} disabled={!current} aria-label="Locate current installation task"
      style={{minHeight: 44, padding: "10px 14px", border: "1px solid #287a80", borderRadius: 8,
        background: current ? "#102e45" : "#e5ecef", color: current ? "#a6f0e5" : "#52646c", fontWeight: 750}}>
      Locate current installation task
    </button>
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
      <details ref={tasksSection} style={panel}><summary>Installation tasks and unresolved dependencies · {installation.tasks.length} observed</summary>
        {installation.tasks.map(task => <article key={task.id} id={"medical-installation-task-" + task.id}
          tabIndex={-1} aria-current={task.id === installation.currentTaskId ? "step" : undefined}
          style={{...panel, scrollMarginTop: 24, overflowWrap: "anywhere",
            borderColor: task.id === installation.currentTaskId ? "#287a80" : "#a8c9bc"}}>
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
