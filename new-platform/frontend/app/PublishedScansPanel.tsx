"use client";

import { useEffect, useState } from "react";
import VerificationLedgerPanel from "./VerificationLedgerPanel";
import LiveScansProgress from "./LiveScansProgress";
import ScoringInputGapsPanel from "./ScoringInputGapsPanel";
import ScanNewResultsPanel from "./ScanNewResultsPanel";
import type { NewFromScanSummary } from "../lib/scan-new-results";

type SourceRow = {
  source?: string; status?: string; findings_due?: number; findings_verified?: number;
  findings_not_applicable?: number; required_findings_unresolved?: number;
  optional_findings_unavailable?: number;
};
type Report = {
  status?: string;
  newFromScan?: NewFromScanSummary;
  scoring?: unknown;
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
type ScanTarget = "ALL" | "PIPELINE" | "PHASE3_RESULTS";
type ActionRun = { id: number; status: string; conclusion: string | null; created_at: string; html_url: string };
type ControlStatus = { dispatchEnabled: boolean; manual?: ActionRun[]; overnight?: ActionRun[]; gmail?: ActionRun[]; gmailRepair?: ActionRun[]; error?: string };

function value(v?: number | string) { return v === undefined || v === null ? "Not reported" : typeof v === "number" ? v.toLocaleString("en-US") : v; }
function score(due?: number, verified?: number, na?: number) {
  if (!Number.isFinite(due) || !due || due <= 0 || !Number.isFinite(verified) || verified == null || verified < 0) return null;
  const cleared = verified + (na || 0);
  return cleared < 0 || cleared > due ? null : Math.round((cleared / due) * 1000) / 10;
}
const SCAN_WORKFLOW = "https://github.com/pdufa/pdufa-command-center/actions/workflows/pdufa-scan-control.yml";
const GMAIL_WORKFLOW = "https://github.com/pdufa/pdufa-command-center/actions/workflows/pdufa-gmail-section-audit.yml";
const GMAIL_REPAIR_WORKFLOW = "https://github.com/pdufa/pdufa-command-center/actions/workflows/pdufa-gmail-repair-cleanup.yml";
const GMAIL_SECTIONS: [string, string][] = [
  ["INBOX", "Inbox"], ["SENT_MAIL", "Sent mail"], ["PDUFA", "PDUFA label"],
  ["SCAN_START", "PDUFA / Scan START"], ["SCAN_END", "PDUFA / Scan END"],
  ["SCAN_ERROR", "PDUFA / Scan ERROR"], ["DAILY_REPORT", "PDUFA / Daily Report"],
  ["WEEKLY_REPORT", "PDUFA / Weekly Report"]
];

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
  const [refreshingRuns, setRefreshingRuns] = useState(true);
  const [runFeedback, setRunFeedback] = useState("Checking GitHub Actions connection…");
  const [scanMessage, setScanMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [scanRefresh, setScanRefresh] = useState(0);
  const [gmailSection, setGmailSection] = useState("INBOX");
  const [gmailMessage, setGmailMessage] = useState("");
  const [gmailSending, setGmailSending] = useState(false);
  useEffect(() => {
    const ctrl = new AbortController();
    setRefreshingRuns(true);
    setRunFeedback("Checking GitHub Actions connection…");
    fetch("/api/scans/control", { cache: "no-store", signal: ctrl.signal })
      .then(async response => {
        const data: ControlStatus = await response.json();
        if (!response.ok) throw new Error(data.error || "Scan status unavailable");
        return data;
      })
      .then(data => {
        if (ctrl.signal.aborted) return;
        setRuns(data);
        setRunError("");
        const checkedAt = new Date().toLocaleTimeString();
        setRunFeedback(
          "GitHub Actions status refreshed at " + checkedAt + ". " +
          (data.dispatchEnabled
            ? "Dashboard token detected. GitHub run listing works; scan launching has not been tested."
            : "No dashboard dispatch token detected. Manual GitHub controls remain available.")
        );
      })
      .catch(error => {
        if (ctrl.signal.aborted) return;
        setRuns(null);
        setRunError("Live GitHub run status unavailable");
        setRunFeedback(
          "GitHub status check failed at " + new Date().toLocaleTimeString() +
          ": " + String(error instanceof Error ? error.message : error) +
          ". No scan was started."
        );
      })
      .finally(() => { if (!ctrl.signal.aborted) setRefreshingRuns(false); });
    return () => ctrl.abort();
  }, [scanRefresh]);

  // No GitHub token on Vercel? Preserve a usable, honest operator path.
  // GitHub itself requires the signed-in repository owner to confirm the workflow.
  function openGitHubScan() {
    setScanMessage(
      "GitHub Actions opened. Sign in if prompted, choose Run workflow on branch main, then set action to " +
      action + " and scan to " + target +
      ". Press Run workflow in GitHub to actually start the scan. No scan was started from this page."
    );
    window.open(SCAN_WORKFLOW, "_blank", "noopener,noreferrer");
  }

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

  async function checkGmail(section: string, repairAndTrash = false) {
    setGmailMessage("");
    const workflow = repairAndTrash ? GMAIL_REPAIR_WORKFLOW : GMAIL_WORKFLOW;
    if (!runs?.dispatchEnabled) {
      setGmailMessage(
        "Opened the " + (repairAndTrash ? "guarded repair + resolved-email Trash" : "read-only audit") +
        " workflow in GitHub. Choose branch main, section " + section +
        ", then press Run workflow. No action has started from this page."
      );
      window.open(workflow, "_blank", "noopener,noreferrer");
      return;
    }
    setGmailSending(true);
    try {
      const response = await fetch("/api/scans/control", {
        method: "POST", cache:"no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: repairAndTrash ? "GMAIL_REPAIR_CLEANUP" : "GMAIL_AUDIT", section }),
      });
      const reply: { message?: string; error?: string } = await response.json();
      setGmailMessage(response.ok ? reply.message || "Gmail request accepted; not yet completed" :
        reply.error || "Gmail audit was not started");
      setScanRefresh(n => n + 1);
    } catch {
      setGmailMessage("Could not confirm Gmail check. Inspect GitHub Actions before trying again.");
    } finally { setGmailSending(false); }
  }

  const sources = record?.sources;
  return <section className="panel scans-page">
    <h2>SCANS — Published source scores and outstanding evidence</h2>
    <p className="subtle">This dashboard reads the original published GitHub scan reports independently of the database. With server-side GitHub authorization, it can directly dispatch the existing scanners; otherwise it opens GitHub's own manual run form. It does not operate a duplicate schedule, generate substitute program IDs, or send orders.</p>
    <p><a href={SCAN_WORKFLOW} target="_blank" rel="noopener noreferrer">OPEN EXISTING GITHUB SCAN RUN CONTROLS ↗</a></p>
    <button type="button" className="secondary" onClick={()=>setRefresh(x=>x+1)}>REFRESH PUBLISHED SCAN STATUS</button>
    <ScanNewResultsPanel summary={record?.newFromScan} loading={!record && !error} />
    {record && <ScoringInputGapsPanel report={record.scoring} />}
    <LiveScansProgress />
    <div className="scans-actions-grid">
    <div className="source-health">
      <strong>Run existing scanners from this dashboard</strong>
      <p className="subtle">Manual commands use the original GitHub Actions workflows; the automatic nightly scan is scheduled for 8 PM Pacific. An accepted request is not a completed scan.</p>
      <div style={{display:"flex", flexWrap:"wrap", alignItems:"end", gap:"0.6rem"}}>
        <label>Action
          <select value={action} onChange={e => setAction(e.target.value as ScanAction)}>
            <option value="REVERIFY_PARTIAL">Reverify partial — incremental</option>
            <option value="VERIFY_ALL">Verify saved evidence</option>
            <option value="RESCAN_ALL">Rescan all — full collection</option>
          </select>
        </label>
        <label htmlFor="pdufa-scan-target">Stage
          <select id="pdufa-scan-target" value={target} onChange={e => setTarget(e.target.value as ScanTarget)}>
            <option value="ALL">ALL — POOL, PIPELINE, Phase 3 results</option>
            <option value="PIPELINE">PIPELINE only</option>
            <option value="PHASE3_RESULTS">Phase 3 results only</option>
          </select>
        </label>
        <button type="button"
          onClick={runs?.dispatchEnabled ? requestScan : openGitHubScan}
          disabled={sending}
          title={runs?.dispatchEnabled ? "Request a scan through GitHub Actions" : "Open the existing GitHub Actions scan form"}>
          {sending ? "REQUESTING…" : runs?.dispatchEnabled ? "START SELECTED SCAN" : "OPEN GITHUB TO RUN SCAN ↗"}
        </button>
        <button type="button" className="secondary" disabled={refreshingRuns} onClick={() => setScanRefresh(x => x + 1)}>{refreshingRuns ? "CHECKING GITHUB…" : "REFRESH RUN STATUS"}</button>
      </div>
      <p className="subtle" role="status" aria-live="polite">{runFeedback}</p>
      {!runs?.dispatchEnabled && <p className="subtle">Direct dispatch from Vercel is not yet authorized. The primary button opens GitHub's authenticated Run workflow form; select branch <strong>main</strong>, action <strong>{action}</strong>, and scan <strong>{target}</strong>, then confirm Run workflow. To enable true one-click launch here, privately add server-only <code>PDUFA_GITHUB_TOKEN</code> in the Vercel Production environment and redeploy. The existing GitHub 9 PM Pacific scheduler remains independent of manual controls.</p>}
      {runError && <p className="risk-line">{runError}</p>}
      {scanMessage && <p role="status">{scanMessage}</p>}
      {runs?.manual?.[0] && <p className="subtle">Last manual control: <a href={runs.manual[0].html_url} target="_blank" rel="noopener noreferrer">run #{runs.manual[0].id}</a> — {runs.manual[0].status} / {runs.manual[0].conclusion || "not concluded"}.</p>}
      {runs?.overnight?.[0] && <p className="subtle">Last full overnight chain: <a href={runs.overnight[0].html_url} target="_blank" rel="noopener noreferrer">run #{runs.overnight[0].id}</a> — {runs.overnight[0].status} / {runs.overnight[0].conclusion || "not concluded"}.</p>}
    </div>
    <details className="source-health nested-expander" aria-label="Gmail per-section and all-email checks">
      <summary>GMAIL AUDIT — BY SECTION OR ALL EMAILS</summary>
      <p className="subtle">CHECK audits in read-only 100-message batches. FIX &amp; TRASH first inventories every section, validates exact GitHub run IDs, then processes the entire queue from most important to least. Critical items receive the limited repair attempts first.</p>
      <div className="gmail-priority-grid" aria-label="Gmail repair priorities">
        <div><strong>P1</strong><span>Overnight / POOL / PIPELINE / Phase 3</span></div>
        <div><strong>P2</strong><span>FDA / SEC / financial / source evidence</span></div>
        <div><strong>P3</strong><span>Gmail authentication and notifications</span></div>
        <div><strong>P4</strong><span>Dashboard / API / CI</span></div>
        <div><strong>P5</strong><span>Already-resolved, superseded and miscellaneous historical alerts</span></div>
      </div>
      <p className="subtle">Only approved transient workflow failures can be retried. FDA/SEC/financial evidence gaps need source verification, not automatic data changes. Emails move to Gmail Trash only when the <strong>same exact GitHub run</strong> has succeeded on a later attempt. Unresolved issues stay visible. No permanent deletion.</p>
      <div style={{display:"flex",flexWrap:"wrap",alignItems:"end",gap:"0.65rem"}}>
        <label>Gmail section
          <select value={gmailSection} onChange={e => setGmailSection(e.target.value)}>
            {GMAIL_SECTIONS.map(([value,name]) => <option key={value} value={value}>{name}</option>)}
          </select>
        </label>
        <button type="button" disabled={gmailSending} onClick={() => checkGmail(gmailSection)}>
          {gmailSending ? "REQUESTING…" : runs?.dispatchEnabled ? "CHECK SELECTED GMAIL SECTION" : "OPEN SECTION GMAIL CHECK ↗"}
        </button>
        <button type="button" disabled={gmailSending} onClick={() => checkGmail("ALL")}>
          {gmailSending ? "REQUESTING…" : runs?.dispatchEnabled ? "CHECK ALL EMAILS" : "OPEN ALL-EMAIL GMAIL CHECK ↗"}
        </button>
        <button type="button" disabled={gmailSending} onClick={() => checkGmail(gmailSection, true)}>
          {gmailSending ? "REQUESTING…" : runs?.dispatchEnabled ? "FIX ISSUES & TRASH RESOLVED — SECTION" : "OPEN FIX & TRASH SECTION ↗"}
        </button>
        <button type="button" disabled={gmailSending} onClick={() => checkGmail("ALL", true)}>
          {gmailSending ? "REQUESTING…" : runs?.dispatchEnabled ? "FIX ISSUES & TRASH RESOLVED — ALL" : "OPEN FIX & TRASH ALL ↗"}
        </button>
        <button type="button" className="secondary" onClick={() => setScanRefresh(n=>n+1)}>REFRESH GMAIL AUDIT STATUS</button>
      </div>
      {!runs?.dispatchEnabled && <p className="subtle">Without a server-side GitHub token, the check and repair buttons open their respective manual GitHub forms; sign in, choose main and the requested section, and press Run workflow. Direct one-click dispatch requires PDUFA_GITHUB_TOKEN in Vercel.</p>}
      {gmailMessage && <p role="status">{gmailMessage}</p>}
      {runs?.gmailRepair?.[0] && <p className="subtle">Latest FIX &amp; TRASH action: <a href={runs.gmailRepair[0].html_url} target="_blank" rel="noopener noreferrer">GitHub run #{runs.gmailRepair[0].id}</a> — {runs.gmailRepair[0].status} / {runs.gmailRepair[0].conclusion || "not concluded"}. Inspect the run summary to see how many were retried, confirmed resolved, or moved to Trash.</p>}
      {runs?.gmail?.[0] && <p className="subtle">Latest Gmail audit: <a href={runs.gmail[0].html_url} target="_blank" rel="noopener noreferrer">GitHub run #{runs.gmail[0].id}</a> — {runs.gmail[0].status} / {runs.gmail[0].conclusion || "not concluded"}. Open the run summary for counts or its audit artifact.</p>}
      <p><a href={GMAIL_WORKFLOW} target="_blank" rel="noopener noreferrer">OPEN READ-ONLY AUDIT HISTORY ↗</a> · <a href={GMAIL_REPAIR_WORKFLOW} target="_blank" rel="noopener noreferrer">OPEN FIX &amp; TRASH HISTORY ↗</a></p>
    </details>
    </div>
    {error && <p className="risk-line">{error}</p>}
    {!record && !error && <p className="subtle">Loading original published scan reports…</p>}
    {record && <>
      <p className="subtle">Report coverage: {value(record.status)} · Evidence updated {value(sources?.updated_at_utc)} · Source workflow #{value(sources?.latest_run_id)}. These scores do not indicate investment or FDA-approval probability.</p>
      <div className="scans-evidence-masonry">
      <div className="source-health">
        <strong>Five-source audit: {value(sources?.status)}</strong>
        <span>{value(sources?.findings_verified)} findings verified / {value(sources?.findings_due)} examined; {value(sources?.required_findings_unresolved)} required findings unresolved.</span>
      </div>
      {(record.clinical?.scans || []).map(scan => {
        const m = scan.metrics || {};
        const pipeline = scan.scan === "2";
        const code = scan.scan === "2" ? "PIPELINE — inventory" : scan.scan === "3" ? "PIPELINE — enrichment" : "PHASE3_RESULTS — posted outcomes";
        const pct = pipeline ? score(m.tracked_trials_total, m.tracked_trials_checked) : null;
        return <details key={scan.scan} className="nested-expander">
          <summary>{code} · {pct == null ? "Score N/A — no validated denominator" : pct.toFixed(1)+"% tracked ID coverage"} · {value(scan.collector_status)}</summary>
          <p>Examined: {value(pipeline ? m.tracked_trials_checked : m.studies_checked)} · {pipeline ? "Tracked trial IDs due: "+value(m.tracked_trials_total) : scan.scan === "3" ? "Matched trial records: "+value(m.matched_trials) : "Matched posted results: "+value(m.matched_posted_results)}.</p>
          <p className="subtle">Why not 100% full verification? Clinical collector completeness does not certify SEC financing, FDA, market, or issuer claims. For non-inventory stages, no complete qualifying denominator has been published.</p>
        </details>;
      })}
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
      </div>
    </>}
    <details className="nested-expander source-verification-caret">
      <summary>
        Source Verification Ledger · {typeof sources?.required_findings_unresolved === "number"
          ? `${sources.required_findings_unresolved} required findings need review`
          : "expand to inspect saved findings"}
      </summary>
      <VerificationLedgerPanel />
    </details>

  </section>;
}
