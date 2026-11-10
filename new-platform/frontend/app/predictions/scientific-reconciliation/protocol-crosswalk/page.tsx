import {R92_CURRENT_PROTOCOL_RESULTS_ROSTER} from
 "../../../../lib/focus-r92-protocol-results-crosswalk";
import CurrentProtocolResultsR92Client from "./CurrentProtocolResultsR92Client";
import {R92_DATED_CROSSWALK_AUDIT} from
 "../../../../lib/focus-r92-dated-crosswalk-audit";
import styles from "../../evidence-gaps/EvidenceRecoveryBoardR68.module.css";

export const metadata={
 title:"Stage 4 | Current registry protocol versus posted primary endpoints",
 description:"Read-only original registered-versus-posted primary outcome lexical crosswalk; NOT prospectively signed SAP analysis"
};
export default function R92CurrentProtocolResultsPage(){
 const d=R92_CURRENT_PROTOCOL_RESULTS_ROSTER;
 if(!d||!R92_DATED_CROSSWALK_AUDIT)return <main className={styles.coverage}>
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
  <div className={styles.stats}>
    <div><small>Dated official source readbacks</small>
      <strong>{R92_DATED_CROSSWALK_AUDIT.checkedNcts}/12</strong></div>
    <div><small>Exact current-registry title/timeframe matches</small>
      <strong>{R92_DATED_CROSSWALK_AUDIT.exactCurrentRegistryTitleTimeframeMatches}/16</strong></div>
    <div><small>Current registry text discrepancies</small>
      <strong>{R92_DATED_CROSSWALK_AUDIT.observedTextDifferences}</strong></div>
    <div><small>Original API SHA-256 receipts unchanged</small>
      <strong>{R92_DATED_CROSSWALK_AUDIT.rawR91SourceHashesStable}/12</strong></div>
  </div>
  <details className={styles.coverageDetails}>
   <summary>Review dated source-verified 12-trial current registry endpoint correspondence</summary>
   <p>Registry snapshot: {R92_DATED_CROSSWALK_AUDIT.sourceDateUtc} UTC.
     Zero observed wording discrepancies is not proof of original
     pre-unblinding prespecification.</p>
   <ul>{R92_DATED_CROSSWALK_AUDIT.rows.map(row=><li key={row.nct}>
     <b>{row.ticker} · {row.nct}</b>
     {" — "}{row.exactTextualMatches}/{row.postedPrimaryCount}
     exact current registry primary title/timeframe text matches.
     <div>{row.reportedPrimaryTitles.join("; ")}</div>
     <div>Original public API SHA-256:
       <code>{row.sourceSHA256}</code></div>
     <a href={row.studyUrl} target="_blank" rel="noopener noreferrer">
       Open official study
     </a>
   </li>)}</ul>
  </details>
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
   <a href="/predictions/scientific-reconciliation/priority-gates">
    Continue original signed-SAP and independent safety review — ACACIA-HCM and Launch-HTN
   </a>. Eleven existing source/authentication requirements are review tasks,
   not completed medical assessments.
  </p>
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
