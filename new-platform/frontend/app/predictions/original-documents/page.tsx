import {R86_ORIGINAL_DOCUMENT_MANIFEST} from
 "../../../lib/focus-r86-original-document-inventory";
import OriginalSourceDocumentsR86Client from "./OriginalSourceDocumentsR86Client";
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
