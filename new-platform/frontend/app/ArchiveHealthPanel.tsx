"use client";

import { useEffect, useState } from "react";
import { archiveCount, archiveLabel, archiveTime, isArchiveHealth, type ArchiveHealth } from "../lib/archive-health";

function ReportDetails({ values }: { values: Record<string, unknown> }) {
  return <dl style={{ display: "grid", gridTemplateColumns: "minmax(140px, 1fr) minmax(0, 2fr)", gap: 8 }}>
    {Object.entries(values).map(([key, value]) => <div key={key} style={{ display: "contents" }}>
      <dt>{archiveLabel(key)}</dt>
      <dd style={{ margin: 0, overflowWrap: "anywhere" }}>{value === null ? "Unverified" :
        typeof value === "object" ? JSON.stringify(value) : String(value)}</dd>
    </div>)}
  </dl>;
}

export default function ArchiveHealthPanel() {
  const [open, setOpen] = useState(false);
  const [report, setReport] = useState<ArchiveHealth | null>(null);
  const [state, setState] = useState("Expand to load the saved verification report.");
  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    setReport(null);
    setState("Loading saved archive verification…");
    fetch("/api/archive-health", { cache: "no-store", signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error(response.status === 401 ? "Sign-in expired. Sign in again." :
          "Archive report is unavailable. No counts or PASS status can be confirmed.");
        const data: unknown = await response.json();
        if (!isArchiveHealth(data)) throw new Error("Archive report is incomplete. No results inferred.");
        if (!controller.signal.aborted) { setReport(data); setState(""); }
      }).catch(error => {
        if (!controller.signal.aborted) { setReport(null); setState(String(error.message || error)); }
      });
    return () => controller.abort();
  }, [open]);

  const metrics = report ? [
    ["Archived trials", archiveCount(report.archived_trials)],
    ["Archive integrity", report.archive_integrity],
    ["Manifest verification", report.manifest_verification],
    ["Last verified", archiveTime(report.last_verified)],
    ["Next scheduled verification", archiveTime(report.next_scheduled_verification)],
    ["Scientific-ready trials (evidence screen)", archiveCount(report.scientific_ready_trials)],
    ["Trials needing additional evidence", archiveCount(report.trials_needing_additional_evidence)],
    ["Trials with regulatory outcome evidence (externally verified)", archiveCount(report.trials_with_regulatory_outcome_evidence)],
  ] : [];

  return <section className="panel" aria-label="Archive health and scientific readiness">
    <details onToggle={event => setOpen(event.currentTarget.open)}>
      <summary style={{ cursor: "pointer", fontWeight: 800 }}>ARCHIVE HEALTH &amp; SCIENTIFIC READINESS</summary>
      {state ? <p role="status">{state}</p> : null}
      {report ? <>
        <dl style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))", gap: 14 }}>
          {metrics.map(([label, value]) => <div key={label}>
            <dt className="subtle">{label}</dt><dd style={{ margin: "4px 0", fontWeight: 700 }}>{value}</dd>
          </div>)}
        </dl>
        <details><summary>Integrity and manifest checks</summary><ReportDetails values={report.checks} /></details>
        <details><summary>Scientific evidence inventory</summary>
          <div style={{ overflowX: "auto" }}><table style={{ width: "100%", textAlign: "left" }}>
            <caption>Recorded evidence in archived trials</caption>
            <thead><tr><th scope="col">Evidence</th><th scope="col">Present</th><th scope="col">Missing / insufficient</th></tr></thead>
            <tbody>{Object.entries(report.inventory).map(([key, metric]) => <tr key={key}>
              <th scope="row">{archiveLabel(key)}{report.definitions?.[key] ?
                <details style={{ fontWeight: 400 }}><summary>Definition and limits</summary><p>{report.definitions[key]}</p></details> : null}</th>
              <td>{archiveCount(metric.present)}</td><td>{archiveCount(metric.missing)}</td>
            </tr>)}</tbody>
          </table></div>
          {report.methodology ? <p className="subtle">{report.methodology}</p> : null}
          {report.scientific_readiness_scope ? <p className="subtle">{report.scientific_readiness_scope}</p> : null}
          <p className="subtle">Zero externally verified regulatory outcomes means this archive inventory has not established any against regulatory sources. It does not prove regulatory evidence is absent.</p>
        </details>
        <details><summary>Daily verification schedule</summary><ReportDetails values={report.scheduler} /></details>
        <p className="subtle">Evidence availability is a readiness inventory. SCIENCE, OUTCOME and MAIN require independent validation. Trial completion does not establish regulatory approval or trading eligibility.</p>
      </> : null}
    </details>
  </section>;
}
