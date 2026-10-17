"use client";

import { useEffect, useState } from "react";

type SourceRow = {
  source?: string; status?: string; findings_due?: number; findings_verified?: number;
  findings_not_applicable?: number; required_findings_unresolved?: number;
  optional_findings_unavailable?: number;
};
type Report = {
  status?: string;
  clinical?: { latest_run_id?: number; updated_at_utc?: string; scans?: Array<{
    scan?: string; label?: string; collector_status?: string; metrics?: Record<string, number>;
  }> } | null;
  sources?: { updated_at_utc?: string; latest_run_id?: number; status?: string;
    findings_due?: number; findings_verified?: number; findings_not_applicable?: number;
    required_findings_unresolved?: number; sources?: SourceRow[];
    missing_required_source_families?: string[];
  } | null;
  gem?: { generated_at_utc?: string; status?: string; observed_phase3_rows?: number;
    two_benchmark_candidate_count?: number; strict_entry_gate_shortlist_count?: number;
    blocking_or_review_flags?: string[];
  } | null;
};

type ScanAction = "VERIFY_ALL" | "REVERIFY_PARTIAL" | "RESCAN_ALL";
type ScanTarget = "ALL" | "PIPELINE" | "GEM_JR" | "GEM";
type ActionRun = { id: number; status: string; conclusion: string | null; created_at: string; html_url: string };
type ControlStatus = { dispatchEnabled: boolean; manual?: ActionRun[]; overnight?: ActionRun[]; error?: string };

function value(v?: number | string) { return v === undefined || v === null ? "Not reported" : typeof v === "number" ? v.toLocaleString("en-US") : v; }
function score(due?: number, verified?: number, na?: number) {
  if (!Number.isFinite(due) || !due || due <= 0 || !Number.isFinite(verified) || verified == null || verified < 0) return null;
  const cleared = verified + (na || 0);
  return cleared < 0 || cleared > due ? null : Math.round((cleared / due) * 1000) / 10;
}
const SCAN_WORKFLOW = "https://github.com/pdufa/pdufa-command-center/actions/workflows/pdufa-scan-control.yml";

