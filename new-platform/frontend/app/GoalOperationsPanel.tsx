"use client";

import type { GoalScanView } from "../lib/goal-scan-evidence";
import { goalOperationalState } from "../lib/goal-operations";
import styles from "./GoalOperationsPanel.module.css";

type Props={scan:GoalScanView|null;scoring:unknown;loading:boolean;onOpenScans:()=>void};
export default function GoalOperationsPanel({scan,scoring,loading,onOpenScans}:Props) {
  const summary=goalOperationalState(scan,scoring);
  return <section className={styles.panel} aria-label="GOAL installation and evidence status">
    <div className={styles.top}>
      <div>
        <h3>Installation verification · source checks</h3>
        <p>What the actual published evidence confirms, and what still needs a working external connection.</p>
      </div>
      <button type="button" onClick={onOpenScans}>Inspect SCANS →</button>
    </div>
    <div className={styles.cards}>
      <article className={styles.card}>
        <strong>Overnight scan report</strong>
        <span className={summary.scan.concern?styles.concern:styles.neutral}>
          {loading?"Reading report…":summary.scan.label}</span>
        <p>{summary.scan.detail}</p>
        {summary.scan.url && <a href={summary.scan.url} target="_blank" rel="noopener noreferrer">Open original GitHub run ↗</a>}
      </article>
      <article className={styles.card}>
        <strong>Scoring evidence</strong>
        <span className={summary.scoring.concern?styles.concern:styles.neutral}>
          {loading?"Reading audit…":summary.scoring.label}</span>
        <p>{summary.scoring.detail}</p>
        {summary.scoring.url && <a href={summary.scoring.url} target="_blank" rel="noopener noreferrer">Open audit source run ↗</a>}
      </article>
      <article className={styles.card}>
        <strong>Independent scan recovery</strong>
        <span className={styles.neutral}>Fallback configured · execution not certified here</span>
        <p>The authenticated Vercel cron can request the guarded GitHub scan scheduler.
          Duplicate prevention protects active or already launched nightly sequences.
          It is a scan-start backup clock, not a Google Drive data backup.</p>
      </article>
      <article className={styles.card}>
        <strong>Google Drive data backup</strong>
        <span className={styles.concern}>Daily task configured · first automatic run unverified</span>
        <p>As of October 23, a separate ChatGPT task was configured to copy the PDUFA Master Scan Data
          Google Sheet daily around 8 AM Pacific. An October 23 snapshot was verified in Drive,
          but this site cannot confirm that the unattended task runs or stays enabled.
          No complete site/Git history backup or tested restore has been established.</p>
      </article>
      <article className={styles.card}>
        <strong>Text and email notifications</strong>
        <span className={styles.concern}>Delivery not verified</span>
        <p>Manual SMS/email test workflows are separate from nightly scanning.
          Recipient opt-in, provider credentials, and a confirmed delivery test are still required.
          SMS is not automatically enabled.</p>
      </article>
      <article className={styles.card}>
        <strong>Alpaca staging charts</strong>
        <span className={styles.concern}>Authentication needs repair</span>
        <p>The staging Render logs showed Alpaca HTTP 401 on October 24.
          The separate research-only enrichment service is not a verified replacement for staging credentials.
          Orders remain disabled.</p>
      </article>
    </div>
    <p className={styles.note}>This status board does not dispatch scans, send messages, create Drive files,
      modify trial restrictions, or enable trading. A configured workflow is not proof of successful delivery.</p>
  </section>;
}
