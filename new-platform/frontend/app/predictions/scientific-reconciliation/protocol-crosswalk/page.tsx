import {R92_CURRENT_PROTOCOL_RESULTS_ROSTER} from
 "../../../../lib/focus-r92-protocol-results-crosswalk";
import CurrentProtocolResultsR92Client from "./CurrentProtocolResultsR92Client";
import styles from "../../evidence-gaps/EvidenceRecoveryBoardR68.module.css";

export const metadata={
 title:"Stage 4 | Current registry protocol versus posted primary endpoints",
 description:"Read-only original registered-versus-posted primary outcome lexical crosswalk; NOT prospectively signed SAP analysis"
};
export default function R92CurrentProtocolResultsPage(){
 const d=R92_CURRENT_PROTOCOL_RESULTS_ROSTER;
 if(!d)return <main className={styles.coverage}>
  <h1>Current protocol versus posted primary endpoints</h1>
  <p role="alert">The original 29-trial and 12-case source
  identity crosswalk failed. No clinical interpretation or forecast is permitted.</p>
 </main>;
 return <main className={styles.coverage}>
  <div className={styles.eyebrow}>MAIN · REVISION 92 · STAGE 4 ORIGINAL SOURCE RECONCILIATION</div>
  <h1>Registry design-to-results primary endpoint comparison</h1>
  <p className={styles.intro}>{d.notice}</p>
  <div className={styles.stats}>
   <div><small>Exact trial population</small><strong>{d.exactFocusTrials}</strong></div>
   <div><small>Trials eligible for posted endpoint crosswalk</small>
    <strong>{d.registeredResultNcts}</strong></div>
   <div><small>Previously read posted primary outcomes</small>
    <strong>{d.priorObservedPrimaryOutcomes}</strong></div>
   <div><small>Independently authenticated original signed SAPs</small>
    <strong>{d.originalSignedSAPsAuthenticated}</strong></div>
   <div><small>Independent scientific signoffs</small>
    <strong>{d.independentScientificSignoffs}</strong></div>
  </div>
  <p className={styles.notice}>
   This comparison aligns today's registry protocol primary endpoint
   descriptions against today's posted aggregate-result primary
   descriptions. It flags exact text, title matches with changed
   timeframes, and lexical research leads. A current registry protocol
   may have been updated after data release, so even a complete text
   match is <strong>not</strong> evidence the original prospective SAP was
   finalized before unblinding. A text mismatch is also not a clinical
   failure. No qualified independent review has occurred.
  </p>
  <CurrentProtocolResultsR92Client rows={d.rows}/>
  <p className={styles.footer}>
   <a href="/predictions/scientific-reconciliation">
    Return to 12-trial original posted efficacy and safety data
   </a>{" · "}
   <a href="/predictions/original-documents/chronology">
    Review publicly uploaded SAP document chronology
   </a>{" · "}
   <a href="/predictions/source-recovery">
    Recover missing original trial sources
   </a>
  </p>
 </main>;
}
