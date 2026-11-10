import {FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES} from "../../../lib/focus-r79-launch-htn-sap-lock-evidence-gates";
import styles from "./ScientificOriginalsIntakeR71.module.css";

/** R79 clinical-evidence authenticity and audit readiness. Not a grade. */
export default function LaunchHtnProspectiveSapGateR79(){
 const g=FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES;
 if(!g)return <section className={styles.shell}
     aria-label="R79 Launch-HTN SAP and unblinding evidence authentication">
     <p role="alert">Original signed evidence requirements failed validation. Gate remains blocked.</p>
   </section>;
 return <section className={styles.shell}
    aria-label="R79 Launch-HTN SAP and unblinding evidence authentication">
   <div className={styles.eyebrow}>MAIN · REVISION 79 · ORIGINAL EVIDENCE AUTHENTICATION GATE</div>
   <h3>Launch-HTN · independent pre-unblinding evidence requirements</h3>
   <p className={styles.disclaimer}>
    This gate distinguishes <strong>original, independently authenticated trial
    records</strong> from later-publication document images and dated press releases.
    The FDA/ICH statistical guidance calls for a final SAP before breaking the blind
    and formal records of finalization and unblinding.</p>
   <div className={styles.stats}>
    <div><small>Original proof requirements authenticated</small>
      <strong>{g.requirementsIndependentlyVerified} / {g.requiredBeforeProspectiveSapChronologyCertified}</strong></div>
    <div><small>Original SAP byte SHA-256 receipts</small>
      <strong>{g.sourceBytesSha256Authenticated} / {g.originalDocumentCount}</strong></div>
    <div><small>Verified first unblinded treatment access</small>
      <strong>NOT AVAILABLE</strong></div>
    <div><small>Independent approved signing trust anchors</small>
      <strong>{g.productionApprovedTrustAnchors} · none configured</strong></div>
   </div>
   <details className={styles.details}>
    <summary>Seven source-level verification blocks and the evidence each needs</summary>
    <ol>{g.sourceRequirements.map(item=><li key={item.id}>
      <strong>{item.label}</strong>
      <div>Evidence status: {item.status.replaceAll("_"," ")}</div>
      <p>{item.evidence}</p>
    </li>)}</ol>
   </details>
   <details className={styles.details}>
    <summary>Scientific standard and independently verifiable chronology controls</summary>
    <ul>{g.reviewStandards.map(standard=><li key={standard.kind}>
      <strong>{standard.kind.replaceAll("_"," ")}</strong> · {standard.norm}
      <div className={styles.sources}><a href={standard.url} target="_blank"
        rel="noopener noreferrer">Read original FDA/ICH guidance</a></div>
    </li>)}</ul>
    <p className={styles.disclaimer}>A separate research verifier checks SHA-256
      matches against original source bytes, chronology between signed SAP finalization,
      documented database lock and first actual unblinding, and two cryptographic
      attestations under separately authorized trust anchors. It has no live approved
      keys or original bytes, and a synthetic test cannot authorize a real case.</p>
   </details>
   <p className={styles.warning}><strong>BLOCKED — authenticity not demonstrated.</strong>
     Printed SAP date {g.observedPrintedMainSapDate} and public first results
     {g.observedPublishedFirstToplineDate} do not determine first unblinding.
     The two addendum date-year conflicts remain unresolved.
     Qualified independent science reviews: <strong>0</strong>.
     Validated FDA application outcomes: <strong>0/23</strong>.
     Approval/CRL forecast: <strong>ABSTAIN</strong>;
     independent decision timing: <strong>UNKNOWN</strong>.</p>
 </section>;
}
