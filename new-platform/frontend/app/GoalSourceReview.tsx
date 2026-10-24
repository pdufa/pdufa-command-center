"use client";
import { useId, useState } from "react";
import { filterSourceIssues, type GoalSourceReview as Review } from "../lib/goal-source-review";
import styles from "./GoalSourceCoverage.module.css";

const PAGE_SIZE = 10;
function checkedTime(stamp: string): string {
  return new Date(stamp).toLocaleString("en-US", { timeZone: "America/Los_Angeles",
    month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short" });
}
export default function GoalSourceReview({ review }: { review: Review | null }) {
  const queryId = useId();
  const familyId = useId();
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("ALL");
  const [page, setPage] = useState(0);
  if (!review) return <p className={styles.empty}>Program-level evidence details are unavailable in this matched report.</p>;
  const categories = [...new Set(review.items.map(item => item.category))];
  const filtered = filterSourceIssues(review.items, category, query);
  const currentPage = Math.min(page, Math.max(0, Math.ceil(filtered.length / PAGE_SIZE) - 1));
  const offset = currentPage * PAGE_SIZE;
  const visible = filtered.slice(offset, offset + PAGE_SIZE);
  return <details className={styles.review}>
    <summary className={styles.reviewSummary}>Inspect required evidence gaps ({review.total.toLocaleString("en-US")}) <span>Expand ▾</span></summary>
    <div className={styles.reviewBody}>
      <p className={styles.intro}>Read the recorded reason for each published finding. These are evidence gaps, not failed trials.
        {review.items.length < review.total ? " The report includes a bounded sample; additional gaps remain in the original audit." : ""}</p>
      <div className={styles.reviewFilters}>
        <label htmlFor={queryId}>Search ticker, exact program or reason
          <input id={queryId} type="search" value={query} onChange={event => { setQuery(event.target.value); setPage(0); }} />
        </label>
        <label htmlFor={familyId}>Source family
          <select id={familyId} value={category} onChange={event => { setCategory(event.target.value); setPage(0); }}>
            <option value="ALL">All source families</option>
            {categories.map(name => <option key={name} value={name}>{name}</option>)}
          </select>
        </label>
      </div>
      <p className={styles.reviewCount} role="status">{filtered.length
        ? `Showing ${offset + 1}–${offset + visible.length} of ${filtered.length} matching published findings.`
        : "No published findings match these filters."} {review.items.length} examples recorded; {review.total} required gaps in the audit.</p>
      <div className={styles.issueList}>
        {visible.map(item => <article key={item.id} className={styles.issue} aria-label={`${item.ticker} ${item.category} ${item.claim} evidence gap`}>
          <div className={styles.issueHeading}><strong>{item.ticker} · {item.category}</strong><span>{item.status.replaceAll("_", " ")}</span></div>
          <p className={styles.issueKey}>{item.eventKey}</p>
          <strong className={styles.issueClaim}>{item.claim.replaceAll("_", " ")}</strong>
          <p>{item.reason}</p>
          <div className={styles.issueSource}>
            <time dateTime={item.checkedAt}>Recorded check: {checkedTime(item.checkedAt)}</time>
            {item.sourceUrl ? <a href={item.sourceUrl} target="_blank" rel="noopener noreferrer">Recorded source ↗</a>
              : <span>Source document not available in this finding</span>}
          </div>
        </article>)}
      </div>
      {filtered.length > PAGE_SIZE ? <div className={styles.reviewPages}>
        <button type="button" disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}>Previous evidence findings</button>
        <span>Page {currentPage + 1} of {Math.ceil(filtered.length / PAGE_SIZE)}</span>
        <button type="button" disabled={offset + PAGE_SIZE >= filtered.length} onClick={() => setPage(currentPage + 1)}>Next evidence findings</button>
      </div> : null}
    </div>
  </details>;
}
