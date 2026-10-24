"use client";

/** The GOAL page is the iterative, screenshot-inspired dashboard workspace.
 * It displays saved facts; missing source evidence remains visibly unavailable.
 * Existing RESULTS/SCANS and FS/FA qualification controls remain authoritative.
 */
import { useMemo, useState } from "react";
import styles from "./GoalDashboard.module.css";

export type GoalRecord = {
  id: string;
  programId?: string;
  ticker: string;
  drug?: string;
  indication?: string;
  pdufaDate?: string;
  checkStatus?: string;
};
export type GoalSection = "SCANS" | "RESULTS" | "PIPELINE" | "GEM_JR" | "GEM" | "RESTRICTIONS";
export type GoalDashboardProps = {
  records: GoalRecord[] | null;
  pipelineCount: number | null;
  gemJrCount: number | null;
  gemCount: number | null;
  sourceAsOf?: string | null;
  sourceState?: string | null;
  scanFinishedAt?: string | null;
  scanComplete?: boolean;
  cached?: boolean;
  onOpen: (section: GoalSection) => void;
};

function number(value: number | null) {
  return value === null || !Number.isSafeInteger(value) || value < 0
    ? "—" : value.toLocaleString("en-US");
}
function pacificDay(now: Date): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Los_Angeles", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(now);
  const get = (key: string) => parts.find(part => part.type === key)?.value || "";
  return [get("year"), get("month"), get("day")].join("-");
}
export function daysUntilReportedDate(date: string | undefined, now = new Date()): number | null {
  if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return null;
  const candidate = new Date(date + "T12:00:00Z");
  if (!Number.isFinite(candidate.getTime()) || candidate.toISOString().slice(0, 10) !== date) return null;
  const today = new Date(pacificDay(now) + "T12:00:00Z");
  return Math.round((candidate.getTime() - today.getTime()) / 86400000);
}
function sourceTime(text?: string | null) {
  if (!text || !Number.isFinite(Date.parse(text))) return "Not verified";
  return new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Los_Angeles", month: "short", day: "numeric",
    year: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short",
  }).format(new Date(text));
}
export function goalSummary(records: GoalRecord[] | null, now = new Date()) {
  if (!records) return { upcoming: null, review: null, dated: [] as (GoalRecord & { days: number })[] };
  const dateItems = records.map(row => ({...row, days: daysUntilReportedDate(row.pdufaDate, now)}))
    .filter((row): row is GoalRecord & {days:number} => row.days !== null && row.days >= 0 && row.days <= 180)
    .sort((a, b) => a.days - b.days || a.ticker.localeCompare(b.ticker) || a.id.localeCompare(b.id));
  const tagged = records.filter(row => !!row.checkStatus?.trim());
  const review = tagged.length
    ? records.filter(row => /(?:NEEDS[ _-]*REVIEW|REVIEW_REQUIRED|\bREVIEW\b)/i.test(row.checkStatus || "")).length
    : null;
  return { upcoming: dateItems.length, review, dated: dateItems };
}

