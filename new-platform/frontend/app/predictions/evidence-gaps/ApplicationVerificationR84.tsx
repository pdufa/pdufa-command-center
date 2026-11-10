import {R84_APPLICATION_VERIFICATION} from "../../../lib/focus-r84-application-verification-queue";
import styles from "./EvidenceRecoveryBoardR68.module.css";

/** Read-only issuer-reported review cycle queue: no live FDA verification. */
export default function ApplicationVerificationR84() {
 const d=R84_APPLICATION_VERIFICATION;
 if(!d)return <section aria-label="R84 application verification queue">
  <p role="alert">The exact trial/application crosswalk failed integrity checks.
   Review status and reported goals are withheld.</p>
 </section>;
 return <section aria-label="R84 application verification queue" className={styles.coverage}>
   <div className={styles.eyebrow}>MAIN · REVISION 84 · APPLICATION REVIEW CHECKLIST</div>
   <h2>FDA application identity and reported goal-date verification</h2>
   <p className={styles.intro}>{d.banner} Original source research snapshot:
     <strong> {d.snapshotAsOf}</strong>. An issuer's reported PDUFA goal is
     not independently confirmed by the FDA in this dataset. Do not treat
     listed statuses as current without checking their original sources.</p>
   <div className={styles.stats}>
     <div><small>Provisional application groups</small><strong>{d.provisionalCycles}</strong></div>
     <div><small>With reported target date</small><strong>{d.reportedTargetCount}</strong></div>
     <div><small>Without reported target</small><strong>{d.noReportedTargetCount}</strong></div>
     <div><small>FDA status confirmations</small><strong>{d.independentFDAApplicationStatusConfirmations}</strong></div>
   </div>
   <p className={styles.notice}>Sorted by retained <strong>issuer-reported</strong> goal
     where available, not by verified next FDA action. Every application is
     linked to its exact supporting NCTs. Already-observed status claims are
     separated from future-decision candidates. Forecast: <strong>ABSTAIN</strong>;
     review timing: <strong>UNKNOWN</strong>. No clinical scores have been signed.</p>
   <div className={styles.coverageGrid}>
     {d.rows.map(row=><article className={styles.coverageGroup} key={row.cycleId}>
       <strong>{row.ticker} · {row.drug}</strong>
       <div>{row.applicationType} · {row.indication}</div>
       <div>Cycle ID: {row.cycleId}</div>
       <div><b>Source-reported stage:</b> {row.sponsorReportedStatus}</div>
       <div><b>Source-reported target:</b> {row.sponsorReportedGoal??"No goal in snapshot"}</div>
       {row.observedHistoricalStatusClaim&&<p><b>Previously observed status claim.</b>
         Verify the actual FDA decision; never count this as an upcoming prediction.</p>}
       <div><b>Original source:</b> <a href={row.sourceUrl}
        target="_blank" rel="noopener noreferrer">Issuer/disclosure · {row.sourceDate}</a></div>
       <p><b>Regulatory question:</b> {row.criticalQuestion}</p>
       <div><b>Supporting clinical trials:</b>
         <ul>{row.linkedNcts.map(nct=><li key={nct}>
           <a href={"/predictions/assessment?nct="+nct}>{nct}</a>
         </li>)}</ul>
       </div>
       <small>Source gaps among linked NCTs:
         primary {row.missingRegistryPrimaryTables}/{row.linkedNcts.length};
         safety {row.missingRegistrySafetyArms}/{row.linkedNcts.length};
         methods {row.missingMethodPageLeads}/{row.linkedNcts.length}.
         Registry absence is not evidence of failure.
         Independent review and current FDA verification are outstanding.</small>
     </article>)}
   </div>
 </section>;
}
