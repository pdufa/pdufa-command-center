"use client";

import { useEffect, useRef, useState } from "react";
import { HEALTH_LABELS, current, overallHealth, type HealthCheck, type SiteHealthReport } from "../lib/site-health";
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
  const [open, setOpen] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    let controller: AbortController | null = null;
    async function load() {
      if (!alive) return;
      if (document.hidden) { timer = setTimeout(load, 60000); return; }
      controller = new AbortController();
      setLoading(true);
      try {
        const response = await fetch("/api/site-health", { cache: "no-store",
          signal: AbortSignal.any([controller.signal, AbortSignal.timeout(25000)]) });
        const data = await response.json();
        if (!response.ok || !data || !Array.isArray(data.checks) || !data.checkedAt ||
            data.checks.length < 10 || !data.checks.every((check: HealthCheck) =>
              check && typeof check.id === "string" && Object.hasOwn(STATES, check.state) &&
              typeof check.label === "string" && typeof check.detail === "string" && typeof check.summary === "string")) {
          throw new Error("Site health could not be verified");
        }
        if (alive) { setReport(data); setError(""); setClock(Date.now()); }
      } catch {
        if (alive) { setReport(null); setError("Health check unavailable. Open the details or try again."); }
      } finally {
        if (alive) { setLoading(false); timer = setTimeout(load, 60000); }
      }
    }
    void load();
    const tick = setInterval(() => setClock(Date.now()), 30000);
    return () => { alive = false; clearTimeout(timer); clearInterval(tick); controller?.abort(); };
  }, [refresh]);

  const stale = report && !current(report.checkedAt, clock || Date.now(), 2 / 60);
  const checks = stale ? report.checks.map(check => ({ ...check,
    state: check.state === "failed" ? "failed" as const : "unknown" as const,
    summary: "Refresh required · " + check.summary })) : report?.checks || UNVERIFIED_CHECKS;
  const state = overallHealth(checks);
  const label = !report && loading ? "Checking…" : HEALTH_LABELS[state];
  return <>
    <button type="button" className={`${styles.trigger} ${styles[state]}`}
      aria-haspopup="dialog" aria-expanded={open} aria-controls="site-health-dialog"
      onClick={() => { dialog.current?.showModal(); setOpen(true); }}>
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
        <span>{checks.filter(check => check.state === "good").length}/{checks.length || 10} checks passed</span>
      </div>
      <p className={styles.explanation}>Green: all checks pass. Yellow: review or incomplete verification. Red: a failed check. Gray: unverified.</p>
      {error && <p role="alert" className={styles.error}>{error}</p>}
      {stale && <p role="alert" className={styles.error}>This display is out of date. Refresh to verify current health.</p>}
      <div className={styles.checks}>{checks.map(check => <details key={check.id} className={styles.check}>
        <summary><span className={`${styles.dot} ${styles[check.state]}`} aria-hidden="true" />
          <span className={styles.checkLabel}>{check.label}</span>
          <span className={styles.checkValue}>{check.summary}<small>{STATES[check.state]}</small></span>
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
