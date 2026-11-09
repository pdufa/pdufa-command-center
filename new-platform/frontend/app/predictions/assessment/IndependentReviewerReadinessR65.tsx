import {FOCUS_R65_REVIEW_GATES,R65_REQUIRED_REVIEW_FIELDS} from
  "../../../lib/focus-r65-independent-review-gates";
import styles from "./IndependentReviewerReadinessR65.module.css";

/** Display only: no POST, no investigator inference, no scores, no claims of
 * real reviewer signatures. Only qualified independent humans may submit
 * genuine evidence to the separately authenticated, disabled-by-default
 * reviewer pilot, subject to phase-first isolation and approval gates.
 */
export default function IndependentReviewerReadinessR65({nct}:{nct:string}){
  const work=FOCUS_R65_REVIEW_GATES;
  if(!work)return <section className={styles.panel}
      aria-label="R65 independent reviewer readiness">
    <h2>Independent reviewer intake</h2>
    <p role="alert">The original R65 research-only reviewer intake failed
      exact-NCT or source-availability validation. Review tasks are withheld.</p>
  </section>;
  const trial=work.records.find(t=>t.nct===nct);
  if(!trial)return <section className={styles.panel}
    role="status">No exact-NCT scientific reviewer intake is available.</section>;
  return <section id="scientific-reviewer-intake-r65"
      aria-label="R65 independent reviewer readiness" className={styles.panel}>
    <div className={styles.eyebrow}>
      MAIN · REVISION 65 · INDEPENDENT REVIEW READINESS · READ ONLY
    </div>
    <h2>Independent scientific adjudication · {trial.ticker} / {trial.nct}</h2>
    <p>
      This is a source-grounded human review docket, not a clinical decision.
      <strong> No independent reviewer has signed the phase, eight methods
      or an FDA forecast.</strong> The 800-method architecture is separate;
      the eight domains below are not automatically assigned numerical scores.
    </p>
    <div className={styles.stats}>
      <div><small>Phase review</small><strong>Not independently verified</strong></div>
      <div><small>Clinical assessment level</small><strong>UNASSESSED · SOURCE ONLY</strong></div>
      <div><small>Independent method grades</small><strong>0 / 8 domains</strong></div>
      <div><small>FDA outcome and accuracy</small><strong>ABSTAIN · NOT CALIBRATED</strong></div>
    </div>
    <div className={styles.notice} role="status">
      <strong>Before any score:</strong> verify exact trial phase, original
      signed protocol and SAP versions, first-public and pre-unblinding
      chronology, the complete relevant clinical evidence, independent
      reviewer authorization, and any conflicting or missing evidence.
      Source page hits alone never authorize a grade.
    </div>
    <div className={styles.domains}>
      {trial.methodTasks.map((task,i)=><details className={styles.domain}
          key={task.id}>
        <summary>
          <strong>{i+1}. {task.label}</strong>
          <span>{task.sourcePageLeads} archived PDF page leads</span>
          <small>REVIEW PENDING · SCORE WITHHELD</small>
        </summary>
        <div className={styles.detail}>
          <p><strong>Independent review checklist — all items require
            documented original evidence:</strong></p>
          <ol>{task.requiredQuestions.map((q,j)=><li key={j}>{q}</li>)}</ol>
          <p><strong>Original page references:</strong>{" "}
            <a href="#original-methods-r64">View original source PDFs and page numbers</a>
          </p>
          <p>Phase verification: pending. Original pre-readout SAP version:
            not verified. Reviewer authentication and independent second
            verifier: not completed. Scientific score: not assigned.</p>
        </div>
      </details>)}
    </div>
    <details className={styles.record}>
      <summary>Required original evidence and reviewer signoff fields ·
        {R65_REQUIRED_REVIEW_FIELDS.length}</summary>
      <div>
        <p>Every future legitimate assessment must record exact source
          identity, separate positive and negative findings, source/version
          chronology, qualified reviewer authorization, independent
          corroboration and append-only review event identity.</p>
        <ul>{R65_REQUIRED_REVIEW_FIELDS.map(x=><li key={x}>
          {x.replace(/([a-z])([A-Z])/g,"$1 $2")}
        </li>)}</ul>
        <p>No signoff fields are filled automatically. Reviewer credential
          entry, unsigned human submissions and promotion to forecast are not
          available in this display.</p>
      </div>
    </details>
    <p className={styles.footer}>
      Across FOCUS: {work.uniqueTrials} exact NCTs, {work.provisionalApplications}
      provisional application groups, {work.requiredMethodReviews} pending
      source-domain review tasks and {work.originalMachinePageLeads} original
      PDF page leads. Signed scientific assessments: 0.
      <a href={work.sourceArchiveUrl} rel="noopener noreferrer"
        target="_blank"> View immutable R65 reviewer intake archive</a>.
      This read-only checklist does not enable the existing isolated
      reviewer-write pilot or change production.
    </p>
  </section>;
}
