import {FOCUS_R77_LAUNCH_HTN_PUBLISHED_METHODS} from "../../../lib/focus-r77-launch-htn-published-methods";
import styles from "./ScientificOriginalsIntakeR71.module.css";

/** Source-only H1–H7 evidence map. Neither a gatekeeping calculator nor FDA forecast. */
export default function LaunchHtnMethodsR77(){
 const d=FOCUS_R77_LAUNCH_HTN_PUBLISHED_METHODS;
 if(!d)return <section className={styles.shell}
   aria-label="R77 Launch-HTN original H1 H7 published methods">
   <p role="alert">Published statistical-method source mismatch; research panel withheld.</p>
 </section>;
 return <section className={styles.shell}
  aria-label="R77 Launch-HTN original H1 H7 published methods">
  <div className={styles.eyebrow}>MAIN · REVISION 77 · SOURCE-REPORTED STATISTICAL HIERARCHY</div>
  <h3>Launch-HTN · H1–H7 endpoints, missing data and laboratory safety</h3>
  <p className={styles.disclaimer}>This panel transcribes the <strong>published JAMA
     supplementary eFigure 2 and eTables 1–4</strong>, not a verified pre-unblinding
     SAP, reproduced familywise statistical test, or independently signed clinical conclusion.</p>
  <div className={styles.stats}>
   <div><small>Hypotheses in source</small><strong>7 · 1 primary + 6 key secondary</strong></div>
   <div><small>Published diagram arrows</small><strong>8 · no alpha replay</strong></div>
   <div><small>Reported primary contrast</small><strong>{d.primaryPublishedEffect.differenceMmHg} mm Hg · p{d.primaryPublishedEffect.reportedP}</strong></div>
   <div><small>Missing data methodology</small><strong>{d.missingness.imputedDatasets} imputed datasets · independent replication NOT DONE</strong></div>
  </div>
  <details className={styles.details}>
   <summary>Expand H1–H7 endpoints and all eight published gatekeeping arrows</summary>
   <div className={styles.domainGrid}>
    {d.publishedSourceHypotheses.map(h=><article className={styles.domain} key={h.id}>
      <strong>{h.id} · {h.category==="PRIMARY"?"Primary":"Key secondary"}</strong>
      <p>{h.endpoint}</p>
      <span>{h.studyComparison==="WITHIN_PARTICIPANT_NONRANDOMIZED_ESCALATED_SUBSET"?
        "WITHIN-PARTICIPANT ANALYSIS — not a new randomized placebo comparison":
        "Published study comparison — no independent source-grade signature"}</span>
    </article>)}
   </div>
   <ul>{d.graphEdges.map((e,i)=><li key={e.from+"-"+e.to}>
     {e.from} → {e.to} · {e.sourceDiagramTransferLabel==="HALF"?
        "½ of the source-diagram transfer allocation":
        "arrow shown; no explicit numeric fraction on source diagram"}</li>)}</ul>
   <p className={styles.disclaimer}>The graph describes source-reported relationships.
     Failure/success propagation and recycled alpha cannot be inferred from arrows
     alone; no familywise multiplicity calculation has been independently reproduced.</p>
  </details>
  <details className={styles.details}>
   <summary>Missing-data and robustness checks · author-reported only</summary>
   <ul>
     <li>Safety-exposed participants: {d.missingness.denominatorSafetyTreated};
       documented treatment-stop/death intercurrent events: {d.missingness.totalTreatmentDiscontinuationOrDeathIntercurrentEvents}
       ({d.missingness.adverseEventIntercurrentEvents} adverse events, {d.missingness.deathIntercurrentEvents} death)</li>
     <li>Adverse-event-related missing observations: {d.missingness.adverseEventRelatedMissingWeek6}
       at week 6; {d.missingness.adverseEventRelatedMissingWeek12} at week 12.
       Additional MAR observations: {d.missingness.otherMissingMARWeek6} at week 6
       and {d.missingness.otherMissingMARWeek12} at week 12.</li>
     <li>Source-selected methods: treatment-policy retrieved dropouts for adverse-event MNAR;
       5% worst outcome for death; randomized-group MAR for other missing outcomes;
       jump-to-reference fallback if necessary</li>
     <li>Published H1 sensitivity contrasts:
       {d.sensitivityPublished.sensitivity1DifferenceMmHg},
       {d.sensitivityPublished.sensitivity2DifferenceMmHg},
       {d.sensitivityPublished.sensitivity4ObservedCaseDifferenceMmHg} mm Hg
       (each reported p{d.sensitivityPublished.sensitivity1ReportedP});
       original analysis code and seed not independently run</li>
   </ul>
  </details>
  <details className={styles.details}>
   <summary>Source eTable 4 safety observations · separate exposed arms</summary>
   <ul>
    <li>Arms: escalation-option {d.safetyReview.safetyArmDenominators[0]},
       fixed 50 mg {d.safetyReview.safetyArmDenominators[1]},
       placebo {d.safetyReview.safetyArmDenominators[2]} exposed participants</li>
    <li>Serum sodium below 130 mmol/L: {d.safetyReview.serumSodiumBelow130.join(" / ")} people by arm</li>
    <li>Observed potassium 5.6–6.0 mmol/L: {d.safetyReview.serumPotassiumObserved5Point6To6Point0.join(" / ")} people by arm</li>
    <li>Confirmed potassium 5.6–6.0 mmol/L: {d.safetyReview.serumPotassiumConfirmed5Point6To6Point0.join(" / ")} people by arm</li>
   </ul>
   <p className={styles.disclaimer}>These published observations are not proof of drug causality,
     serious-event causality, adjusted exposure risk or overall FDA benefit-risk.</p>
  </details>
  <details className={styles.details}>
   <summary>Six unsigned original-source, statistics and regulatory review gates</summary>
   <ul>{d.reviewGates.map(gate=><li key={gate}>{gate}</li>)}</ul>
  </details>
  <div className={styles.sources}>
   <a href={d.journalOriginalArticle} target="_blank" rel="noopener noreferrer">
    Open original JAMA article and its source PDF supplements</a>
   <a href={d.originalSupplementStableIndex} target="_blank" rel="noopener noreferrer">
    Open the independently indexed published supplement collection</a>
  </div>
  <p className={styles.warning}><strong>Scientific grade: UNASSESSED.</strong>
    Prospectively locked original SAP: NOT VERIFIED.
    Independently reproduced multiplicity: NO.
    Signed independent science reviews: <strong>0</strong>.
    Validated FDA application forecasts: <strong>0/23</strong>.
    Future FDA decision: <strong>ABSTAIN</strong>; timing <strong>UNKNOWN</strong>.
    Published clinical evidence does not authorize a numerical approval probability.</p>
 </section>;
}
