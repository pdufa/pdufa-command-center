import {FOCUS_R70_PUBLICATION_TRIAGE} from "../../../lib/focus-r70-publication-abstract-triage";
import styles from "./PublicationEvidenceRoleR70.module.css";

/** R70 public journal/PubMed title-and-abstract research triage ONLY. It
 * deliberately does not infer efficacy success, FDA approval, confidence,
 * statistical SAP conformity, signed clinical judgment or historical accuracy.
 */
export default function PublicationEvidenceRoleR70({nct}:{nct:string}){
 const c=FOCUS_R70_PUBLICATION_TRIAGE;
 if(!c)return <div className={styles.shell}
   aria-label={"R70 publication role classification for "+nct}>
   <p role="alert">Research role classification withheld: one or more original
    source identifiers or medical forecast safeguards did not validate.</p>
 </div>;
 const papers=c.papers.filter(x=>x.nct===nct);
 if(!papers.length)return null;
 return <section className={styles.shell}
   aria-label={"R70 publication role classification for "+nct}>
  <div className={styles.kicker}>REVISION 70 · PUBLICATION ROLE · TITLE/ABSTRACT TRIAGE</div>
  <h3>Is this the pivotal Phase 3 result?</h3>
  <p>Each link has a <strong>provisional article role</strong> based on the
   public PubMed/journal title and abstract. Even a direct Phase 3 primary
   report is <strong>not a signed scientific assessment</strong> and cannot
   independently validate its original locked SAP or regulatory outcome.</p>
  <div className={styles.entries}>
   {papers.map(p=><div key={p.pmid} className={styles.entry}>
    <strong className={styles.role}>{p.roleLabel}</strong>
    <div className={styles.title}>{p.title}</div>
    <p>{p.reason}</p>
    <a target="_blank" rel="noopener noreferrer"
      href={p.pubmedUrl}>PubMed {p.pmid} · Inspect source abstract</a>
    <small>Full original methods, estimand, missingness, multiplicity,
     prespecification chronology and reviewer signoff: not adjudicated</small>
   </div>)}
  </div>
  <p className={styles.limit}>Source triage is not efficacy scoring.
   <strong> Independently signed grades: 0.</strong> Validated FDA forecasts:
   <strong> 0/23.</strong> Outcome: <strong>ABSTAIN</strong>.</p>
 </section>;
}
