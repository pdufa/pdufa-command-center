import {R93_PRIORITY_SCIENTIFIC_GATES} from
 "../../../../lib/focus-r93-priority-scientific-gates";
import {R94_ACACIA_COHORT_SAFETY_SOURCE} from
 "../../../../lib/focus-r94-acacia-cross-source-reconciliation";
import {R95_EU_ACACIA_PROTOCOL_IDENTITY} from
 "../../../../lib/focus-r95-eu-protocol-identity-gates";
import styles from "../../evidence-gaps/EvidenceRecoveryBoardR68.module.css";

export const metadata={
 title:"Stage 4 | Priority Original Scientific Authentication Gates",
 description:"Source-linked independent review handoff for ACACIA-HCM and Launch-HTN, no clinical grading or FDA forecasts"
};

export default function PriorityOriginalScientificGatesR93(){
 const d=R93_PRIORITY_SCIENTIFIC_GATES;
 const acacia=R94_ACACIA_COHORT_SAFETY_SOURCE;
 const sourceIdentity=R95_EU_ACACIA_PROTOCOL_IDENTITY;
 if(!d||!acacia||!sourceIdentity)return <main className={styles.coverage}>
  <h1>Priority original scientific evidence review</h1>
  <p role="alert">Original FOCUS evidence and exact scientific blockers did not
   pass locked source integrity checks. No reviewer, SAP, score or FDA
   conclusion is represented as verified.</p>
 </main>;
 return <main className={styles.coverage}>
  <div className={styles.eyebrow}>MAIN · REVISION 95 · STAGE 4 INDEPENDENT SCIENCE EVIDENCE GATES</div>
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
   {c.trial==="ACACIA_HCM"&&
    <details className={styles.coverageDetails} open>
     <summary>Revision 95: correct original EU protocol identity, amendment records and unresolved participant-count conflict</summary>
     <p><b>Exact study identity:</b> {sourceIdentity.exactNct}
      {" · "} EU CTIS {sourceIdentity.euTrialNumber}
      {" · "} Sponsor protocol <strong>{sourceIdentity.sponsorProtocolCode}</strong>
      {" · "} aficamten versus {sourceIdentity.correctComparator.toLowerCase()}.
      The EU record lists {sourceIdentity.CTISPublicDocumentEntries} public
      document <b>entries</b>, including
      {" "}{sourceIdentity.ctisAmendment4ProtocolEntries} Amendment 4 protocol
      listings and {sourceIdentity.ctisAmendment3SynopsisEntries} Amendment 3
      synopsis listing. Their original PDF bytes have <b>not</b> been retrieved.</p>
     <p><a href={sourceIdentity.officialEUHistorySource}
        target="_blank" rel="noopener noreferrer">
         Official EU Clinical Trials Information System study
      </a>
      {" · "}
      <a href={sourceIdentity.publicDocumentIndexSource}
       target="_blank" rel="noopener noreferrer">
       Public CTIS document names and amendment submission chronology
      </a>
     </p>
     <p>The CTIS document index reports {sourceIdentity.plannedInCTIS}
      {" "}planned participants (
      {sourceIdentity.plannedEUMemberStates} in listed EU countries and
      {" "}{sourceIdentity.plannedRestOfWorld} elsewhere). This was a
      <b> planning target</b>, not the 517 later randomized participants.
      CTIS SM-3 submitted {sourceIdentity.ctisSubstantialModification3Submitted}
      {" "}and decided {sourceIdentity.ctisSubstantialModification3Decision}.
      CTIS SM-4 submitted {sourceIdentity.ctisSubstantialModification4Submitted}
      {" "}and decided {sourceIdentity.ctisSubstantialModification4Decision}.
      These EU regulatory records cannot substitute for source-controlled
      final SAP and first-unblinded-access audit.</p>
     <p><b>Wrong-trial safeguard:</b> another public aficamten protocol,
       <code> {sourceIdentity.wrongProtocolCodeExcluded}</code>, concerns
       obstructive HCM versus metoprolol. It is <b>not</b> ACACIA-HCM.
       {" "}<a href={sourceIdentity.confusingOtherTrialProtocolSource}
          target="_blank" rel="noopener noreferrer">
        View distinct journal protocol source (not usable for ACACIA)
       </a>.
     </p>
     <p><b>Participant accounting correction:</b> public sponsor and
      publication descriptions are not yet reconciled. The later August
      sponsor release reports <b>517 randomized and treated</b>, whereas
      an earlier May sponsor release reports <b>516 randomized and treated</b>
      and a secondary publication describes 517 randomized and 516 treated.
      The one-person treatment explanation remains <b>unproven</b>.</p>
     <ul>{sourceIdentity.sourcePublishedCohortClaims.map(v=>
      <li key={v.source}><b>{v.source}:</b> {v.claim}</li>)}</ul>
     <p><a href={sourceIdentity.laterSponsorCohortSource}
       target="_blank" rel="noopener noreferrer">
       Later sponsor source reporting 517 randomized and treated
      </a>. Original CONSORT/first-dose listings, original signed SAP and
       blind-break logs: NOT VERIFIED. FDA forecast: ABSTAIN.</p>
    </details>}
   {c.trial==="ACACIA_HCM"&&<details className={styles.coverageDetails}>
    <summary>Revision 94: cross-source cohort and heart-failure case-definition audit</summary>
    <p>New public-source comparison checked on {acacia.originalSourceDateUtc} UTC.
     The primary NEJM article lists <b>{acacia.randomizedFromNEJM} randomized</b>
     {" "}({acacia.aficamtenRandomized} aficamten,
     {" "}{acacia.placeboRandomized} placebo). A later published clinical appraisal
     describes <b>{acacia.secondaryPaperReportedTreated} treated</b>.
     Earlier research suggested randomized-versus-treated cohorts might
     explain the difference, but the newer sponsor 517 randomized-and-treated
     statement conflicts with that explanation. The counts are
     <b> not reconciled without original CONSORT and first-dose listings</b>.
    </p>
    <p>For heart-failure serious adverse events, the earlier case figures
     retained for review were
     {" "}<b>{acacia.earlySourceReportedHfSAECasesAficamten}/
      {acacia.earlySourceReportedHfSAECasesPlacebo}</b>.
     The later October sponsor report describes
     {" "}<b>{acacia.octoberSponsorHfSAECasesAficamten}/
      {acacia.octoberSponsorHfSAECasesPlacebo}</b>.
     Within the later aficamten count,
     {" "}{acacia.octoberSponsorHFWithLVEFBelow50}
     {" "}cases were reported with LVEF below 50%, and
     {" "}{acacia.octoberSponsorHFWithoutLVEFBelow50}
     {" "}without that association. These later subcategories
     add up internally but do <b>not</b> reconcile the earlier 11/1 source.
     Original event/cutoff and exposure evidence remains missing.</p>
    <p>A published responder-analysis author statement says the analysis
     entered the SAP before database lock and unblinding. That claim is
     <b> not</b> independently authenticated signatory or access-log evidence.
     Original public NEJM protocol/appendix PDF bytes were not retrieved
     in this pass.</p>
    <details className={styles.coverageDetails}>
     <summary>See all {acacia.numberOfOriginalResearchSourceLinks} dated publication and sponsor claims</summary>
     <ul>{acacia.sourceLinks.map(s=><li key={s.id}>
       <b>{s.type}</b> · {s.published}
       <p>{s.claim}</p>
       <a href={s.url} target="_blank" rel="noopener noreferrer">
        Open original publication or issuer statement
       </a>
     </li>)}</ul>
    </details>
    <details className={styles.coverageDetails}>
     <summary>Required original cohort, SAE and SAP authenticity follow-ups</summary>
     <ul>{acacia.reviewNeeded.map(s=><li key={s}>{s}</li>)}</ul>
    </details>
    <p><b>Evidence classification:</b> public reported-source comparison.
     Cohort case-level accounting: UNVERIFIED. HF clinical adjudication:
     UNVERIFIED. Original prospectively signed SAP: UNVERIFIED.
     Qualified independent review: NOT SIGNED.
     FDA outcome forecast: ABSTAIN.</p>
   </details>}
   {c.newlyIndexedPublisherProtocolAttachmentLead&&
     <details className={styles.coverageDetails}>
      <summary>New publisher-indexed ACACIA-HCM original protocol and appendix leads</summary>
      <p>The original New England Journal of Medicine article published
       {" "}{c.newlyIndexedPublisherProtocolAttachmentLead.sourcePublished}
       {" "}lists a downloadable <b>trial protocol</b>
       {" "}(<code>{c.newlyIndexedPublisherProtocolAttachmentLead.advertisedProtocolPdfFilename}</code>)
       and a <b>supplementary appendix</b>
       {" "}(<code>{c.newlyIndexedPublisherProtocolAttachmentLead.advertisedAppendixPdfFilename}</code>).
       These are newly indexed public attachment leads, not authenticated final
       signed SAP files. Exact supplement bytes have not been captured
       in this revision.</p>
      <p>The paper reports randomized assignment to
       {" "}{c.newlyIndexedPublisherProtocolAttachmentLead.sourceReportedRandomizedAficamten}
       {" "}aficamten and
       {" "}{c.newlyIndexedPublisherProtocolAttachmentLead.sourceReportedRandomizedPlacebo}
       {" "}placebo participants, totaling
       {" "}{c.newlyIndexedPublisherProtocolAttachmentLead.sourceReportedTotalRandomized}.
       The earlier 516-versus-517 reporting question remains open until
       original analysis-set and treated-population listings are reconciled.</p>
      <p><a href={c.newlyIndexedPublisherProtocolAttachmentLead.sourceArticle}
       target="_blank" rel="noopener noreferrer">
       Open original NEJM article and its advertised supplementary documents
      </a>. Final controlled SAP signatures, blind-break audit and independent
       clinical adjudication: NOT VERIFIED.</p>
     </details>}
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
