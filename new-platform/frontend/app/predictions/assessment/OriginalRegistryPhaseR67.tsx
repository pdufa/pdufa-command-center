import {FOCUS_R67_PHASE_SOURCE} from "../../../lib/focus-r67-phase-source";
import styles from "./OriginalRegistryPhaseR67.module.css";

/** Immutable R66 original registry labels. Display-only, no phase signoff,
 * trial failure, scientific score or FDA application outcome inferred.
 */
export default function OriginalRegistryPhaseR67({nct}:{nct:string}){
  const source=FOCUS_R67_PHASE_SOURCE;
  if(!source)return <section className={styles.card}
      aria-label="R67 original registry phase source evidence">
    <h2>Phase-first source evidence</h2>
    <p role="alert">Exact original R66 registry phase source integrity or
      membership verification failed. Phase evidence is withheld.</p>
  </section>;
  const study=source.records.find(x=>x.nct===nct);
  if(!study)return <section className={styles.card}
      role="status">No exact-NCT phase source record is available.</section>;
  return <section id="phase-first-original-r67"
      aria-label="R67 original registry phase source evidence" className={styles.card}>
    <div className={styles.eyebrow}>MAIN · REVISION 67 · PHASE FIRST · ORIGINAL REGISTRY RESEARCH</div>
    <h2>Study phase and original source · {study.ticker} / {study.nct}</h2>
    <p className={styles.note}>The source labels below were taken from a dated
      ClinicalTrials.gov registration record and cross-checked against the
      immutable R66 archive. <strong>They are not independent clinical verification,
      proof of efficacy, or the FDA application status.</strong></p>
    <div className={styles.stats}>
      <div><small>Registry-reported trial phase</small><strong>{study.sourcePhase}</strong></div>
      <div><small>Registry study status</small><strong>{study.sourceStatus}</strong></div>
      <div><small>Independent phase review</small><strong>NOT VERIFIED</strong></div>
      <div><small>Clinical assessment level</small><strong>UNASSESSED · SOURCE ONLY</strong></div>
    </div>
    <div className={styles.sourceDate}>
      <span><strong>Registry last update posted:</strong> {study.sourceUpdatedDate}</span>
      <span><strong>Registry status verified month:</strong> {study.registryVerifiedMonth}</span>
      <a href={study.originalRegistryUrl} target="_blank" rel="noopener noreferrer">
        Open original ClinicalTrials.gov study</a>
    </div>
    <details className={styles.details}>
      <summary>Study design, enrollment and original completion dates</summary>
      <div className={styles.detailGrid}>
        <p><strong>Reported allocation:</strong> {study.allocation==="NA"?"N/A (not randomized)":study.allocation}</p>
        <p><strong>Reported masking:</strong> {study.masking}</p>
        <p><strong>Reported enrollment:</strong> {study.enrollment} ({study.enrollmentType.toLowerCase()})</p>
        <p><strong>Primary completion date:</strong> {study.primaryCompletionDate} ({study.primaryCompletionType.toLowerCase()})</p>
      </div>
    </details>
    <details className={styles.details}>
      <summary>Outstanding trial-phase verification and design exceptions · {study.reviewFlags.length}</summary>
      <ul>{study.reviewFlags.map(flag=><li key={flag}>{flag}</li>)}</ul>
      <p>Source missingness, an incomplete recruitment status or an N/A allocation
        cannot be converted into trial failure, a clinical score or an FDA decision.</p>
    </details>
    <p className={styles.status}>
      <strong>Phase source coverage:</strong> {source.ncts}/29 trials ·
      Phase 3 only {source.sourceReportedPhase3Only} ·
      Combined Phase 2/3 {source.sourceReportedCombinedPhase23} ·
      Independent reviewer phase signoffs <strong>0</strong>.
      FDA outcome: <strong>ABSTAIN</strong>; measured accuracy: <strong>NOT CALIBRATED</strong>.
    </p>
    <p className={styles.footer}>Original research evidence:
      <a href={source.archiveUrl} target="_blank" rel="noopener noreferrer">
        Revision 66 immutable source archive</a>.
      Original record hash cross-linked to the previous scientific dossier;
      original protocol/SAP version and signed human phase review still required.
      No science or production writes.</p>
  </section>;
}
