import {FOCUS_R72_CAPR_REGULATORY_SOURCE_CHALLENGE} from "../../../lib/focus-r72-capr-regulatory-source-challenge";
import styles from "./ScientificOriginalsIntakeR71.module.css";

/** Source-only adverse and supportive original regulatory evidence.
 * July 2026 FDA briefing is not a decision on the revised August application.
 */
export default function CaprFdaChallengeR72(){
 const r=FOCUS_R72_CAPR_REGULATORY_SOURCE_CHALLENGE;
 if(!r)return <section aria-label="R72 original regulatory source conflict" role="alert">
  Original FDA-versus-sponsor source identity or release guard failed; comparison withheld.
 </section>;
 return <section className={styles.shell}
   aria-label="R72 original FDA and issuer conflict for NCT05126758">
  <div className={styles.eyebrow}>MAIN · REVISION 72 · ORIGINAL FDA CONTRADICTORY EVIDENCE</div>
  <h3>CAPR / HOPE-3 · FDA vs applicant analysis</h3>
  <p className={styles.disclaimer}>Original FDA advisory material (July 29, 2026) identified important
   differences between the prespecified and later reported analysis. The August amended BLA
   changed the requested emphasis to upper-limb function; a July cardiomyopathy advisory review
   is <strong>not a final ruling on that later refined indication</strong>. This panel is research,
   not a graded prediction.</p>
  <div className={styles.stats}>
   <div><small>Application identity</small><strong>{r.bla} · {r.cycleId}</strong></div>
   <div><small>FDA goal reported by issuer</small><strong>{r.pdufaTarget.date}</strong></div>
   <div><small>Already-observed review-clock event</small>
    <strong>Formal major-amendment extension from {r.pdufaTarget.previousDate}</strong></div>
   <div><small>Future review timing / FDA decision</small>
    <strong>{r.futureTimingForecast} / {r.futureApprovalOrCrlForecast}</strong></div>
  </div>
  <div className={styles.sources}>
   <a target="_blank" rel="noopener noreferrer" href={r.originalFDAReportSource}>
    Original FDA July 29 briefing · primary Table 7, printed pages 39–40</a>
   <a target="_blank" rel="noopener noreferrer" href={r.pdufaTarget.source}>
    Original SEC August 24 amendment and PDUFA extension filing</a>
   <a target="_blank" rel="noopener noreferrer"
     href={r.evidenceChronology[r.evidenceChronology.length-1].source}>
    November 9 issuer cardiac-data update (nominal/subgroup results)</a>
  </div>
  <details className={styles.details} open>
   <summary>Three original-source primary analyses · incompatible endpoint scales</summary>
   <div className={styles.domainGrid}>
    {r.primaryAnalysisComparisons.map(c=><article key={c.id} className={styles.domain}>
     <strong>{c.analysis}</strong>
     <p><strong>Endpoint scale: {c.endpointScale}</strong></p>
     <p>Effect difference: {c.difference} · 95% CI {c.ci} · p={c.p}</p>
     <small>{c.interpretation}. FDA briefing printed page {c.sourcePdfPrintedPage}.</small>
    </article>)}
   </div>
   <p className={styles.disclaimer}>Absolute PUL-score points and percentage-point changes are
    different units. Do not rank those effect sizes directly. The FDA reported sensitivity of
    the result to changed missing-data handling and statistical analysis versions.</p>
  </details>
  <details className={styles.details}>
   <summary>Key secondary LVEF · analysis-version differences</summary>
   <div className={styles.domainGrid}>
    {r.secondaryAnalysisComparisons.map(c=><article className={styles.domain} key={c.id}>
     <strong>{c.analysis}</strong><p>Nominal p={c.p}</p><small>{c.endpointScale}</small>
    </article>)}
   </div>
   <p className={styles.disclaimer}>The issuer's November 9 cardiac update reports
    all-participant randomized LVEF p=0.09; the later subgroup and natural-history comparisons
    are nominal and/or non-randomized. These cannot substitute for the prespecified endpoint gate.</p>
  </details>
  <details className={styles.details}>
   <summary>Eight dated regulator/issuer evidence chronology events</summary>
   <ul>{r.evidenceChronology.map(c=><li key={c.date}>
    <strong>{c.date}:</strong> {c.event} (<a href={c.source}
     rel="noopener noreferrer" target="_blank">original source</a>)
   </li>)}</ul>
  </details>
  <details className={styles.details}>
   <summary>Six unresolved independent scientific and CMC review gates</summary>
   <ul>{r.priorityResearchGates.map(item=><li key={item}>{item}</li>)}</ul>
  </details>
  <p className={styles.warning}>Original FDA first-public publication time and a complete
   post-amendment FDA clinical review are not authenticated in this research record.
   <strong> Signed clinical reviews: 0; science grade: UNASSESSED; approval/CRL: ABSTAIN;
   future timing: UNKNOWN; calibrated accuracy: UNAVAILABLE.</strong>
   Original FDA analysis must not be misrepresented as a finalized post-amendment decision.</p>
 </section>;
}
