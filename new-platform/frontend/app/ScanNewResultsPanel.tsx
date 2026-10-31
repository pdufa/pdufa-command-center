"use client";

import type { NewFromScanRow, NewFromScanSummary } from "../lib/scan-new-results";

function shown(n: number | null) {
  return n === null ? "—" : n.toLocaleString("en-US");
}
function category(row: NewFromScanRow) {
  return row.kind === "NEW_PROGRAM" ? "NEW MASTER PROGRAM" :
    row.kind === "NEW_PHASE3_RESULT" ? "NEW PHASE 3 RESULT" :
    "NEW SAVED CANDIDATE";
}

export default function ScanNewResultsPanel({
  summary,
  loading = false,
}: {
  summary: NewFromScanSummary | null | undefined;
  loading?: boolean;
}) {
  const runLink = summary?.runId
    ? "https://github.com/pdufa/pdufa-command-center/actions/runs/" + summary.runId
    : null;
  const primary = [
    {key:"pipeline",label:"PIPELINE",desc:"New master programs",value:summary?.pipelineNewPrograms ?? null},
    {key:"phase3-result",label:"PHASE 3 RESULTS",desc:"New posted Phase 3 results (historic source count)",value:summary?.gemJrNewResultRecords ?? null},
  ];
  const known = summary && primary.some(x => x.value !== null);
  return <section className="scans-new-results" aria-label="New from scan — latest published additions">
    <header className="scans-new-header">
      <div>
        <span className="scans-new-eyebrow">LATEST PUBLISHED SCAN</span>
        <h3>NEW FROM SCAN</h3>
        <p>New discoveries and saved admissions are shown separately. Rechecked and updated trials are not labeled new.</p>
      </div>
      <div className="scans-new-run">
        <strong>{summary?.scanPacificDate || "Date not verified"}</strong>
        <small>{runLink ? <a href={runLink} target="_blank" rel="noopener noreferrer">GitHub scan #{summary?.runId} ↗</a> : "Scan run not verified"}</small>
      </div>
    </header>
    {loading && !summary ? <p className="scans-new-unavailable">Loading newly published scan results…</p> :
      !summary || !known ? <p className="scans-new-unavailable">New-record counts are not available from a matched published scan. No zero or candidate additions are inferred.</p> :
      <>
        <div className="scans-new-metrics">
          {primary.map(x => <div key={x.key} className={"scans-new-metric"+(x.value !== null && x.value > 0?" scans-new-positive":"")}>
            <span className="scans-new-stage">{x.label}</span>
            <strong className="scans-new-number">{shown(x.value)}</strong>
            <span className="scans-new-description">{x.desc}</span>
            <span className="scans-new-state">{x.value === null ? "NOT VERIFIED" : x.value > 0 ? "NEW FROM SCAN" : "NO NEW ADDITIONS"}</span>
          </div>)}
        </div>
        <div className="scans-new-update-note" role="note">
          <strong>UPDATED / RECHECKED — {shown(summary.pipelineChangedTrials)} PIPELINE trials</strong>
          <span>Updates are not new candidates and are excluded from the new-addition cards.</span>
        </div>
        <div className="scans-new-detail-head">
          <h4>What was new?</h4>
          <small>Only published identifiers appear below. No ticker or trial is invented.</small>
        </div>
        {summary.rows.filter(row=>row.kind==="NEW_PROGRAM"||row.kind==="NEW_PHASE3_RESULT").length ? <div className="scans-new-table-viewport">
          <table className="scans-new-table">
            <thead><tr><th>Stage</th><th>Status</th><th>Ticker</th><th>Program / drug</th><th>Trial ID</th><th>Evidence</th></tr></thead>
            <tbody>{summary.rows.filter(row=>row.kind==="NEW_PROGRAM"||row.kind==="NEW_PHASE3_RESULT").map((row, i) => <tr key={row.stage+"|"+row.kind+"|"+(row.trialId || i)}>
              <td><strong>{row.kind==="NEW_PHASE3_RESULT"?"PHASE 3 RESULTS":"POOL"}</strong></td>
              <td><span className={"scans-new-item-badge"+(row.exactRun?"":" scans-new-date-badge")}>{category(row)}</span></td>
              <td>{row.ticker ? <strong>{row.ticker}</strong> : <em>Not published</em>}</td>
              <td>{row.drug || "Identity not published in the scan report"}</td>
              <td>{row.trialId ? <code>{row.trialId}</code> : "—"}</td>
              <td>{row.label}{row.sourceUrl && <div><a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">ClinicalTrials.gov source ↗</a></div>}</td>
            </tr>)}</tbody>
          </table>
        </div> :
          <p className="scans-new-unavailable">No individually identified new rows were published for this scan.</p>}
      </>}
    <footer className="scans-new-footer">
      <strong>Reading these numbers:</strong> New master programs and posted Phase 3 results are different measures; they can overlap and must not be added together. Counts are dated source observations and are not proof of eligibility or regulatory success.
      {summary?.warnings?.length ? <ul>{summary.warnings.map(w => <li key={w}>{w}</li>)}</ul> : null}
      <small>Collection success does not establish complete FDA, SEC, financing, market, or clinical-source verification or trading eligibility.</small>
    </footer>
  </section>;
}
