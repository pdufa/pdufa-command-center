import {FOCUS_R78_LAUNCH_HTN_PUBLIC_CHRONOLOGY} from "../../../lib/focus-r78-launch-htn-public-chronology";
import styles from "./ScientificOriginalsIntakeR71.module.css";

/** Source-dated registry/journal/SEC disclosures; NOT a signed DB lock or FDA grade. */
export default function LaunchHtnPublicChronologyR78(){
 const d=FOCUS_R78_LAUNCH_HTN_PUBLIC_CHRONOLOGY;
 if(!d)return <section className={styles.shell}
   aria-label="R78 Launch-HTN public readout and FDA review chronology">
   <p role="alert">Original issuer/public-source chronology did not validate. Details withheld.</p>
 </section>;
 const o=d.observation,r=d.regulatory;
 return <section className={styles.shell}
   aria-label="R78 Launch-HTN public readout and FDA review chronology">
   <div className={styles.eyebrow}>MAIN · REVISION 78 · SOURCE-DATED PUBLIC DISCLOSURES</div>
   <h3>Launch-HTN · from trial follow-up to the reported PDUFA target</h3>
   <p className={styles.disclaimer}>
     Original JAMA and issuer SEC disclosures establish when particular facts became
     publicly documented. <strong>They do not establish the actual date of final database
     lock, unblinding, or prospective SAP approval.</strong>
   </p>
   <div className={styles.stats}>
    <div><small>Last patient follow-up reported</small>
      <strong>{o.lastFollowupReportedDate}</strong></div>
    <div><small>Printed SAP signature imprints</small>
      <strong>{o.mainSapPrintedSignatureImprint} and {o.windowingAddendumPrintedSignatureImprint}</strong></div>
    <div><small>SEC sponsor topline readout</small>
      <strong>{o.publicIssuerToplineSECDisclosureDate}</strong></div>
    <div><small>Issuer-reported FDA PDUFA target</small>
      <strong>{r.pdufaTargetDate}</strong></div>
   </div>
   <details className={styles.details}>
    <summary>Nine source-dated trial, journal and regulatory events</summary>
    <ol>{d.sourceEvents.map(event=><li key={event.eventId}>
      <strong>{event.date} · {event.eventKind.replaceAll("_"," ").toLowerCase()}</strong>
      <p>{event.summary}</p>
      <div className={styles.sources}>
       <a href={event.sourceUrl} target="_blank" rel="noopener noreferrer">
         Open original public journal, issuer or SEC source</a>
       <span>Source document date: {event.sourceDate}</span>
      </div>
    </li>)}</ol>
   </details>
   <details className={styles.details}>
    <summary>Six remaining regulatory and original SAP validation requirements</summary>
    <ul>{d.blockingTasks.map(gate=><li key={gate}>{gate}</li>)}</ul>
   </details>
   <p className={styles.disclaimer}>
     In the journal, treatment assignment is described as masked until final
     database lock, but no calendar lock date is given. An earlier printed SAP
     signature and a later public readout <strong>cannot prove that signatures
     preceded actual unblinding</strong>. The two printed addendum date
     discrepancies remain unresolved.
   </p>
   <p className={styles.warning}>
     <strong>Qualified scientific review: 0 · clinical grade UNASSESSED.</strong>
     FDA NDA review continuing was <strong>issuer-reported on {r.latestSourceDate}</strong>,
     not a new FDA decision. Published target {r.pdufaTargetDate} is not a guarantee
     of action on that day. Verified original database-lock date: <strong>UNKNOWN</strong>.
     Validated FDA application forecasts: <strong>0/23</strong>.
     Official prediction: <strong>ABSTAIN</strong>; independent future timing forecast:
     <strong> UNKNOWN</strong>.
   </p>
 </section>;
}
