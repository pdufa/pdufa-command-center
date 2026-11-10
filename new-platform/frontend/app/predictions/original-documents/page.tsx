import {R86_ORIGINAL_DOCUMENT_MANIFEST} from
 "../../../lib/focus-r86-original-document-inventory";
import OriginalSourceDocumentsR86Client from "./OriginalSourceDocumentsR86Client";
import datedSourceAudit from "../../../data/focus-r86-live-source-census-20261110.json";
import datedPdfByteAudit from "../../../data/focus-r87-public-pdf-byte-receipts-20261110.json";
import styles from "../evidence-gaps/EvidenceRecoveryBoardR68.module.css";

export const metadata={
 title:"Stage 4 Step 2 | 29-trial Original Protocol and SAP Source Inventory",
 description:"Read-only live ClinicalTrials.gov protocol/SAP/document/posted result source metadata, no scientific signoff"
};
export default function OriginalDocumentsR86Page(){
 const d=R86_ORIGINAL_DOCUMENT_MANIFEST;
 if(!d)return <main className={styles.coverage}>
  <h1>Stage 4 Step 2 — original scientific source reconciliation</h1>
  <p role="alert">Exact roster or original-source integrity checks failed.
   The source checklist is withheld and no clinical conclusion is valid.</p>
 </main>;
 return <main className={styles.coverage}>
  <div className={styles.eyebrow}>MAIN · REVISION 86 · STEP 2 ORIGINAL DOCUMENT INTAKE</div>
  <h1>Original protocols, SAPs and registry results</h1>
  <p className={styles.intro}>{d.notice}</p>
  <div className={styles.stats}>
   <div><small>Exact FOCUS NCTs</small><strong>{d.exactTrials}</strong></div>
   <div><small>Provisional FDA applications</small><strong>{d.provisionalApplications}</strong></div>
   <div><small>Pivotal report leads in five-case subset</small><strong>{d.knownPivotalReportSourceLeads}</strong></div>
   <div><small>Authenticated original signed SAPs</small><strong>{d.independentSignedSAPsAuthenticated}</strong></div>
  </div>
  <p className={styles.notice}>Two prioritized source-reconciliation pilots:
   ACACIA-HCM and Launch-HTN. The retained Launch-HTN case has
   <strong> {d.knownLaunchDocumentaryBlockers} authenticated-source requirements</strong>;
   ACACIA-HCM has
   <strong> {d.knownAcaciaDocumentaryBlockers} open source/denominator questions</strong>.
   Neither has independently authenticated pre-unblinding SAP chronology.
   The remaining trials still need original document acquisition and qualified review.</p>

  <div className={styles.stats} aria-label="Dated original-source readback">
    <div><small>2026-11-10 live registry reads</small>
      <strong>{datedSourceAudit.successfulHttp200}/{datedSourceAudit.totalExactNcts}</strong></div>
    <div><small>Trial records listing a protocol</small>
      <strong>{datedSourceAudit.trialsWithProtocolListing}</strong></div>
    <div><small>Trial records listing an SAP</small>
      <strong>{datedSourceAudit.trialsWithSAPListing}</strong></div>
    <div><small>Distinct uploaded file listings</small>
      <strong>{datedSourceAudit.documentListings}</strong></div>
    <div><small>Records with posted aggregate results</small>
      <strong>{datedSourceAudit.trialsWithPostedAggregateResults}</strong></div>
  </div>
  <div className={styles.stats} aria-label="Dated public PDF byte receipts">
   <div><small>Public protocol/SAP PDF files SHA-256 fingerprinted</small>
     <strong>{datedPdfByteAudit.publiclyDownloadedAndSha256Fingerprinted}/{datedPdfByteAudit.exactCurrentPublicDocumentListings}</strong></div>
   <div><small>Trials with fingerprinted source PDFs</small>
     <strong>{datedPdfByteAudit.distinctNctsWithFingerprintedPdf}/29</strong></div>
   <div><small>Authenticated signed original SAPs</small>
     <strong>{datedPdfByteAudit.originalSignedProspectiveSAPVersionsAuthenticated}</strong></div>
  </div>
  <p className={styles.footer}>Source-byte fingerprint receipt dated
   <strong> {datedPdfByteAudit.observationDateUtc} UTC</strong>.
   Across the listed public PDFs, <strong>
   {datedPdfByteAudit.records.reduce((sum,row)=>sum+row.byteCount,0).toLocaleString()}
   </strong> bytes were retrieved and SHA-256-fingerprinted. That is a
   public source-byte check only, not prospective signing, source-custodian
   attestation, scientific review, or FDA prediction.</p>
  <p className={styles.footer}>Dated source-observation receipt:
   <strong> {datedSourceAudit.observationDateUtc} UTC</strong>.
   These are observed public document and results listings, not independent
   science reviews, current official FDA application statuses, or
   authenticated pre-unblinding SAPs. One record lists a combined protocol/SAP
   document. Use the check button to re-query the official registry on demand.</p>
  <p className={styles.footer}>
    <a href="/predictions/original-documents/chronology">
      Open Step 2 original SAP document-date and upload chronology for all 29 trials
    </a>
    {" · "} This compares public file dates to registry primary completion,
    not verified unblinding, final database lock, or signed SAP certification.
  </p>
  <p className={styles.footer}>
    <a href="/predictions/source-recovery">
      Source recovery for 17 FOCUS trials without current registry protocol/SAP files
    </a>
    {" · "} Five have known original journal leads in the five-case research archive.
  </p>
  <OriginalSourceDocumentsR86Client rows={d.rows}/>
  <p className={styles.disclaimer}><a href="/predictions/phase-verification">
   Back to Step 1 phase-source checks
  </a>{" · "}<a href="/predictions/evidence-gaps">
   29-trial and 23-cycle evidence gaps
  </a>. A sponsor-uploaded document listing is not a verified signed original;
   a posted primary endpoint is not a favorable decision;
   FDA forecasts remain ABSTAIN with no calibrated accuracy.
  </p>
 </main>;
}
