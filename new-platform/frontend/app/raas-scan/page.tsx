/** RAAS read-only scan results; never labels 60 inventoried metrics as 60 valid grades. */
import type {Metadata} from "next";
import Link from "next/link";
import {executeRaasReadinessScan} from "../../lib/raas-readiness-scan";
import {evaluateRaasInstallation} from "../../lib/raas-installation-gates";
import {auditRaasSurveyAccuracy} from "../../lib/raas-self-accuracy-audit";
import RaasSelfAuditHistoryButton from "./RaasSelfAuditHistoryButton";
import activeTwoYearIntake from "../../data/raas-active-2024-2025-pdufa-intake.json";
import activeStudyConfig from "../../data/raas-active-study-config.json";
import fdaAccuracySnapshot from "../../data/raas-fda-three-way-accuracy-site-snapshot.json";
import RaasFullUniverseScores from "../RaasFullUniverseScores";
import css from "../raas-history/page.module.css";
export const metadata:Metadata={
 title:"RAAS 60-Metric Scan Status | PDUFA",
 description:"Evidence-level RAAS scan, distinct from independent historical validation and release of numeric scores."
};
const report=executeRaasReadinessScan();
const installation=evaluateRaasInstallation(report,activeTwoYearIntake);
const selfAudit=auditRaasSurveyAccuracy(report,installation,fdaAccuracySnapshot);

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
   <RaasFullUniverseScores/>
   <section className={css.section} data-raas-self-audit={selfAudit.status}>
    <div className={css.sectionTitle}>
     <h2>RAAS accuracy audit · how accurate is RAAS itself?</h2>
     <span>{selfAudit.raasGatesPassed}/{selfAudit.raasGatesRequired} evidence gates satisfied</span>
    </div>
    <RaasSelfAuditHistoryButton audit={selfAudit}/>
    <div className={css.stats}>
     <div><strong>{selfAudit.status==="NOT_MEASURABLE"?"Not measurable":"Under review"}</strong>
      <span>Independent RAAS predictive reliability rating</span></div>
     <div><strong>{selfAudit.raasGatesPassed}/{selfAudit.raasGatesRequired}</strong>
      <span>Research-evidence gates · NOT an accuracy percentage</span></div>
     <div><strong>{selfAudit.independentReturnAccuracyPct===null?"Not validated":selfAudit.independentReturnAccuracyPct+"%"}</strong>
      <span>Independent stock-return predictive accuracy</span></div>
     <div><strong>{selfAudit.independentFDAThreeWayAccuracyPct===null?"Not validated":selfAudit.independentFDAThreeWayAccuracyPct+"%"}</strong>
      <span>Separate FDA PASS / CRL / EXTENSION accuracy</span></div>
    </div>
    <p className={css.disclaimer}><strong>No numerical accuracy rating is justified yet.</strong>
     {" "}The research catalog has been checked, but the independently validated historical returns,
     issuer-disjoint holdouts and prospective FDA forecasts needed to measure predictive accuracy
     are absent. A missing accuracy estimate does not mean 0% accuracy or 100% inaccuracy.</p>
    <div className={css.checks}>
     {selfAudit.raasGates.map(g=><details key={g.id} className={css.check} data-raas-self-audit-gate={g.id}>
      <summary><span className={css.indicator}>{g.passed?"✓":"!"}</span>
       <strong>{g.name}</strong><span className={css.status}>{g.achieved}/{g.required} {g.unit} · {g.passed?"verified":"not yet verified"}</span>
      </summary>
      <div className={css.checkBody}><p>{g.explanation}</p></div>
     </details>)}
    </div>
    <details className={css.check} data-raas-self-audit-fda="separate-target">
     <summary><span className={css.indicator}>!</span><strong>Separate FDA three-class accuracy test</strong>
      <span className={css.status}>{selfAudit.fdaProspectiveGate.achieved}/{selfAudit.fdaProspectiveGate.required} independently frozen forecast requirement · not validated</span>
     </summary>
     <div className={css.checkBody}>
      <p>{selfAudit.fdaProspectiveGate.explanation}</p>
      <p>On the older, retrospectively selected binary cases, the RAAS predecessor had
       {" "}{fdaAccuracySnapshot.legacyCorrect} correct calls versus
       {" "}{fdaAccuracySnapshot.alwaysApproveCorrect} for always predicting approval,
       a difference of {selfAudit.retrospectiveDifferenceInCorrectCalls} correct calls
       ({selfAudit.retrospectiveBaselineDifferencePctPoints} percentage points).
       These numbers do not establish prospective accuracy or EXTENSION recognition.</p>
      <p><Link href="/raas-worklist#raas-fda-prediction-accuracy">Open FDA three-way evidence and independent accuracy requirements</Link></p>
     </div>
    </details>
    <p className={css.notice}>{selfAudit.warning}</p>
   </section>
   <section className={css.section} data-raas-installation-gates={installation.state}>
    <div className={css.sectionTitle}>
     <h2>Installation acceptance checks</h2>
     <span>{installation.completedGates}/{installation.totalGates} checks satisfied · {installation.state==="COMPLETE"?"release evidence present":"RAAS not ready"}</span>
    </div>
    <p className={css.disclaimer}>The 60 metric definitions exist, but definitions and source scans are not validated predictive grades. The active {activeStudyConfig.studyDurationYears}-year study covers {activeStudyConfig.years.join("–")}; earlier 2016–2025 research is archived. Original PDUFA disclosures and independent 2024/2025 outcome census audits are still required.</p>
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
    <p className={css.disclaimer}>Active {activeStudyConfig.years.join("–")} PDUFA census: {installation.eligibleSourceYears}/{activeStudyConfig.studyDurationYears} years independently audited. {installation.sourceYears.filter(y=>!y.verified).map(y=>y.year).join(", ")} are not yet certified as complete. A previously downloaded Alpaca price bar is not proof that the company met the historical market-cap and source-timing rules.</p>
    <p><a href="https://github.com/pdufa/pdufa-command-center/actions/workflows/raas-alpaca-active-two-year-study.yml" target="_blank" rel="noopener noreferrer">Open the active Alpaca 2024–2025 research workflow and its downloadable evidence-gap report</a></p>
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
    <p><Link href="/raas-worklist">Open the 60-metric TOP/BOTTOM RAAS evidence and validation worklist</Link></p>
    <p><Link href="/raas-history">Open detailed historical evidence and prospective source baseline audit</Link></p>
   </footer>
 </main>;
}
