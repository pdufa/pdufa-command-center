import {R93_PRIORITY_SCIENTIFIC_GATES} from
 "../../../../lib/focus-r93-priority-scientific-gates";
import {R94_ACACIA_COHORT_SAFETY_SOURCE} from
 "../../../../lib/focus-r94-acacia-cross-source-reconciliation";
import {R95_EU_ACACIA_PROTOCOL_IDENTITY} from
 "../../../../lib/focus-r95-eu-protocol-identity-gates";
import R103_PAGE_CENSUS from "../../../../data/focus-r103-acacia-original-pdf-structural-census-20261110.json";
import R101_TEXT_DIAGNOSTICS from "../../../../data/focus-r101-acacia-pdf-text-diagnostic-readback-20261110.json";
import {R98_ACACIA_CTIS_ORIGINAL_PDF_RECEIPTS} from "../../../../lib/focus-r98-ctis-original-pdf-receipts";
import styles from "../../evidence-gaps/EvidenceRecoveryBoardR68.module.css";

export const metadata={
 title:"Stage 4 | Priority Original Scientific Authentication Gates",
 description:"Source-linked independent review handoff for ACACIA-HCM and Launch-HTN, no clinical grading or FDA forecasts"
};

export default function PriorityOriginalScientificGatesR93(){
 const d=R93_PRIORITY_SCIENTIFIC_GATES;
 const acacia=R94_ACACIA_COHORT_SAFETY_SOURCE;
 const sourceIdentity=R95_EU_ACACIA_PROTOCOL_IDENTITY;
 const originalFiles=R98_ACACIA_CTIS_ORIGINAL_PDF_RECEIPTS;
 if(!d||!acacia||!sourceIdentity||!originalFiles)return <main className={styles.coverage}>
  <h1>Priority original scientific evidence review</h1>
  <p role="alert">Original FOCUS evidence and exact scientific blockers did not
   pass locked source integrity checks. No reviewer, SAP, score or FDA
   conclusion is represented as verified.</p>
 </main>;
 return <main className={styles.coverage}>
  <div className={styles.eyebrow}>MAIN · REVISION 103 · STAGE 4 INDEPENDENT SCIENCE EVIDENCE GATES</div>
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
    R103_PAGE_CENSUS.nct==="NCT06081894"&&
    R103_PAGE_CENSUS.protocol==="CY 6033"&&
    R103_PAGE_CENSUS.FDAForecast==="ABSTAIN"&&
    <details className={styles.coverageDetails}>
     <summary>Revision 103: verified original-PDF page structure (not complete page text)</summary>
     <p>Original PDF byte checks passed on all four source documents. Only the
      Greek AM4 protocol has a structurally consistent page count.
      Compressed PDF object streams prevent treating the other page-object
      counts as complete page totals.</p>
     <ul>{R103_PAGE_CENSUS.documents.map(d=>
      <li key={d.key}><b>{d.key}</b>:
       {" "}{d.structuralPageDictionariesFound} page dictionaries detected;
       {" "}{d.objectStreams} compressed object-stream containers;
       {" "}{d.structurallyConsistent?"structural page count consistent":"page count not independently verified"}.
       {" "}<a href={"/predictions/scientific-reconciliation/priority-gates/ctis-page-census?doc="+encodeURIComponent(d.key)}
       target="_blank" rel="noopener noreferrer">Inspect original PDF structure</a>
      </li>)}</ul>
     <p><b>Do not use these counts as clinical page citations.</b>
      Full page text, signed prospective SAP chronology and independent
      scientific review remain unverified. FDA forecast: ABSTAIN.</p>
    </details>}
   {c.trial==="ACACIA_HCM"&&
    R101_TEXT_DIAGNOSTICS.exactNct==="NCT06081894"&&
    R101_TEXT_DIAGNOSTICS.protocol==="CY 6033"&&
    R101_TEXT_DIAGNOSTICS.FDAForecast==="ABSTAIN"&&
    R101_TEXT_DIAGNOSTICS.completeOriginalDocumentTextExtracted===false&&
    <details className={styles.coverageDetails} open>
     <summary>Revision 101: original-PDF text extraction coverage (partial, not a scientific review)</summary>
     <p>Four original CTIS documents are source-hash verified, but the initial
      bounded text-operator extractor recovered only
      {" "}<b>{R101_TEXT_DIAGNOSTICS.totalTextOperatorChunks}</b> short text
      operator fragments across them. This is not full text, page numbering,
      an authenticated signed SAP or a completed scientific review.</p>
     <ul>{R101_TEXT_DIAGNOSTICS.originalDocuments.map(d=>
      <li key={d.key}><b>{d.key}</b>:
       {" "}{d.textOperatorChunks} text fragments;
       {" "}{d.streams} PDF streams inspected;
       {" "}{d.foundTerms.length?("detectable terms: "+d.foundTerms.join(", ")):"no matching terms detected"}
       . <a href={"/predictions/scientific-reconciliation/priority-gates/ctis-text-index?doc="+encodeURIComponent(d.key)}
          target="_blank" rel="noopener noreferrer">
         View original PDF text-operator diagnostic
       </a></li>)}</ul>
     <p><b>Important:</b> zero extracted fragments is not proof of an
      empty document. PDF text encoding, fonts and array operators may be
      unsupported. Original page-level endpoint comparison and controlled
      SAP approval chronology remain NOT VERIFIED.
      {" "}Original gates still open: ACACIA {R101_TEXT_DIAGNOSTICS.acaciaEvidenceGatesStillOpen},
      Launch {R101_TEXT_DIAGNOSTICS.launchEvidenceGatesStillOpen}.
      FDA forecast: ABSTAIN.</p>
    </details>}
   {c.trial==="ACACIA_HCM"&&<details className={styles.coverageDetails} open>
    <summary>R98 original public EU protocol PDFs: 4 byte-verified source receipts</summary>
    <p><b>{originalFiles.originalPdfFilesAvailable}</b> genuine CTIS PDF files
     retrieved through the official CTIS document service;
     <b> {originalFiles.originalTotalBytesSourceVerified.toLocaleString()} bytes</b>
     with SHA-256 checksums and original PDF header/EOF verification.
     <b> {originalFiles.originalPdfFilesPermanentlyArchived}</b> copies
     permanently archived in this repository;
     <b> {originalFiles.originalDocumentsScientificallyPageReviewed}</b> documents
     independently inspected page by page. These results verify original
     public PDF bytes at retrieval, not an authenticated final signed SAP.</p>
    <ul>{originalFiles.originalDocuments.map(x=><li key={x.key}>
     <b>{x.title}</b> — version {x.manualVersion},
     {" "}{x.byteCount.toLocaleString()} bytes.
     <div>Original public PDF SHA-256: <code>{x.sha256}</code></div>
     <a href={"/predictions/scientific-reconciliation/priority-gates/ctis-pdf-check?doc="+encodeURIComponent(x.key)+"&download=1"}>
      Download SHA-256 verified original PDF for independent review
     </a>
     {" · "}
     <a href={x.originalSourceUrl} target="_blank" rel="noopener noreferrer">
      Official CTIS source
     </a>
     <div>Permanent file archive: NO. Original PDF page-level
      scientific assessment: NOT COMPLETED. Signed prospective SAP: NOT VERIFIED.</div>
    </li>)}</ul>
    <p>Acacia source gates still unresolved:
     {" "}{originalFiles.ACACIAOriginalGatesUnresolved}.
     Launch-HTN unresolved: {originalFiles.launchOriginalGatesUnresolved}.
     FDA forecast: ABSTAIN.</p>
   </details>}
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
