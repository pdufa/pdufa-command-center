/** All-trial RAAS evidence triage; not a scoring or trading route. */
import type {Metadata} from "next";
import Link from "next/link";
import EvidenceBacklogClient from "./EvidenceBacklogClient";
import css from "../raas-history/page.module.css";

export const metadata:Metadata={
 title:"RAAS · All-Trial Evidence Gaps | PDUFA",
 description:"Source-by-source gap triage for 762 ClinicalTrials.gov research records before independent RAAS rating and FDA forecast validation."
};
export default function RaasEvidenceBacklogPage(){
 return <main className={css.root} data-raas-762-evidence-backlog="research-gaps-only">
  <header className={css.header}>
   <Link className={css.back} href="/raas-scan">← RAAS 60-metric scan</Link>
   <h1>RAAS · all-trial evidence gap queue</h1>
   <p>Prioritized work across all 762 saved Phase 3 research trial identifiers.
    Expand each trial to see exactly what the registered source contains,
    the documented TOP/BOTTOM review counts, and the next missing evidence step.</p>
  </header>
  <p className={css.disclaimer}><strong>Research triage, not 762 approved scores.</strong>
   The saved registry index verifies trial-level source availability; it does not establish
   the current $300M–$10B live Pipeline, an accepted FDA application, an eligible
   PDUFA date or the phase of every indication. Known current Phase 3 and accepted
   FDA cases are prioritized only from separate dated source snapshots.
   Every unknown metric stays ungraded until a same-program primary source,
   independent benchmark and source-date review are recorded.
  </p>
  <p className={css.notice} style={{marginTop:18}}>
   <strong>Nightly source revisions:</strong> The dedicated change-history
   monitor distinguishes new posted results, revised primary or safety
   evidence, and administrative registry updates, with exact NCT source
   hashes and manual-review flags.
   {" "}<Link href="/raas-evidence-changes">Open the source change history</Link>.
   Source changes never auto-update RAAS grades or historical predictions.
  </p>
  <EvidenceBacklogClient/>
  <p className={css.foot} style={{marginTop:25}}>
   <Link href="/raas-review-queue">Review existing 82 independently pending metric packets</Link>.
   Neither a registry design diagnostic nor a source-rich study converts into an
   FDA PASS/CRL/EXTENSION probability or calibrated RAAS rating.
   Retired GEM and GEM JR scans remain inactive; historical data is preserved.
  </p>
 </main>;
}
