import {FOCUS_R71_PIVOTAL_EVIDENCE_INTAKE} from "../../../lib/focus-r71-pivotal-evidence-intake";
import styles from "./ScientificOriginalsIntakeR71.module.css";
import CaprFdaChallengeR72 from "./CaprFdaChallengeR72";
import LaunchHtnOriginalDocumentsR73 from "./LaunchHtnOriginalDocumentsR73";
import LaunchHtnSourceChronologyR75 from "./LaunchHtnSourceChronologyR75";
import LaunchHtnMethodsR77 from "./LaunchHtnMethodsR77";

/** Scientific source lead queue only. Source-reported p values do not qualify
 * a predictive approval/CRL grade or original protocol lock verification.
 */
export default function ScientificOriginalsIntakeR71({nct}:{nct:string}){
 const r=FOCUS_R71_PIVOTAL_EVIDENCE_INTAKE;
 if(!r)return <section aria-label={"R71 pivotal source method intake for "+nct}
   className={styles.shell}><p role="alert">
   Archived original PMID, trial-identity or reviewer-release source validation failed.
   Research source details are withheld.
  </p></section>;
 const trial=r.fiveRecords.find(t=>t.nct===nct);
 if(!trial)return null;
 return <><section className={styles.shell}
   aria-label={"R71 pivotal source method intake for "+nct}>
   <div className={styles.eyebrow}>MAIN · REVISION 71 · POST-PUBLICATION SCIENTIFIC EVIDENCE INTAKE</div>
   <h3>{trial.trial} · published primary finding and review gaps</h3>
   <p className={styles.disclaimer}>The values below are reported in public
     journal articles or abstracts, not independently replicated. They are
     <strong> not a clinical pass/fail score, FDA outcome, or validated forecast</strong>.
     Publication dates can be after a historical prediction cut-off.</p>
   <div className={styles.stats}>
     <div><small>Published primary outcome</small><strong>{trial.primaryEndpoint}</strong></div>
     <div><small>Authors' reported effect</small><strong>{trial.reportedEffect}</strong></div>
     <div><small>Analysis population in source</small><strong>{trial.analysisPopulation}</strong></div>
     <div><small>Safety observations in source</small><strong>{trial.safetyObservation}</strong></div>
   </div>
   <div className={styles.sources}>
     <strong>Access reviewed:</strong> {trial.sourceAccess.replaceAll("_"," ").toLowerCase()}
     <span><strong>Published:</strong> {trial.published}</span>
     <a target="_blank" rel="noopener noreferrer" href={trial.articleUrl}>
       Open original article / PubMed source</a>
     <a target="_blank" rel="noopener noreferrer" href={trial.journalUrl}>
       Publisher or DOI article location</a>
     {trial.supplementUrl&&<a target="_blank" rel="noopener noreferrer"
       href={trial.supplementUrl}>Publisher protocol and supplemental materials listing</a>}
     <span className={styles.sourceStatus}>{trial.supplementStatus.replaceAll("_"," ")}</span>
   </div>
   <details className={styles.details}>
     <summary>Eight domain-by-domain scientific review requirements · unassessed</summary>
     <div className={styles.domainGrid}>
     {trial.domains.map((d,i)=><article className={styles.domain} key={d.key}>
       <div><strong>{i+1}. {d.label}</strong>
         <span>UNASSESSED · no independent reviewer signature</span></div>
       <p>{d.needed}</p>
       <small>{d.sourceReportedEvidenceAvailable?
         "Published outcome reported; not independently adjudicated":
         "Original evidence reconciliation pending"}</small>
     </article>)}
     </div>
   </details>
   <details className={styles.details}>
     <summary>Priority trial-specific protocol, statistical and safety follow-ups · {trial.specificReviewNeeds.length}</summary>
     <ul>{trial.specificReviewNeeds.map(task=><li key={task}>{task}</li>)}</ul>
   </details>
   <p className={styles.warning}><strong>Source access is not scientific completion.</strong>
    Original signed pre-unblinding SAP validated: <strong>NO</strong>.
    Qualified scientific reviews: <strong>0</strong>.
    Approved/CRL forecast validated: <strong>0/23</strong>.
    Measured calibration: <strong>UNAVAILABLE</strong>.
    Future FDA decision: <strong>ABSTAIN</strong>.</p>
 </section>
 {nct==="NCT05126758"&&<CaprFdaChallengeR72/>}
 {nct==="NCT06153693"&&<LaunchHtnOriginalDocumentsR73/>}
 {nct==="NCT06153693"&&<LaunchHtnSourceChronologyR75/>}
 {nct==="NCT06153693"&&<LaunchHtnMethodsR77/>}
 </>;
}