export default function PublishedScansPanel() {
  const [record, setRecord] = useState<Report | null>(null);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    const ctrl = new AbortController();
    fetch("/api/published-scans", { cache:"no-store", signal: ctrl.signal })
      .then(async r => { if (!r.ok) throw Error("Published scan reports unavailable (" + r.status + ")"); return r.json(); })
      .then((x: Report) => { if (!ctrl.signal.aborted) { setRecord(x); setError(""); } })
      .catch(e => { if (!ctrl.signal.aborted) { setError(String(e)); } });
    return () => ctrl.abort();
  }, [refresh]);
  const [action, setAction] = useState<ScanAction>("REVERIFY_PARTIAL");
  const [target, setTarget] = useState<ScanTarget>("ALL");
  const [runs, setRuns] = useState<ControlStatus | null>(null);
  const [runError, setRunError] = useState("");
  const [scanMessage, setScanMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [scanRefresh, setScanRefresh] = useState(0);
  useEffect(() => {
    const ctrl = new AbortController();
    fetch("/api/scans/control", { cache: "no-store", signal: ctrl.signal })
      .then(async response => {
        const data: ControlStatus = await response.json();
        if (!response.ok) throw new Error(data.error || "Scan status unavailable");
        return data;
      })
      .then(data => { if (!ctrl.signal.aborted) { setRuns(data); setRunError(""); } })
      .catch(() => { if (!ctrl.signal.aborted) { setRunError("Live GitHub run status unavailable"); } });
    return () => ctrl.abort();
  }, [scanRefresh]);

  async function requestScan() {
    setSending(true);
    setScanMessage("");
    try {
      const response = await fetch("/api/scans/control", {
        method: "POST", cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, scan: target }),
      });
      const data: { message?: string; error?: string } = await response.json();
      setScanMessage(response.ok && data.message ? data.message :
        data.error || "Scan request not confirmed");
      setScanRefresh(x => x + 1);
    } catch {
      setScanMessage("Unable to confirm a new scan request. Check GitHub Actions before retrying.");
    } finally {
      setSending(false);
    }
  }

  const sources = record?.sources;
  return <section className="panel">
    <h2>SCANS — Published source scores and outstanding evidence</h2>
    <p className="subtle">This staging platform reads original Streamlit scan reports independently of the database. It reads original scan reports and, when a server-only GitHub token is configured, can dispatch the existing scanners. It does not operate a duplicate schedule, generate substitute program IDs, or send orders.</p>
    <p><a href={SCAN_WORKFLOW} target="_blank" rel="noopener noreferrer">OPEN EXISTING GITHUB SCAN RUN CONTROLS ↗</a></p>
    <button type="button" className="secondary" onClick={()=>setRefresh(x=>x+1)}>REFRESH PUBLISHED SCAN STATUS</button>
    <div className="source-health">
      <strong>Run existing scanners from this dashboard</strong>
      <p className="subtle">Manual commands use the original GitHub Actions workflows; the only automated schedule remains the original 10 PM Pacific chain. An accepted request is not a completed scan.</p>
      <div style={{display:"flex", flexWrap:"wrap", alignItems:"end", gap:"0.6rem"}}>
        <label>Action
          <select value={action} onChange={e => setAction(e.target.value as ScanAction)}>
            <option value="REVERIFY_PARTIAL">Reverify partial — incremental</option>
            <option value="VERIFY_ALL">Verify saved evidence</option>
            <option value="RESCAN_ALL">Rescan all — full collection</option>
          </select>
        </label>
        <label>Stage
          <select value={target} onChange={e => setTarget(e.target.value as ScanTarget)}>
            <option value="ALL">ALL — sequential including GEM</option>
            <option value="PIPELINE">PIPELINE only</option>
            <option value="GEM_JR">GEM JR only</option>
            <option value="GEM">GEM only</option>
          </select>
        </label>
        <button type="button" onClick={requestScan} disabled={sending || !runs?.dispatchEnabled}>
          {sending ? "REQUESTING…" : "START SELECTED SCAN"}
        </button>
        <button type="button" className="secondary" onClick={() => setScanRefresh(x => x + 1)}>REFRESH RUN STATUS</button>
      </div>
      {runs && !runs.dispatchEnabled && <p className="subtle">The SCANS page is installed, but its START button is disabled until PDUFA_GITHUB_TOKEN is saved as a server-only Vercel environment variable (fine-grained GitHub token with Actions read/write on this repository), followed by a redeploy. In the meantime, use the linked GitHub Actions workflow → Run workflow. Existing nightly scans continue independently.</p>}
      {runError && <p className="risk-line">{runError}</p>}
      {scanMessage && <p role="status">{scanMessage}</p>}
      {runs?.manual?.[0] && <p className="subtle">Last manual control: <a href={runs.manual[0].html_url} target="_blank" rel="noopener noreferrer">run #{runs.manual[0].id}</a> — {runs.manual[0].status} / {runs.manual[0].conclusion || "not concluded"}.</p>}
      {runs?.overnight?.[0] && <p className="subtle">Last full overnight chain: <a href={runs.overnight[0].html_url} target="_blank" rel="noopener noreferrer">run #{runs.overnight[0].id}</a> — {runs.overnight[0].status} / {runs.overnight[0].conclusion || "not concluded"}.</p>}
    </div>
    {error && <p className="risk-line">{error}</p>}
    {!record && !error && <p className="subtle">Loading original published scan reports…</p>}
    {record && <>
      <p className="subtle">Report coverage: {value(record.status)} · Evidence updated {value(sources?.updated_at_utc)} · Source workflow #{value(sources?.latest_run_id)}. These scores do not indicate investment or FDA-approval probability.</p>
      <div className="source-health">
        <strong>Five-source audit: {value(sources?.status)}</strong>
        <span>{value(sources?.findings_verified)} findings verified / {value(sources?.findings_due)} examined; {value(sources?.required_findings_unresolved)} required findings unresolved.</span>
      </div>
      {(record.clinical?.scans || []).map(scan => {
        const m = scan.metrics || {};
        const pipeline = scan.scan === "2";
        const code = scan.scan === "2" ? "PIPELINE — inventory" : scan.scan === "3" ? "PIPELINE — enrichment" : "GEM JR";
        const pct = pipeline ? score(m.tracked_trials_total, m.tracked_trials_checked) : null;
        return <details key={scan.scan} className="nested-expander">
          <summary>{code} · {pct == null ? "Score N/A — no validated denominator" : pct.toFixed(1)+"% tracked ID coverage"} · {value(scan.collector_status)}</summary>
          <p>Examined: {value(pipeline ? m.tracked_trials_checked : m.studies_checked)} · {pipeline ? "Tracked trial IDs due: "+value(m.tracked_trials_total) : scan.scan === "3" ? "Matched trial records: "+value(m.matched_trials) : "Matched posted results: "+value(m.matched_posted_results)}.</p>
          <p className="subtle">Why not 100% full verification? Clinical collector completeness does not certify SEC financing, FDA, market, or issuer claims. For non-inventory stages, no complete qualifying denominator has been published.</p>
        </details>;
      })}
      {record.gem && <details className="nested-expander">
        <summary>GEM · Qualification score N/A — baseline incomplete · {value(record.gem.status)}</summary>
        <p>Phase 3 research rows: {value(record.gem.observed_phase3_rows)} · Potential two-benchmark candidates: {value(record.gem.two_benchmark_candidate_count)} · Cleared strict entry gate: {value(record.gem.strict_entry_gate_shortlist_count)}</p>
        <p>Why not 100%? Unverified financing and readouts plus source limitations prevent a defensible scan-coverage denominator. Entry candidates passing the strict gate are not a scan-success percentage.</p>
        {(record.gem.blocking_or_review_flags || []).map(flag=><p key={flag}>{flag}</p>)}
      </details>}
      {(sources?.sources || []).map(s => {
        const pct = score(s.findings_due, s.findings_verified, s.findings_not_applicable);
        const missing = s.findings_due === undefined || s.findings_verified === undefined ? null : Math.max(0,s.findings_due - s.findings_verified - (s.findings_not_applicable || 0));
        return <details className="nested-expander" key={s.source}>
          <summary>{value(s.source)} · {pct == null ? "Score N/A" : pct.toFixed(1)+"% resolved"} · {value(s.status)}</summary>
          <p>Verified: {value(s.findings_verified)} · Not applicable: {value(s.findings_not_applicable || 0)} · Examined: {value(s.findings_due)} · Outstanding: {value(missing ?? undefined)}.</p>
          <p><strong>Why not 100%?</strong> Required outstanding: {value(s.required_findings_unresolved || 0)}. Supplemental unavailable: {value(s.optional_findings_unavailable || 0)}. Where the denominator is fully resolved, 100% only covers reported checks, not the broader research universe.</p>
        </details>;
      })}
      <p className="subtle">If the new platform's persistent database is unavailable, source reports can remain readable here while saved checklists, program IDs, and other database-dependent operations stay blocked to prevent data loss.</p>
    </>}
  </section>;
}
