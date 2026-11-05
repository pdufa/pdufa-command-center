/** Independent RAAS review assignments sourced from the real provisional ledger.
 * This page never approves clinical grades or issues calibrated forecasts.
 */
import type {Metadata} from "next";
import Link from "next/link";
import {buildRaasIndependentReviewQueue} from "../../lib/raas-independent-review-queue";
import {currentReviewIntakeAudit} from "../../lib/raas-external-review-intake";
import ReviewQueueClient from "./ReviewQueueClient";
import css from "../raas-history/page.module.css";

export const metadata:Metadata={
 title:"RAAS · Independent Metric Review Queue | PDUFA",
 description:"Source-backed, exact-trial RAAS metrics awaiting external independent verification and calibration."
};
const queue=buildRaasIndependentReviewQueue();
const receiptAudit=currentReviewIntakeAudit();
export default function IndependentMetricReviewQueuePage(){
 return <main className={css.root} data-raas-independent-review-queue="source-reviewed-pending">
  <header className={css.header}>
   <Link className={css.back} href="/raas-scan">← Back to RAAS scores</Link>
   <h1>RAAS · independent metric review queue</h1>
   <p>Exact clinical trial, therapy, stage and individual metric source records
    awaiting a documented independent second assessment. Expand any row for
    its evidence, comparator, uncertainty and required sign-off work.</p>
  </header>
  <div className={css.stats}>
   <div><strong>{queue.total}</strong><span>Provisional source-backed metric review tasks</span></div>
   <div><strong>{queue.currentFdaPhase3Metrics}</strong><span>Accepted FDA application with registered Phase 3 support · review priority</span></div>
   <div><strong>{queue.currentTopPhase3Metrics}</strong><span>Six current Phase 3 TOP study research-review tasks</span></div>
   <div><strong>{queue.independentlyVerifiedSignoffs}</strong><span>Certified independent signed reviews available</span></div>
  </div>
  <p className={css.disclaimer} data-raas-review-state="NOT_VALIDATED">
   <strong>Read-only validation queue, not a list of approved grades.</strong>
   {" "}{queue.aiPending} AI-assisted source crosschecks await an independent reviewer;
   {" "}{queue.markedIndependentWithoutAuditedReceipt} records marked reviewed without a
   separately audited sign-off receipt. Source snapshot: {queue.asOf}.
   {" "}There are {queue.uniqueNcts} unique NCTs across {queue.issuerCount} tickers
   in this reviewed-metric task inventory, not a complete current Pipeline universe.
   The other {queue.otherResearchMetrics} metric tasks are historical/other research,
   not source-verified current Phase 3 applicants.
  </p>
  <p className={css.notice}>
   <strong>How to advance:</strong> Assign each record to an independent expert, reproduce
   the original and benchmark measurements, audit biases and risks, and capture
   signed attributable review evidence. Reconcile verified sign-offs into the canonical
   metric feed only after audit, then separately validate all 30 metrics and prospective
   three-way FDA probabilities. This page cannot certify human sign-offs automatically.
   Neither prior AI research nor an FDA-accepted application establishes FDA success odds,
   a PASS/CRL/EXTENSION prediction, or a 30/30 RAAS rating.
  </p>
  <section className={css.section} data-raas-external-review-intake="AUTHENTICATION_REQUIRED">
   <div className={css.sectionTitle}>
    <h2>External reviewer receipt audit</h2>
    <span>Receiving a document does not validate the reviewer</span>
   </div>
   <div className={css.stats}>
    <div><strong>{receiptAudit.submitted}</strong><span>External signed-document references submitted</span></div>
    <div><strong>{receiptAudit.pendingExternalAuthentication}</strong><span>Structurally complete receipts, pending human authentication</span></div>
    <div><strong>{receiptAudit.blocked}</strong><span>Receipts blocked by identity, date, source revision or missing fields</span></div>
    <div><strong>{receiptAudit.certifiedIndependentSignoffs}</strong><span>Externally certified independent review sign-offs</span></div>
   </div>
   <p className={css.notice}>Each downloadable review packet has a SHA-256 checksum
    binding its exact NCT, therapy, indication, RAAS stage and metric to the
    primary/benchmark evidence and risk assessment. Changed evidence invalidates
    the prior packet for matching. The checksum proves only integrity of the
    recorded packet, <strong>not medical accuracy or source authenticity</strong>.
    A submitted receipt is not an independent clinical validation until
    a separate authenticated reviewer and evidence adjudication are completed.
    This website does not accept public review uploads or automatically release scores.
   </p>
  </section>
  <p className={css.notice}>To expand from these 82 already source-checked metric
   research tasks to every registered study, open
   {" "}<Link href="/raas-evidence-backlog">the complete 762-trial evidence-gap queue</Link>.
   It identifies the next source task without inventing scores.</p>
  <ReviewQueueClient queue={queue}/>
  <p className={css.foot} style={{marginTop:20}}>
   The queue is re-derived from the checked-in research ledger on deployment.
   It does not amend the ledger, alter TOP/BOTTOM histories, or reactivate
   retired GEM/GEM JR screens. An unreviewed metric is N/A, never zero.
   {" "}<Link href="/raas-worklist#raas-fda-prediction-accuracy">
    FDA outcome calibration and prospective holdout gates</Link>.
  </p>
 </main>;
}
