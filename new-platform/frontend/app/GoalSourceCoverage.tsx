"use client";
import type { GoalScanView } from "../lib/goal-scan-evidence";
import { goalSourceCoverage } from "../lib/goal-source-coverage";
import { goalSourceReview } from "../lib/goal-source-review";
import GoalSourceReview from "./GoalSourceReview";
import styles from "./GoalSourceCoverage.module.css";

type Props={source:unknown;scan:GoalScanView|null;loading:boolean};
function num(x:number){return x.toLocaleString("en-US");}
export default function GoalSourceCoverage({source,scan,loading}:Props){
  const audit=goalSourceCoverage(source,scan);
  return <section className={styles.shell} aria-label="GOAL independently recorded source audit coverage">
    <details className={styles.details}>
      <summary className={styles.summary}>
        <span>Source audit · FDA / SEC / financial evidence</span>
        <small>{loading?"Checking report…":audit
          ? audit.fullCoverage?"Published coverage complete · inspect ▾"
          :"Published coverage partial · inspect ▾"
          :"Source coverage not verified · inspect ▾"}</small>
      </summary>
      <div className={styles.content}>
        {audit ? <>
          <p className={styles.intro}>Original source audit for <strong>{audit.date}</strong>
            {audit.today?" (today Pacific)":" (previous published day)"}.
            The audit software completed, but that is separate from complete source coverage.
            These are <strong>source findings, not numbers of clinical trials</strong>.</p>
          <div className={styles.metrics}>
            <div><span>Findings verified</span><strong>{num(audit.verified)} / {num(audit.due)}</strong>
              <small>{audit.coveragePercent.toFixed(1)}% of due findings</small></div>
            <div><span>Unresolved</span><strong>{num(audit.unresolved)}</strong>
              <small>Need evidence review</small></div>
            <div><span>Conflicted</span><strong>{num(audit.conflicted)}</strong>
              <small>Conflicting source identity; do not treat as verified</small></div>
            <div><span>Unavailable</span><strong>{num(audit.unavailable)}</strong>
              <small>Cannot treat as verified</small></div>
            <div><span>Not applicable</span><strong>{num(audit.notApplicable)}</strong>
              <small>Not counted as verified</small></div>
          </div>
          <div className={audit.fullCoverage?styles.ok:styles.caution}>
            <strong>{audit.fullCoverage?"Published audit reports full source coverage":"Full source coverage NOT verified"}</strong>
            <p>{audit.missingRequired.length
              ? "Required source families still missing: "+audit.missingRequired.join(", ")+"."
              : "No required source families listed as missing in this matched report."}</p>
          </div>
          <a href={audit.runUrl} target="_blank" rel="noopener noreferrer">
            Open original source audit run #{audit.runId} ↗
          </a>
          <GoalSourceReview key={audit.runId} review={goalSourceReview(source,scan)} />
        </> : <p className={styles.empty}>{loading
          ? "Reading the original source audit…"
          : "No valid source audit could be matched to this dated clinical run. Counts withheld rather than copied from another date or run."}</p>}
        <p className={styles.foot}>Coverage is limited to the recorded audit scope.
          An individual FDA, SEC or issuer record may still require review.
          Missing data is not zero, a clinical failure, a probability or permission to trade.
          No new scan, provider request, or data write is performed here.</p>
      </div>
    </details>
  </section>;
}
