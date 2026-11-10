import {R88_SOURCE_CHRONOLOGY} from
 "../../../../lib/focus-r88-source-chronology-triage";
import styles from "../../evidence-gaps/EvidenceRecoveryBoardR68.module.css";

export const metadata={
 title:"Stage 4 | Original SAP chronology: source-date reconciliation (R88)",
 description:"Dated public protocol/SAP file metadata versus original registry primary completion, not verified prospective signing"
};
export default function SourceChronologyR88Page(){
 const d=R88_SOURCE_CHRONOLOGY;
 if(!d)return <main className={styles.coverage}>
  <h1>Original SAP chronology verification</h1>
  <p role="alert">The dated source receipt and original 29-trial evidence
   failed integrity checks. Chronology is withheld; no scientific grades or
   FDA decisions can be inferred.</p>
 </main>;
 return <main className={styles.coverage}>
   <div className={styles.eyebrow}>MAIN · REVISION 88 · STEP 2 ORIGINAL DOCUMENT CHRONOLOGY</div>
   <h1>Original SAP dates, registry upload chronology and independent review gaps</h1>
   <p className={styles.intro}>{d.notice}
    <strong> Source receipt: {d.observationDateUtc} UTC.</strong>
   </p>
   <div className={styles.stats}>
    <div><small>Exact FOCUS trials</small><strong>{d.trialCount}</strong></div>
    <div><small>Public PDF files fingerprinted</small><strong>{d.listedPdfFiles}</strong></div>
    <div><small>Trials without current registry files</small><strong>{d.trialsWithoutListedPdf}</strong></div>
    <div><small>SAP listing dates after primary completion</small><strong>{d.sapListedDocumentDatesAfterPrimaryCompletion}/12</strong></div>
    <div><small>Authentic prospective SAPs certified</small><strong>{d.authenticatedProspectiveSAPs}</strong></div>
    <div><small>Qualified medical signoffs</small><strong>{d.independentSignedMedicalReviews}</strong></div>
   </div>
   <p className={styles.notice}>
    <strong>Interpret these comparisons carefully.</strong> The registry primary-completion
    date is <strong>not</strong> the database-lock date, the first blind-break date,
    or the date a final SAP was approved. A listed date after primary completion
    can represent a later amendment or document version; a listed date before
    primary completion cannot prove final prospective approval. All 23 file
    uploads are later than that milestone in this archived cohort. None has
    a prospectively authenticated signed timeline in this research review.
   </p>
   <p className={styles.footer}>
    Every source file below retains its public PDF link, recorded SHA-256,
    document date and public upload timestamp; exact trial and application-cycle
    identities are locked to the 29/23 research snapshot. Source timestamp
    timezone is unspecified. No patient-level reanalysis, scientific grading,
    or FDA probability is performed by these comparisons.
   </p>
   <div className={styles.coverageGrid}>
     {d.rows.map(row=><article className={styles.coverageGroup} key={row.nct}>
       <strong>{row.ticker} · {row.nct}</strong>
       <div>{row.reportedPhase} · primary completion
        <b> {row.archivedPrimaryCompletionDate}</b>
        {" "}({row.archivedPrimaryCompletionType}, registry-reported)</div>
       {row.originalPilot&&<div>
        <b>Priority source pilot:</b> {row.originalPilot==="ACACIA_HCM"?
          "ACACIA-HCM · original dual-primary and safety chronology":
          "Launch-HTN · original SAP and blind-break chronology"}
       </div>}
       <div><b>Source intake state:</b> {
        row.sourcePdfFiles.length===0?
          "No current public protocol/SAP listing — search other originals":
        row.sapDateChronologyState==="LISTED_SAP_DATE_AFTER_PRIMARY_COMPLETION_RECONCILE_VERSION"?
          "Listed SAP document date later than primary completion — reconcile version approval":
          "Listed SAP document date not later than primary completion — verify final signature"}
       </div>
       <div>Provisional FDA application(s): {row.cycleIds.join(", ")}</div>
       <p><b>Next original evidence:</b> {row.nextRequiredProof}</p>
       <details className={styles.coverageDetails}>
        <summary>Open {row.sourcePdfFiles.length} date-stamped original-file leads and SHA-256 receipts</summary>
        {row.sourcePdfFiles.length===0?
         <p>No protocol/SAP PDF is listed in this dated current-registry
          snapshot. Historical versions, sponsor clinical study reports,
          journal appendices or regulator documents may still be available.
          Lack of a current file is not a negative efficacy finding.</p>:
         <ul>{row.sourcePdfFiles.map(doc=><li key={doc.filename}>
           <b>{doc.filename}</b>
           <div>Document listing date: <strong>{doc.documentDate}</strong>;
            public upload time: <strong>{doc.registryUploadDate}</strong>
            {" "}(registry timezone not specified)</div>
           <div>Document listed date versus primary completion:
            <strong> {doc.printedDateComparedToCompletion==="AFTER"?"after":"on or before"}</strong>.
            Registry upload date versus primary completion:
            <strong> {doc.uploadComparedToCompletion==="AFTER"?"after":"on or before"}</strong>.
           </div>
           <div><a href={doc.sourcePdfUrl} target="_blank"
             rel="noopener noreferrer">Open public original PDF</a>
             {" · "}{doc.sizeBytes.toLocaleString()} bytes
             {" · "}{doc.listsProtocol?"Protocol":""}
             {doc.listsProtocol&&doc.listsSAP?" and ":""}
             {doc.listsSAP?"SAP":""}</div>
           <div>SHA-256 readback: <code>{doc.sha256}</code></div>
         </li>)}</ul>}
       </details>
       <p><small>Signed final prospective SAP: NOT VERIFIED.
        First unblinded-access audit: NOT VERIFIED.
        Qualified scientific review: NOT SIGNED.
        FDA outcome forecast: ABSTAIN.</small></p>
       <a href={row.registryStudyUrl} target="_blank" rel="noopener noreferrer">
        Open official ClinicalTrials.gov study
       </a>
     </article>)}
   </div>
   <p className={styles.footer}>
    <a href="/predictions/source-recovery">
      Continue Step 2: recover the 17 original-source gaps from existing journals and official historical versions
    </a>
   </p>
   <p className={styles.footer}>
    <a href="/predictions/original-documents">
      Return to live original protocol/SAP source inventory
    </a>
    {" · "}
    <a href="/predictions/phase-verification">
      Step 1 registry phase verification
    </a>
   </p>
 </main>;
}
