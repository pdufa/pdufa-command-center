/** Primary RAAS task: prepare all 762 research NCTs for source-backed
 * stage-specific metric assessment. This is not the separate FDA prediction audit.
 */
import type {Metadata} from "next";
import Link from "next/link";
import Raas762ScoringWorkspace from "../Raas762ScoringWorkspace";
import registry from "../../data/raas-registry-evidence-status.json";
import partial from "../../data/raas-all-trials-partial-metric-ratings-status.json";
import css from "../raas-history/page.module.css";

export const metadata:Metadata={
 title:"RAAS 762 Trial Scoring Setup | PDUFA",
 description:"Search all 762 exact ClinicalTrials.gov NCTs, inspect separate TOP/BOTTOM RAAS metric requirements and score histories, export evidence gaps."
};
if(registry.summary.researchTrials!==762||
 registry.summary.sourceRecordsStored!==762||
 registry.summary.approvedOverallRaasScores!==0||
 partial.researchTrials!==762||
 partial.trialStageRows!==1524||
 partial.fullValidatedRaasScores!==0||
 partial.totalIndependentMetricReviews!==0)
 throw Error("RAAS_762_SCORING_WORKSPACE_SOURCE_COVERAGE_INCONSISTENT");

export default function RaasScoresPage(){
 return <main className={css.root} data-raas-primary-workspace="762-trial-scoring-setup">
  <header className={css.header}>
   <Link className={css.back} href="/tools">← TOOLS</Link>
   <h1>RAAS · 762 trial scoring setup</h1>
   <p>Work through all 762 research NCTs first. A row is available for every
    trial, including those without approved numerical metrics. Open each
    trial’s TOP or BOTTOM 30-metric checklist and its cross-stage history.</p>
  </header>
  <Raas762ScoringWorkspace/>
  <section className={css.section} data-raas-other-tools="secondary">
   <div className={css.sectionTitle}>
    <h2>Supporting tools · secondary to scoring all 762 rows</h2>
   </div>
   <p><Link href="/raas-evidence-backlog">
    Prioritized source and evidence gaps for the same 762 NCTs
   </Link></p>
   <p><Link href="/raas-review-queue">
    Review existing metric evidence assignments
   </Link></p>
   <p><Link href="/raas-scan">
    Advanced 60-metric readiness, source diagnostics and FDA accuracy auditing
   </Link></p>
   <p className={css.disclaimer}>
    Scope is the saved 762-record research roster, not the larger 11,000+
    trial POOL, retired GEM/JR scans, or an independently verified
    current $300M–$10B PDUFA-eligible cohort. The 17 trials with partial
    metric evidence do not have validated overall RAAS scores.
   </p>
  </section>
 </main>;
}
