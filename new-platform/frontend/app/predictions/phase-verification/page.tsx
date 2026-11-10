import {
  R85_PHASE_MANIFEST
} from "../../../lib/focus-r85-registry-phase-crosscheck";
import styles from "../evidence-gaps/EvidenceRecoveryBoardR68.module.css";

export const metadata={
 title:"FOCUS Phase-First Original-Registry Cross-Check | MAIN R85",
 description:"Source-only comparison of 29 locked FOCUS NCTs against current ClinicalTrials.gov; not independent phase signoff"
};
export default function PhaseVerificationR85Page(){
 const manifest=R85_PHASE_MANIFEST;
 if(!manifest)return <main className={styles.coverage}>
  <h1>Phase-first original-source verification</h1>
  <p role="alert">The archived 29-trial phase source failed exact-population integrity checks.
   Registry cross-checks are withheld until the source record is reconciled.</p>
 </main>;
 return <main className={styles.coverage}>
  <div className={styles.eyebrow}>MAIN · REVISION 85 · STEP 1 SOURCE-CHECK GATE</div>
  <h1>Phase-first original-source verification</h1>
  <p className={styles.intro}>{manifest.banner} Archived registry source observed
   <strong> {manifest.sourceObservedOn}</strong>.
   The checks run only for the exact original NCTs in the locked FOCUS set.
   A field match is not a signed phase review and does not verify FDA approval.</p>
  <div className={styles.stats}>
   <div><small>Exact FOCUS trial records</small><strong>{manifest.exactTrials}</strong></div>
   <div><small>Registry says Phase 3</small><strong>{manifest.sourceReportedPhase3}</strong></div>
   <div><small>Registry says Phase 2/3</small><strong>{manifest.sourceReportedCombinedPhase23}</strong></div>
   <div><small>Independently signed phase reviews</small><strong>{manifest.independentlySignedPhaseReviews}</strong></div>
  </div>
  <p className={styles.notice}>
   Every &quot;Check current registry&quot; link fetches only that NCT from the official
   public ClinicalTrials.gov v2 API, then compares its phase, enrollment,
   design, study status and timestamp fields against the archived source.
   A mismatch is a <strong>review request</strong>, never an automatic
   clinical pass or fail. API errors do not silently count as matches.
   Full SAP authentication and qualified independent phase review remain outstanding.
  </p>
  <div className={styles.coverageGrid}>
   {manifest.rows.map(x=><article className={styles.coverageGroup} key={x.nct}>
    <strong>{x.ticker} · {x.nct}</strong>
    <div>{x.registryReportedPhase} · {x.registryReportedStatus}</div>
    <div><b>Review order:</b> {x.phaseFirstReviewPriority}</div>
    <div>Original registry updated {x.archivedSourceUpdatedDate}
     {" · "} last verified {x.archivedRegistryVerifiedMonth}</div>
    <div>Design: {x.allocation} · {x.masking} · enrollment {x.enrollment} ({x.enrollmentType})</div>
    <div>Reported primary completion {x.primaryCompletionDate} ({x.primaryCompletionType})</div>
    <div>Retained result/safety fields:
     {x.primaryTablePresentInRetainedSource?" primary indexed":" primary not indexed"};
     {x.safetyArmsPresentInRetainedSource?" safety indexed":" safety not indexed"}</div>
    <p><a href={"/predictions/phase-verification/check?nct="+x.nct}
      target="_blank" rel="noopener noreferrer">
      Check current ClinicalTrials.gov fields (live, JSON)
    </a>{" · "}
    <a href={x.sourceUrl} target="_blank" rel="noopener noreferrer">
      Open original registry study
    </a></p>
    <details className={styles.coverageDetails}>
      <summary>Original-source identity and required independent review</summary>
      <p><small>Archived original registry SHA-256:
       <code>{x.archivedRegistrySha256}</code></small></p>
      <p>Linked provisional application cycles: {x.cycleIds.join(", ")}</p>
      <p>Authenticate original signed protocol and SAP, lock chronology, design,
       analyses and adverse-event definitions; qualified independent phase review:
       <strong> NOT SIGNED</strong>. No grade or forecast released.</p>
    </details>
   </article>)}
  </div>
  <p className={styles.disclaimer}><a href="/predictions/evidence-gaps">
    Return to all 29 source gaps and 23 provisional FDA applications
  </a>. Trial registry dates and phase classifications can change; source
  availability is not treatment safety, trial success or a calibrated FDA prediction.</p>
 </main>;
}
