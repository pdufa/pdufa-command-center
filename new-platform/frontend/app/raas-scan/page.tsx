/** RAAS read-only scan results; never labels 60 inventoried metrics as 60 valid grades. */
import type {Metadata} from "next";
import Link from "next/link";
import {executeRaasReadinessScan} from "../../lib/raas-readiness-scan";
import {evaluateRaasInstallation} from "../../lib/raas-installation-gates";
import tenYearIntake from "../../data/raas-ten-year-pdufa-intake.json";
import css from "../raas-history/page.module.css";
export const metadata:Metadata={
 title:"RAAS 60-Metric Scan Status | PDUFA",
 description:"Evidence-level RAAS scan, distinct from independent historical validation and release of numeric scores."
};
const report=executeRaasReadinessScan();
const installation=evaluateRaasInstallation(report,tenYearIntake);
export default function RaasScanPage(){
 const s=report.summary;
 return <main className={css.root} data-raas-readiness-executed={report.scanExecution}>
   <header className={css.header}>
    <Link className={css.back} href="/tools">← Back to TOOLS</Link>
    <h1>RAAS · 60-metric scan status</h1>
    <p>Source readiness was checked against the exact committed evidence snapshot. An executed source audit is not the same as a historically calibrated RAAS investment score.</p>
   </header>
   <div className={css.stats}>
    <div><strong>{s.metricsInspected}/60</strong><span>Metric requirements inspected · 30 TOP / 30 BOTTOM</span></div>
    <div><strong>{s.reviewEligibleMetrics}/60</strong><span>Passed independent historical holdout requirements</span></div>
    <div><strong>{s.approvedMetricCalibrations}/60</strong><span>Approved metric scoring calibrations</span></div>
    <div><strong>{s.historicalAcceptedCases}</strong><span>Accepted historical event-window trades</span></div>
   </div>
   <p className={css.disclaimer}><strong>SCAN EXECUTED · FINAL RAAS NOT VALIDATED.</strong> The audit inspected every definition and available evidence record. It did not create a price forecast, set missing scores to zero, import unpublished trial outcomes, or claim that a source lead has been calibrated. Underlying source snapshot: {report.sourceAsOf}; metric specification: {report.specVersion}.</p>
   <section className={css.section} data-raas-installation-gates={installation.state}>
    <div className={css.sectionTitle}>
     <h2>Installation acceptance checks</h2>
     <span>{installation.completedGates}/{installation.totalGates} checks satisfied · {installation.state==="COMPLETE"?"release evidence present":"RAAS not ready"}</span>
    </div>
    <p className={css.disclaimer}>The 60 metric definitions exist, but definitions and source scans are not validated predictive grades. The full 2016–2025 study requires evidence for each historical year and originally published PDUFA dates.</p>
    <div className={css.checks}>
     {installation.gates.map(g=><details className={css.check} key={g.id} data-raas-gate={g.id}>
      <summary>
       <span className={css.indicator}>{g.completed?"✓":"!"}</span>
       <strong>{g.name}</strong>
       <span className={css.status}>{g.achieved}/{g.required} {g.unit} · {g.completed?"gate passed":"blocked"}</span>
      </summary>
      <div className={css.checkBody}><p>{g.completed?"This check passed, but other independent checks remain required.":g.blocker}</p></div>
     </details>)}
    </div>
    <p className={css.disclaimer}>Historical PDUFA census: {installation.eligibleSourceYears}/10 years independently audited. {installation.sourceYears.filter(y=>!y.verified).map(y=>y.year).join(", ")} are not yet certified as complete. A previously downloaded Alpaca price bar is not proof that the company met the historical market-cap and source-timing rules.</p>
    <p><a href="https://github.com/pdufa/pdufa-command-center/actions/workflows/raas-alpaca-ten-year-study.yml" target="_blank" rel="noopener noreferrer">Open the Alpaca 10-year research workflow and its downloadable evidence-gap report</a></p>
   </section>
   <section className={css.section}>
    <div className={css.sectionTitle}><h2>Evidence actually recorded</h2><span>Research coverage only, not validated scores</span></div>
    <div className={css.facts}>
     <div><span>Prospective source collection</span><strong>{s.prospectiveIssuers} issuers · {s.prospectivePrograms} therapy programs · {s.prospectiveSourceFacts} dated facts</strong></div>
     <div><span>Retrospective study material</span><strong>{s.retrospectiveResearchWindows} selected research windows, 0 original RAAS predictions</strong></div>
     <div><span>Price and SEC verification</span><strong>{s.independentlyConfirmedNominalCloses}/{s.nominalClosePoints} nominal closes cross-checked; {s.secShareBridgeCases}/{s.retrospectiveResearchWindows} SEC share counts; {s.secShareCapMismatches} unresolved capitalization discrepancies</strong></div>
     <div><span>Regulatory evidence</span><strong>{s.fdaPrimaryCrosschecks} historical post-exit FDA action source checks</strong></div>
    </div>
    <p className={css.disclaimer}>Matching a nominal closing price, counting trial identifiers, or recording earlier issuer data does not establish independently verified adjusted returns or a successful RAAS prediction. The source audit does not fetch new market data automatically.</p>
   </section>
   {(["pre","post"] as const).map(stage=><section className={css.section} key={stage}>
    <div className={css.sectionTitle}>
     <h2>{stage==="pre"?"TOP · before Phase 3 results":"BOTTOM · after Phase 3 results"} · 30 metric checks</h2>
     <span>{report.metrics.filter(m=>m.stage===stage&&m.approvedCalibration).length}/30 approved</span>
    </div>
    <div className={css.checks}>
     {report.categories.filter(g=>g.stage===stage).map(group=><details key={stage+"|"+group.id} className={css.check} data-raas-scan-group={stage+"|"+group.id}>
      <summary><span className={css.indicator}>◌</span><strong>{group.name} · {group.total} metrics</strong>
       <span className={css.status}>{group.approved} calibrated · {group.historicallyValidated} holdout-ready · {group.sourceFacts} research links</span>
      </summary>
      <div className={css.checkBody}>
       {report.metrics.filter(m=>m.stage===stage&&m.category===group.name).map(metric=>
        <div key={metric.id} className={css.sourceFact} data-raas-scan-metric={metric.id}>
         <strong>{metric.id} · {metric.name}</strong>
         <p><strong>{metric.status.replaceAll("_"," ")}</strong> · {metric.prospectiveSourceFacts} prospective source links across {metric.prospectiveIssuerCount} issuers · {metric.validatedHistoricalPrograms} eligible historical program/return pairs</p>
         <p>Issuer-disjoint historical training/holdout: {metric.holdoutTrainIssuers}/{metric.holdoutTestIssuers}. Held-out high/low grade cohorts: {metric.heldOutHighIssuers}/{metric.heldOutLowIssuers}. This is not a metric score.</p>
         <p>Required: {metric.requiredEvidence}</p>
         <p className={css.factCaution}>Blocker: {metric.reason}</p>
        </div>)}
      </div>
     </details>)}
    </div>
   </section>)}
   <section className={css.section}>
    <h2>Completion requirements</h2>
    <div className={css.checks}>
     {report.limitations.map((reason,i)=><p className={css.notice} key={i}>{reason}</p>)}
    </div>
   </section>
   <footer className={css.footer}>
    <strong>Audit record and execution history</strong>
    <p><a href="https://github.com/pdufa/pdufa-command-center/actions/workflows/raas-readiness-scan.yml" target="_blank" rel="noopener noreferrer">Open scheduled RAAS scan workflow and dated per-metric JSON artifacts</a>. The workflow executes on source changes and a daily schedule; its output reflects the committed sources at each execution, not a claim of automatic independent evidence collection.</p>
    <p><Link href="/raas-history">Open detailed historical evidence and prospective source baseline audit</Link></p>
   </footer>
 </main>;
}
