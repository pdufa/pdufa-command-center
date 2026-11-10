import {FOCUS_R75_LAUNCH_HTN_CHRONOLOGY} from "../../../lib/focus-r75-launch-htn-chronology";
import styles from "./ScientificOriginalsIntakeR71.module.css";

/** Source-observed dates, not signed SAP authentication or an FDA prediction. */
export default function LaunchHtnSourceChronologyR75(){
 const d=FOCUS_R75_LAUNCH_HTN_CHRONOLOGY;
 if(!d)return <section className={styles.shell}
    aria-label="R75 Launch-HTN publisher PDF chronology">
    <p role="alert">Original publisher PDF chronology validation failed; research details withheld.</p>
   </section>;
 return <section className={styles.shell}
   aria-label="R75 Launch-HTN publisher PDF chronology">
   <div className={styles.eyebrow}>MAIN · REVISION 75 · PUBLISHER PDF CHRONOLOGY RESEARCH</div>
   <h3>Launch-HTN · protocol/SAP printed dates and signatures</h3>
   <p className={styles.disclaimer}>Original publisher PDF page renders were inspected for
      <strong> seven documents and ten exact pages</strong>. These are observed document labels
      and signature imprints, not an authenticated prospective study lock or independent
      medical signoff.</p>
   <div className={styles.stats}>
     <div><small>Last study follow-up (published article)</small>
       <strong>{d.observedLastParticipantFollowUpDate}</strong></div>
     <div><small>Main SAP printed signature date</small>
       <strong>2025-02-13 · unverified lock chronology</strong></div>
     <div><small>Windowing addendum signature imprint</small>
       <strong>2025-02-23 · unverified first-public date</strong></div>
     <div><small>Internal document date discrepancies</small>
       <strong>{d.sameSourcePrintedYearDiscrepancies} · needs reconciliation</strong></div>
   </div>
   <details className={styles.details}>
    <summary>Seven publisher source PDFs · observed dates and original page references</summary>
    <ol>{d.docs.map(x=><li key={x.filename}>
       <strong>Supplement {x.supplementNumber} · {x.documentVersion}</strong>
       <div>Document heading/effective date: {x.printedEffectiveOrHeaderDate??"not shown on reviewed cover"}.
        Signature imprint: {x.printedSignatureDate??"not independently inspected"}.
        Inspected PDF physical page(s): {x.observedPageNumbers.join(", ")} of {x.sourceRenderedPages}.</div>
       {x.printedDateConflict&&
         <strong>Printed internal year conflict: needs source-version reconciliation</strong>}
       <p>{x.notes}</p>
      </li>)}</ol>
   </details>
   <div className={styles.sources}>
    <a href={d.journalPage} target="_blank" rel="noopener noreferrer">
      Open JAMA original publisher supplement section</a>
    <a href={d.pmcPublicIndex} target="_blank" rel="noopener noreferrer">
      Open independent PMC article and original supplement index</a>
   </div>
   <p className={styles.warning}><strong>Chronology is NOT verified as prospective.</strong>
     Clinical follow-up ending before a printed SAP signature date is not proof
     of post-unblinding analysis changes. Actual database lock, unblinding and
     signature provenance remain unknown. Original source PDF SHA receipts:
     <strong> 0/7 via the currently blocked automated retrieval route</strong>.
     Qualified scientific grades: <strong>0</strong>;
     future FDA decision <strong>ABSTAIN</strong>; timing <strong>UNKNOWN</strong>.</p>
 </section>;
}
