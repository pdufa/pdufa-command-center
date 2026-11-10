import {FOCUS_R73_LAUNCH_HTN_DOCUMENT_INDEX} from "../../../lib/focus-r73-launch-htn-document-index";
import styles from "./ScientificOriginalsIntakeR71.module.css";

/** R73: published document *index* only; not original signed locked plan proof. */
export default function LaunchHtnOriginalDocumentsR73(){
 const d=FOCUS_R73_LAUNCH_HTN_DOCUMENT_INDEX;
 if(!d)return <section className={styles.shell}
   aria-label="R73 Launch-HTN published protocol and SAP document index">
   <p role="alert">Original publication document-index validation failed. Links withheld.</p>
 </section>;
 return <section className={styles.shell}
   aria-label="R73 Launch-HTN published protocol and SAP document index">
   <div className={styles.eyebrow}>MAIN · REVISION 73 · DOCUMENT SOURCE DISCOVERY</div>
   <h3>Launch-HTN · seven published protocol, SAP and methods file links</h3>
   <p className={styles.disclaimer}>The public JAMA/PMC article lists
     <strong> 3 protocol versions, 3 statistical-analysis documents, and 1 methods supplement</strong>.
     These are indexed source leads only. The original PDF bytes, signatures,
     prospective plan-lock dates, and first-publication chronology have NOT
     been independently authenticated.</p>
   <div className={styles.sources}>
     <a href={d.originalPublicArticleIndex} target="_blank"
       rel="noopener noreferrer">Open original public JAMA supplement index</a>
   </div>
   <details className={styles.details}>
     <summary>Seven exact original publication supplement links · unverified bytes</summary>
     <ol>{d.documents.map(doc=><li key={doc.filename}>
       <a href={doc.publicOriginalIndexLink} target="_blank" rel="noopener noreferrer">
        Supplement {doc.supplementNumber} · {doc.title}</a>
       <div>ORIGINAL PDF NOT BYTE-VERIFIED · SIGNED SAP/PROTOCOL CHRONOLOGY UNKNOWN</div>
     </li>)}</ol>
   </details>
   <details className={styles.details}>
     <summary>Six outstanding source chronology, statistics and safety review gates</summary>
     <ol>{d.checksRemaining.map(item=><li key={item}>{item}</li>)}</ol>
   </details>
   <p className={styles.warning}><strong>Scientific review remains UNASSESSED.</strong>
    Verified original PDF bytes: <strong>0/7</strong>.
    Signed pre-unblinding statistical plans: <strong>0</strong>.
    Qualified scientific reviews: <strong>0</strong>.
    FDA forecast: <strong>ABSTAIN</strong>; timing <strong>UNKNOWN</strong>.
    This publication index does not create a clinical grade or approval probability.</p>
 </section>;
}
