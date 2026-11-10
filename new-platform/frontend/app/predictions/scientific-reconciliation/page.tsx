import {R91_POSTED_RESULTS_ROSTER} from
 "../../../lib/focus-r91-posted-results-reconciliation";
import PostedResultsR91Client from "./PostedResultsR91Client";
import {R91_DATED_SOURCE_AUDIT} from "../../../lib/focus-r91-source-audit-readiness";
import styles from "../evidence-gaps/EvidenceRecoveryBoardR68.module.css";

export const metadata={
 title:"Stage 4 Scientific Reconciliation | Original Posted Endpoint and Safety Data",
 description:"Exact-NCT original ClinicalTrials.gov primary outcome and adverse event denominator readback, without independent science certification"
};
export default function ScientificReconciliationR91Page(){
 const d=R91_POSTED_RESULTS_ROSTER;
 if(!d||!R91_DATED_SOURCE_AUDIT)return <main className={styles.coverage}>
  <h1>Stage 4 — scientific source reconciliation</h1>
  <p role="alert">Original 29-NCT source integrity verification failed.
   No scientific review, clinical pass/fail, or FDA forecast can be inferred.</p>
 </main>;
 return <main className={styles.coverage}>
  <div className={styles.eyebrow}>MAIN · REVISION 91 · STAGE 4 STEP 2/3</div>
  <h1>Primary endpoints, analysis groups and adverse-event denominators</h1>
  <p className={styles.intro}>{d.notice} The original posted-results
    census was observed on <strong>{d.datedRegistrySnapshot} UTC</strong>.
    Use the button to fetch an exact trial's current public original record.
    Results-source extraction is not a qualified medical or statistical review.
  </p>
  <div className={styles.stats}>
   <div><small>Exact FOCUS trials</small><strong>{d.exactTrials}</strong></div>
   <div><small>Registry results posted at source census</small>
    <strong>{d.withPostedResultsAtSnapshot}</strong></div>
   <div><small>No registry posted aggregate results at census</small>
    <strong>{d.withoutPostedResultsAtSnapshot}</strong></div>
   <div><small>Prospectively signed SAPs authenticated</small>
    <strong>{d.originalSignedSAPsVerified}</strong></div>
   <div><small>Verified analysis-population reconciliations</small>
    <strong>{d.originalAnalysisPopulationsIndependentlyReconciled}</strong></div>
   <div><small>Qualified independent science signoffs</small>
    <strong>{d.qualifiedScienceSignoffs}</strong></div>
  </div>
  <div className={styles.stats} aria-label="Dated original posted results readback">
    <div><small>Official records re-read and fingerprinted</small>
     <strong>{R91_DATED_SOURCE_AUDIT.originalResultsSourceNcts}/12</strong></div>
    <div><small>Original PRIMARY outcome entries</small>
     <strong>{R91_DATED_SOURCE_AUDIT.reportedPrimaryOutcomeEntries}</strong></div>
    <div><small>Reported serious adverse-event terms</small>
     <strong>{R91_DATED_SOURCE_AUDIT.seriousAdverseTermEntries}</strong></div>
    <div><small>Original safety exposure groups</small>
     <strong>{R91_DATED_SOURCE_AUDIT.safetyArmGroupEntries}</strong></div>
    <div><small>Registry-reported comparison p-value fields</small>
     <strong>{R91_DATED_SOURCE_AUDIT.sourcePValueEntries}</strong></div>
    <div><small>Signed original final SAPs independently authenticated</small>
     <strong>{R91_DATED_SOURCE_AUDIT.finalProspectivelySignedSAPsIndependentlyAuthenticated}</strong></div>
  </div>
  <details className={styles.coverageDetails}>
    <summary>Open dated 12-trial source SHA-256 and original primary endpoint receipt</summary>
    <p>Snapshot observed {R91_DATED_SOURCE_AUDIT.observedDateUtc} UTC.
      These are original posted registry fields, not independent
      effect estimates, safety assessments, or FDA prediction accuracy.</p>
    <ul>{R91_DATED_SOURCE_AUDIT.rows.map(row=><li key={row.nct}>
      <b>{row.ticker} · {row.nct}</b> — {row.primaryOutcomeCount} primary,
      {" "}{row.seriousAdverseEventTerms} serious AE terms,
      {" "}{row.safetyArmGroups} reported safety group(s)
      <div>{row.originallyPostedPrimaryTitles.join("; ")}</div>
      <div>Official response SHA-256: <code>{row.rawOriginalSourceSHA256}</code></div>
      <a href={row.originalResultNctUrl} target="_blank" rel="noopener noreferrer">
       Official original posted result record
      </a>
    </li>)}</ul>
  </details>
  <p className={styles.notice}>
   The first 12 source records have ClinicalTrials.gov posted aggregate
   result tables. The other 17 have issuer, SEC or publisher report leads
   in the adjacent source-recovery page, but not current registry-posted
   aggregate results. A registry-published p-value, arm count, or adverse
   event term is only the reported source field. It must be reconciled with
   the original final approved SAP, analysis sets, missing-data rules,
   exposure and treatment windows by independent qualified reviewers.
   No trial grade, probability, or FDA decision is released.
  </p>
  <p className={styles.footer}>
   <a href="/predictions/scientific-reconciliation/protocol-crosswalk">
    Open Stage 4 current registry protocol-versus-posted primary endpoint crosswalk
   </a>. Exact textual comparisons are neither original signed SAP verification
   nor independent scientific endpoint adjudication.
  </p>
  <PostedResultsR91Client rows={d.rows}/>
  <p className={styles.footer}>
   <a href="/predictions/source-recovery">
    Source links for all 17 trials without public original protocol/SAP uploads
   </a>{" · "}
   <a href="/predictions/original-documents/chronology">
    Original signed SAP/version chronology gaps
   </a>{" · "}
   <a href="/predictions/phase-verification">
    Registry phase-source integrity checks
   </a>.
  </p>
 </main>;
}
