"use client";

import { useEffect, useRef, useState } from "react";
import { HEALTH_LABELS, overallHealth, type HealthCheck, type SiteHealthReport } from "../lib/site-health";
import styles from "./SiteHealthStatus.module.css";

function when(value: string | null) {
  return value ? new Date(value).toLocaleString("en-US", { timeZone: "America/Los_Angeles",
    month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short" }) : "Not checked";
}
const STATES = { good: "Good", warning: "Needs review", failed: "Failed", unknown: "Unverified" };
const UNVERIFIED_CHECKS: HealthCheck[] = [
  ["website", "Website & sign-in"], ["deployment", "Deployment"], ["backend", "Backend & database"],
  ["lists", "PIPELINE · GEM JR · GEM"], ["scans", "Clinical scan collection"],
  ["sources", "Source verification"], ["scoring", "Scoring data"],
  ["controls", "Restrictions, buttons & popups"], ["screens", "iPhone & desktop display"],
  ["email", "PDUFA email count"],
].map(([id, label]) => ({ id, label, state: "unknown", summary: id === "email" ? "Count unavailable" : "Unverified",
  detail: "No current verified result is available. Refresh status to try again.", checkedAt: null }));

export default function SiteHealthStatus() {
  const [report, setReport] = useState<SiteHealthReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [clock, setClock] = useState(0);
  const [receivedAt, setReceivedAt] = useState(0);
  const [open, setOpen] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    let watchdog: ReturnType<typeof setTimeout>;
    let controller: AbortController | null = null;
    let inFlight = false;
    async function load() {
      if (!alive || inFlight) return;
      if (document.hidden) { timer = setTimeout(load, 60000); return; }
      clearTimeout(timer);
      const requestController = new AbortController();
      controller = requestController;
      inFlight = true;
      watchdog = setTimeout(() => requestController.abort(), 25000);
      setLoading(true);
      try {
        const response = await fetch("/api/site-health", { cache: "no-store",
          signal: requestController.signal });
        if (response.status === 401) throw new Error("Sign-in expired. Reload the dashboard and sign in again.");
        if (!response.ok) throw new Error("Health service returned HTTP " + response.status + ". Tap Refresh status to try again.");
        const data = await response.json();
        if (!response.ok || !data || !Array.isArray(data.checks) || !data.checkedAt ||
            data.checks.length < 10 || !data.checks.every((check: HealthCheck) =>
              check && typeof check.id === "string" && Object.prototype.hasOwnProperty.call(STATES, check.state) &&
              typeof check.label === "string" && typeof check.detail === "string" && typeof check.summary === "string")) {
          throw new Error("Site health could not be verified");
        }
        if (alive) { const time = Date.now(); setReport(data); setError(""); setClock(time); setReceivedAt(time); }
      } catch (cause) {
        if (alive) { setError(requestController.signal.aborted
          ? "Health check timed out. Tap Refresh status to try again."
          : cause instanceof Error ? cause.message : "Health check unavailable. Tap Refresh status to try again."); }
      } finally {
        clearTimeout(watchdog);
        inFlight = false;
        if (alive) { setLoading(false); timer = setTimeout(load, 60000); }
      }
    }
    const resume = () => { if (!document.hidden) { clearTimeout(timer); void load(); } };
    document.addEventListener("visibilitychange", resume);
    window.addEventListener("focus", resume);
    void load();
    const tick = setInterval(() => setClock(Date.now()), 30000);
    return () => { alive = false; clearTimeout(timer); clearTimeout(watchdog); clearInterval(tick); controller?.abort();
      document.removeEventListener("visibilitychange", resume); window.removeEventListener("focus", resume); };
  }, [refresh]);

  // Use elapsed client time, so a device clock differing from the server cannot
  // turn a freshly received report into ten unverified checks.
  const stale = !!report && (!!error || (receivedAt > 0 && (clock || Date.now()) - receivedAt > 120000));
  const pending = loading && !report;
  const checks = stale ? report.checks.map(check => ({ ...check,
    state: check.state === "failed" ? "failed" as const : "unknown" as const,
    summary: "Last verified · refresh required · " + check.summary })) : report?.checks || (pending ? UNVERIFIED_CHECKS.map(check => ({
      ...check, summary: "Checking…", detail: "Waiting for the live health checks to return.",
    })) : UNVERIFIED_CHECKS);
  const state = overallHealth(checks);
  const label = !report && loading ? "Checking…" : HEALTH_LABELS[state];
  return <>
    <button type="button" className={`${styles.trigger} ${styles[state]}`}
      aria-haspopup="dialog" aria-expanded={open} aria-controls="site-health-dialog"
      onClick={() => { dialog.current?.showModal(); setOpen(true); if (!loading) setRefresh(value => value + 1); }}>
      <span className={styles.dot} aria-hidden="true" />
      <span><strong>SITE HEALTH</strong><span className={styles.triggerLabel} aria-live="polite">{label}</span></span>
      <span aria-hidden="true">▾</span>
    </button>
    <dialog ref={dialog} id="site-health-dialog" className={styles.dialog}
      aria-labelledby="site-health-title" onClose={() => setOpen(false)}
      onClick={event => { if (event.target === event.currentTarget) dialog.current?.close(); }}>
      <div className={styles.dialogHeader}>
        <div><h2 id="site-health-title">Site health</h2><p>All site checks in one place</p></div>
        <button type="button" className="secondary" onClick={() => dialog.current?.close()} autoFocus>Close ×</button>
      </div>
      <div className={`${styles.overall} ${styles[state]}`} role="status">
        <span className={styles.dot} aria-hidden="true" /><strong>{label}</strong>
        <span>{pending ? "Checking 10 items…" : `${checks.filter(check => check.state === "good").length}/${checks.length || 10} checks passed`}</span>
      </div>
      <p className={styles.explanation}>Green: all checks pass. Yellow: review or incomplete verification. Red: a failed check. Gray: unverified.</p>
      {error && <p role="alert" className={styles.error}>{error}</p>}
      {stale && <p role="alert" className={styles.error}>This display is out of date. Refresh to verify current health.</p>}
      <div className={styles.checks}>{checks.map(check => <details key={check.id} className={styles.check}>
        <summary><span className={`${styles.dot} ${styles[check.state]}`} aria-hidden="true" />
          <span className={styles.checkLabel}>{check.label}</span>
          <span className={styles.checkValue}>{check.summary}<small>{pending ? "Checking" : STATES[check.state]}</small></span>
          <span aria-hidden="true">⌄</span>
        </summary>
        <p>{check.detail}</p><p className={styles.checkedAt}>Checked: {when(check.checkedAt)}</p>
      </details>)}</div>
      <div className={styles.dialogFooter}>
        <span>Last health check: {when(report?.checkedAt || null)}<br />Updates every minute while this page is visible.</span>
        <button type="button" className="secondary" disabled={loading} onClick={() => setRefresh(value => value + 1)}>{loading ? "Checking…" : "Refresh status"}</button>
      </div>
      <p className={styles.mailNote}>Email totals are saved read-only counts with their own timestamp, refreshed after the nightly workflow. No mail is changed.</p>
    </dialog>
  </>;
}
