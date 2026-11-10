import Link from "next/link";
import {FOCUS_R64_METHOD_PAGE_VIEW} from "../../../lib/focus-r64-original-method-page-view";
import styles from "./OriginalMethodSourceLadderR64.module.css";

/** R64: purely presentational native, accessible expand/collapse. No reviewer
 * submission, provisional grade, FDA prediction or data source re-fetch.
 */
export default function OriginalMethodSourceLadderR64({nct}:{nct:string}){
  const source=FOCUS_R64_METHOD_PAGE_VIEW;
  if(!source)return <section aria-label="Original PDF method review source audit"
      className={styles.shell}>
    <h2>Original scientific method page audit</h2>
    <p role="alert">The immutable R63 original-source page index did not pass
      exact-NCT or source-integrity checks. Findings are withheld.</p>
  </section>;
  const trial=source.trials.find(t=>t.nct===nct);
  if(!trial)return <section className={styles.shell} role="status">
    Source review is unavailable for the requested exact NCT.
  </section>;
  return <section id="original-methods-r64" aria-label="R64 original method page review"
      className={styles.shell}>
    <div className={styles.eyebrow}>MAIN · REVISION 64 · EIGHT ORIGINAL SCIENTIFIC SOURCE DOMAINS</div>
    <h2>Scientific assessment page references · {trial.ticker} / {trial.nct}</h2>
    <div className={styles.statusRow}>
      <div className={styles.value}>
        <span>Research installation stage</span><strong>4 · Evidence collection</strong>
      </div>
      <div className={styles.value}>
        <span>Trial assessment level</span><strong>UNASSESSED · SOURCE ONLY</strong>
      </div>
      <div className={styles.value}>
        <span>Domain review positions</span><strong>8 · 0 adjudicated</strong>
      </div>
      <div className={styles.value}>
        <span>FDA outcome / accuracy</span><strong>ABSTAIN · NOT CALIBRATED</strong>
      </div>
    </div>
    <p className={styles.explainer}>
      Expand an individual domain to inspect the original public protocol or
      statistical analysis plan PDF page leads. These are machine-matched
      phrases, <strong>not independent clinical grades or verified pre-unblinding
      prespecifications</strong>. An unmatched keyword does not establish a missing
      scientific method, and a source-free registry record does not establish trial failure.
    </p>
    <div className={styles.summary} role="status">
      <strong>{trial.totalPageLeads}</strong> page references for this NCT ·
      <strong> {trial.sourcePdfDocumentsWithPageLeads}</strong> PDF files with
      identified page references · <strong>0/8</strong> domains independently graded.
      Across FOCUS: 29 unique trials, 23 provisional application cycles,
      232 unscored domain positions and 466 page references.
    </div>
    <div className={styles.domains}>
      {trial.domains.map((d,i)=><details key={d.key} className={styles.domain}>
        <summary>
          <strong>{i+1}. {d.label}</strong>
          <span>{d.references.length>0?
            d.references.length+" source page lead"+(d.references.length===1?"":"s"):
            "No current page lead — other originals may exist"}</span>
          <small>Assessment level: UNASSESSED · Not graded</small>
        </summary>
        <div className={styles.expanded}>
          <p><strong>Scientific grade:</strong> Not assigned. <strong>Independent
            reviewer signoff:</strong> Not completed. Historical original version,
            protocol amendment timing and original locked SAP status remain unverified.</p>
          {d.references.length?
            <ul>{d.references.map((ref,j)=><li key={j}>
              <a target="_blank" rel="noopener noreferrer"
                href={ref.pageUrl}>{ref.filename} · PDF page {ref.pdfPageOneBased}</a>
              <span>Original document, page-linked source lead only</span>
            </li>)}</ul>:
            <p>No machine-detected page reference from the archived current
              public documents. Recover original sponsor, journal, trial registry
              or regulatory source material; do not infer an absent method or negative result.</p>}
        </div>
      </details>)}
    </div>
    <p className={styles.footer}>
      Original R63 PDF review archive: <a href={source.archiveUrl} target="_blank"
        rel="noopener noreferrer">Open immutable source record</a>.
      Every page link opens the original public PDF; page anchors may be
      interpreted differently on some iPhone PDF viewers.
      <strong> No medical-review grades, 800-test completion, calibrated
        probabilities or released FDA predictions are claimed.</strong>
    </p>
    <p className={styles.back}><Link href="/predictions">Return to FDA prediction research board</Link></p>
  </section>;
}
