import {R93_PRIORITY_SCIENTIFIC_GATES} from
 "../../../../lib/focus-r93-priority-scientific-gates";
import styles from "../../evidence-gaps/EvidenceRecoveryBoardR68.module.css";

export const metadata={
 title:"Stage 4 | Priority Original Scientific Authentication Gates",
 description:"Source-linked independent review handoff for ACACIA-HCM and Launch-HTN, no clinical grading or FDA forecasts"
};

export default function PriorityOriginalScientificGatesR93(){
 const d=R93_PRIORITY_SCIENTIFIC_GATES;
 if(!d)return <main className={styles.coverage}>
  <h1>Priority original scientific evidence review</h1>
  <p role="alert">Original FOCUS evidence and exact scientific blockers did not
   pass locked source integrity checks. No reviewer, SAP, score or FDA
   conclusion is represented as verified.</p>
 </main>;
 return <main className={styles.coverage}>
  <div className={styles.eyebrow}>MAIN · REVISION 93 · STAGE 4 INDEPENDENT SCIENCE EVIDENCE GATES</div>
  <h1>Priority original scientific evidence checklist</h1>
  <p className={styles.intro}>{d.notice} Evidence baseline:
   {" "}<strong>{d.datedSourceReview} UTC</strong>.</p>
  <div className={styles.stats}>
   <div><small>Exact FOCUS trial universe</small>
    <strong>{d.exactFOCUSTrialsUnaffected}</strong></div>
   <div><small>Priority source-review trials</small>
    <strong>{d.priorityOriginalTrialCases}</strong></div>
   <div><small>Open original-evidence verification gates</small>
    <strong>{d.unresolvedAuthenticatedScienceRequirements}</strong></div>
   <div><small>Authenticated signed prospective SAPs</small>
    <strong>{d.independentlyVerifiedSignedProspectiveSAPs}</strong></div>
   <div><small>Qualified independent scientific signoffs</small>
    <strong>{d.qualifiedIndependentScienceSignoffs}</strong></div>
   <div><small>Validated FDA forecasts</small>
    <strong>{d.validatedFDAPredictions}</strong></div>
  </div>
  <p className={styles.notice}>
    <a href="/predictions/scientific-reconciliation/priority-gates/export">
      Export 11 original-evidence requirements to CSV for independent review
    </a>.
    This research handoff contains dated public sources and follow-up
    requirements only. It does not mark an SAP verified, an assessment graded
    or an application approved. Authorized reviewers must examine
    original controlled records, not simply confirm publication dates.
  </p>
  {d.cases.map(c=><section key={c.nct}>
   <h2>{c.trial==="ACACIA_HCM"?"ACACIA-HCM":"Launch-HTN"} · {c.ticker} · {c.nct}</h2>
   <p><b>Trial phase:</b> {c.phase}. Provisional review application:
    {" "}{c.applicationCycles.join(", ")}.
    {" "}<a href={c.originalRegistryUrl}
      target="_blank" rel="noopener noreferrer">
      Official ClinicalTrials.gov record
    </a>.
   </p>
   <p className={styles.notice}>{c.timelineSummary}</p>
   {c.trial==="ACACIA_HCM"?<p>
     Four preserved exact historical registry versions:
     {" "}<a href="https://clinicaltrials.gov/study/NCT06081894?tab=history"
     target="_blank" rel="noopener noreferrer">View public version history</a>.
     The documented original comparison shows {d.acaciaRegistryPrimaryEndpointsVersion26}
     {" "}primary endpoint in v26 and {d.acaciaRegistryPrimaryEndpointsVersion27}
     {" "}in v27. Their pre-unblinding effective SAP approval remains unknown.
   </p>:<p>
     The {d.launchPublishedSAPImprint} published SAP imprint predates the
     {" "}{d.launchPublicToplineDate} public topline disclosure. This does not
     establish the real database-lock or blind-break date.
   </p>}
   <div className={styles.coverageGrid}>
    {c.gates.map(g=><article className={styles.coverageGroup}
      key={c.nct+":"+g.id}>
      <strong>{g.title}</strong>
      <div><b>Gate:</b> <code>{g.id}</code></div>
      <div><b>Research evidence state:</b> {g.sourceStatus}</div>
      <div><b>Review order:</b> Priority {g.reviewPriority}
       {" · "}<b>Authenticated / signed:</b> NO</div>
      <p><b>Scientific question:</b> {g.scientificQuestion}</p>
      <details className={styles.coverageDetails}>
       <summary>View exact evidence and required independent proof</summary>
       <p><b>Original source evidence currently held:</b> {g.existingEvidence}</p>
       <p><b>Required original approval or safety proof:</b>
        {" "}{g.originalProofRequired}</p>
       <p><a href={g.sourceUrl}
        target="_blank" rel="noopener noreferrer">
        {g.sourceEvidenceLabel}
       </a>{" · "}
       <a href={g.storedResearchReceiptUrl}
        target="_blank" rel="noopener noreferrer">
        Open original repository evidence receipt
       </a>.</p>
       <p>Interpretation: published research lead only.
        Formal prospective SAP/source custody verification:
        NOT AUTHENTICATED. Independent signed review:
        NOT COMPLETED.</p>
      </details>
      <p><small>Qualified original-source gate:
       NOT VERIFIED. Clinical pass/fail: NOT ASSIGNED.
       Regulatory outcome: ABSTAIN.</small></p>
     </article>)}
   </div>
  </section>)}
  <p className={styles.footer}>
   <a href="/predictions/scientific-reconciliation/protocol-crosswalk">
    Return to 12-trial current registry endpoint text comparison
   </a>{" · "}
   <a href="/predictions/source-recovery">
    Return to original journal/issuer source recovery
   </a>{" · "}
   <a href="/predictions/original-documents/chronology">
    Review archived public SAP chronology
   </a>.
  </p>
 </main>;
}
