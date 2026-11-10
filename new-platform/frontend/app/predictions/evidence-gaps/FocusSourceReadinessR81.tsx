import {FOCUS_R81_SOURCE_READINESS} from "../../../lib/focus-r81-all-focus-source-readiness";
import styles from "./EvidenceRecoveryBoardR68.module.css";

/** Read-only crosswalk of 29 original exact NCTs and 23 provisional cycles. */
export default function FocusSourceReadinessR81(){
 const d=FOCUS_R81_SOURCE_READINESS;
 if(!d)return <section aria-label="R81 all FOCUS source readiness"
   className={styles.coverage}>
   <p role="alert">The exact 29-trial / 23-cycle source crosswalk failed validation.
    Source readiness details are withheld; no FDA grade can be released.</p>
 </section>;
 return <section aria-label="R81 all FOCUS source readiness"
   className={styles.coverage}>
  <div className={styles.eyebrow}>MAIN · REVISION 81 · ALL FOCUS SOURCE COVERAGE</div>
  <h2>Every FOCUS trial and provisional FDA application cycle</h2>
  <p className={styles.intro}>This is an <strong>evidence-intake coverage map</strong>,
   not a ranking of drugs, clinical trial outcomes or approval probabilities.
   A source paper indexed by R71 is not independent full-text adjudication,
   and no pivotal paper in the five-case R71 subset does not mean that no paper exists.</p>
  <div className={styles.stats}>
   <div><small>Exact FOCUS trials</small><strong>{d.exactTrials}</strong></div>
   <div><small>Provisional FDA cycles</small><strong>{d.provisionalCycles}</strong></div>
   <div><small>Pivotal original paper leads in R71</small><strong>{d.R71PublicationLeads}</strong></div>
   <div><small>Not indexed in five-study R71</small><strong>{d.remainingNotIndexedInR71}</strong></div>
   <div><small>Verified pre-unblinding SAPs</small><strong>{d.originalSignedProspectiveSAPsVerified}</strong></div>
   <div><small>Signed science reviews</small><strong>{d.independentScientificSignoffs}</strong></div>
  </div>
  <p className={styles.notice}>Current retained registry has primary tables for
   <strong> {d.registryCurrentPrimaryTrials}/29</strong> trials,
   arm-specific safety tables for <strong>{d.registryCurrentSafetyArmTrials}/29</strong>
   and original PDF method-page leads for <strong>{d.registryCurrentMethodPageLeadTrials}/29</strong>.
   These are source availability, not signed assessments.
   All <strong>{d.fullScientificSourceReviewPositions}</strong>
   source-review positions are unassessed. FDA forecast <strong>ABSTAIN</strong>;
   independently measured accuracy <strong>UNAVAILABLE</strong>.</p>
  <p className={styles.footer}>
   <a href="/predictions/evidence-gaps/export" download="focus-29-source-evidence-gaps-r83.csv">
    Download all 29 trial evidence gaps (CSV)
   </a>
   {" · "}One exact NCT per row, with all provisional application-cycle links.
   This is a dated source-research handoff, not FDA prediction accuracy or a clinical score.
  </p>
  <details className={styles.coverageDetails}>
   <summary>Expand all 23 provisional application cycles and their exact NCT evidence status</summary>
   <div className={styles.coverageGrid}>
   {d.applicationGroups.map(group=><article className={styles.coverageGroup} key={group.cycleId}>
    <strong>{group.ticker} · {group.cycleId}</strong>
    <div>{group.trialCount} linked NCT{group.trialCount===1?"":"s"} ·
     {group.originalPublishedMainReportLeads} published pivotal source lead{group.originalPublishedMainReportLeads===1?"":"s"} in R71</div>
    <div>Retained registry primary tables: {group.currentRegistryPrimaryNcts.length}/{group.trialCount}
     {" · "}method PDF page leads: {group.currentMethodPageLeadNcts.length}/{group.trialCount}.
     These count source access, not positive outcomes.</div>
    <ul>{group.ncts.map(nct=>{
      const trial=d.rows.find(x=>x.nct===nct);
      return <li key={nct}>
       <a href={"/predictions/assessment?nct="+nct}>{nct}</a>
       <span> · {trial?.indexedOriginalPivotalPublication?
        "Pivotal publication indexed — not adjudicated":
        "No pivotal report indexed in five-case R71; other public sources may exist"}</span>
       {trial&&<>
        <div className={styles.sourceCounts} aria-label={nct+" retained-source availability"}>
         <span>Primary: {trial.currentRegistryPrimaryTable?"table available":"not posted here"}</span>
         <span>Safety: {trial.currentRegistrySafetyArms?"arm data available":"not posted here"}</span>
         <span>Method PDFs: {trial.retainedMethodPageLeads?"lead indexed":"no lead in snapshot"}</span>
        </div>
        <small>Next evidence step: {trial.currentRegistryPrimaryTable?
          "verify endpoint statistics, analysis population and adverse-event windows against dated original protocol/SAP":
          "seek original sponsor or journal pivotal results and dated protocol/SAP; missing registry tables do not imply trial failure"}.
          Independent reviewer signoff is still required.</small>
       </>}
      </li>;
    })}</ul>
    <small>Authenticated original SAPs 0 · signed reviews 0 · FDA ABSTAIN</small>
   </article>)}
   </div>
  </details>
  <p className={styles.disclaimer}>Application groups are research identities,
   not necessarily separate FDA dossiers. No live FDA grade, historical accuracy or
   approval/CRL probability is established by this source-only crosswalk.</p>
 </section>;
}