export default function GoalDashboard({
  records, pipelineCount, gemJrCount, gemCount,
  sourceAsOf, sourceState, scanFinishedAt, scanComplete = false, cached = false, onOpen,
}: GoalDashboardProps) {
  const [query, setQuery] = useState("");
  const [windowDays, setWindowDays] = useState<30 | 90 | 180>(180);
  const summary = useMemo(() => goalSummary(records), [records]);
  const rows = summary.dated.filter(row =>
    row.days <= windowDays &&
    [row.ticker, row.drug, row.indication, row.id, row.programId].some(value =>
      (value || "").toLowerCase().includes(query.trim().toLowerCase()))).slice(0, 20);
  const savedLabel = cached ? "Saved snapshot / not verified current" : "Published source snapshot";
  return <main className={styles.goal} aria-label="GOAL dashboard workspace">
    <header className={styles.intro}>
      <div>
        <span className={styles.kicker}>GOAL · Dashboard design workspace</span>
        <h2>PDUFA Tracker — The target dashboard</h2>
        <p>Building toward your desktop and iPhone reference image. Existing scan, restriction and scoring pages remain unchanged.</p>
      </div>
      <span className={styles.workInProgress}>Working design · Not final</span>
    </header>
    <div className={styles.statusRow} aria-label="Goal reference status cards">
      <section className={styles.statusCard}>
        <span className={styles.statusLabel}>◷ Last updated</span>
        <strong>{sourceTime(sourceAsOf)}</strong>
        <small>{savedLabel}</small>
      </section>
      <section className={styles.statusCard}>
        <span className={styles.statusLabel}>▣ Overnight scan</span>
        <strong>{scanComplete && scanFinishedAt ? "Confirmed complete" : "Not confirmed complete"}</strong>
        <small>{sourceTime(scanFinishedAt)}</small>
      </section>
      <section className={styles.statusCard}>
        <span className={styles.statusLabel}>◈ Data source status</span>
        <strong>{sourceState || "Not verified"}</strong>
        <small>Source summary only; individual FDA / SEC checks may still require review.</small>
      </section>
    </div>
    <div className={styles.metrics} aria-label="Goal dashboard metrics">
      <section className={styles.metric}><span>Pipeline candidates</span><strong>{number(pipelineCount)}</strong><small>Reported source programs, not every monitored trial</small></section>
      <section className={styles.metric}><span>Reported PDUFA ≤180 days</span><strong>{number(summary.upcoming)}</strong><small>Saved dates; individual FDA verification required</small></section>
      <section className={styles.metric}><span>Review-tagged programs</span><strong>{number(summary.review)}</strong><small>Saved program statuses, not scan-finding totals</small></section>
      <section className={styles.metric}><span>New / updated today</span><strong>—</strong><small>Dated scan reconciliation not connected here yet</small></section>
      <section className={styles.metric}><span>Special designations</span><strong>—</strong><small>Verified designation summary pending integration</small></section>
    </div>
    <section className={styles.results} aria-label="Upcoming saved PDUFA candidates">
      <div className={styles.sectionHeader}>
        <div><h3>Upcoming PDUFA events</h3><p>Preview from the saved Pipeline. Not a claim that today's scan found these events.</p></div>
        <button type="button" onClick={() => onOpen("RESULTS")}>Open RESULTS →</button>
      </div>
      <div className={styles.filters}>
        <div role="group" aria-label="PDUFA date windows">
          {([30,90,180] as const).map(days => <button type="button" key={days}
            className={windowDays === days ? styles.selected : styles.unselected}
            aria-pressed={windowDays === days} onClick={() => setWindowDays(days)}>Next {days} days</button>)}
        </div>
        <label>Search saved events
          <input type="search" value={query} onChange={e => setQuery(e.target.value)}
            placeholder="Ticker, trial, drug, indication…" aria-label="Search GOAL events" />
        </label>
      </div>
      <div className={styles.tableScroll}>
        <table>
          <thead><tr><th>Ticker</th><th>Program / indication</th><th>Reported date</th><th>Days</th><th>Source status</th><th>Open</th></tr></thead>
          <tbody>{rows.length ? rows.map(row => <tr key={row.id}>
            <td><strong>{row.ticker || "—"}</strong></td>
            <td>{row.drug || row.indication || row.id}<small>{row.id}</small></td>
            <td>{row.pdufaDate}</td><td>{row.days}</td>
            <td>{row.checkStatus || "Review needed"}</td>
            <td><button type="button" onClick={() => onOpen("PIPELINE")}>Pipeline →</button></td>
          </tr>) : <tr><td colSpan={6}>{records ? "No saved events match this date range and search." : "Loading the published Pipeline. No dates inferred."}</td></tr>}</tbody>
        </table>
      </div>
      <p className={styles.footnote}>Showing up to 20 matches; the full list and restrictions remain in PIPELINE. Missing values are not zero.</p>
    </section>
    <div className={styles.stageGrid} aria-label="Goal candidate stage previews">
      <section><div className={styles.stageHeader}><h3>♧ Pipeline</h3><button type="button" onClick={() => onOpen("PIPELINE")}>View all →</button></div>
        <strong>{number(pipelineCount)}</strong><span>Saved Pipeline candidates</span>
        <p>Market-cap, public-company and Phase 3 criteria remain governed by the RESTRICTIONS page.</p></section>
      <section><div className={styles.stageHeader}><h3>◇ GEM JR</h3><button type="button" onClick={() => onOpen("GEM_JR")}>View all →</button></div>
        <strong>{number(gemJrCount)}</strong><span>Saved stage members</span>
        <p>Existing GEM JR restrictions and independent FS/FA selections are preserved.</p></section>
      <section><div className={styles.stageHeader}><h3>◆ GEM</h3><button type="button" onClick={() => onOpen("GEM")}>View all →</button></div>
        <strong>{number(gemCount)}</strong><span>Saved stage members</span>
        <p>Existing GEM restrictions, scores and independent FS/FA selections are preserved.</p></section>
    </div>
    <section className={styles.next} aria-label="GOAL dashboard build milestones">
      <h3>Building this screen toward the reference image</h3>
      <div className={styles.milestones}>
        <div><strong>In place</strong><span>GOAL tab, desktop/mobile layout, live source-backed cards, Pipeline and GEM links</span></div>
        <div><strong>Next integration</strong><span>Verified daily new/review/designation counts, scan-result detail table, restriction summaries</span></div>
        <div><strong>Still pending</strong><span>Google Drive backup controls, CSV/Excel export, unified settings and phone layout polish</span></div>
      </div>
      <div className={styles.actions}>
        <button type="button" onClick={() => onOpen("SCANS")}>Open SCANS</button>
        <button type="button" onClick={() => onOpen("RESULTS")}>View scan RESULTS</button>
        <button type="button" onClick={() => onOpen("RESTRICTIONS")}>Edit RESTRICTIONS</button>
      </div>
      <p className={styles.footnote}>GOAL is a design-and-integration workspace, not a replacement for audited scan reports or the original restriction controls. No trading action is enabled.</p>
    </section>
  </main>;
}
