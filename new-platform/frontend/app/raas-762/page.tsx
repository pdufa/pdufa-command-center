/** Primary RAAS workspace: all 762 source-backed trial setup rows.
 * Neither saved research metric coverage nor registry evidence implies
 * independent validation of numerical ratings or FDA predictions.
 */
import type {Metadata} from "next";
import Link from "next/link";
import status from "../../data/raas-all-trials-partial-metric-ratings-status.json";
import Raas762ScoringWorkspace from "../Raas762ScoringWorkspace";
import css from "../raas-history/page.module.css";

export const metadata:Metadata={
 title:"RAAS · 762 Trial Scoring Setup | PDUFA",
 description:"All 762 research NCT rows with TOP/BOTTOM 30-metric scoring checklists, missing evidence, search, filters and score history."
};
export default function Raas762Page(){
 return <main className={css.root} data-raas-primary-scoring-setup="762-nct-rows">
  <header className={css.header}>
   <Link className={css.back} href="/tools">← TOOLS</Link>
   <h1>RAAS · 762-trial scoring setup</h1>
   <p><strong>One trial per row, all 762 NCTs.</strong> The 30 TOP and
    30 BOTTOM metric slots, missing-review status and unified trial history
    are accessible directly in the scoring table below.</p>
  </header>
  <Raas762ScoringWorkspace/>
  <p className={css.disclaimer}>
   <strong>Current score audit:</strong> {status.uniqueNctsWithActualProvisionalMetricScores}
   {" "}of {status.researchTrials} NCTs have at least one source-checked provisional
   metric review; {status.fullValidatedRaasScores} independently validated full
   RAAS ratings. This is the entire saved 762-trial research universe, not
   a claim that 762/762 scores are complete or that all meet current
   $300M–$10B Phase 3 PDUFA Pipeline restrictions.
  </p>
  <p className={css.foot}>
   <Link href="/raas-evidence-backlog">Evidence gaps and prioritization for these same 762 trials</Link>
   {" · "}<Link href="/raas-review-queue">Independent source-review assignments</Link>
   {" · "}<Link href="/raas-scan">Technical RAAS scan diagnostics</Link>.
  </p>
 </main>;
}
