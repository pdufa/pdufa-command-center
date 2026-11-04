/** Read-only 60-metric validation worklist; never use evidence coverage as an
 * investment rating. This route is linked from both Phase 3 spreadsheets.
 */
import type {Metadata} from "next";
import Link from "next/link";
import {buildRaasMetricValidationWorklist,raasDocumentedTrialOptions,type RaasWorklistTrial} from "../../lib/raas-metric-validation-worklist";
import {activePdufaGoalAsOfAudit} from "../../lib/raas-pdufa-goal-asof-metric-audit";
import {activeSECAsOfEntryShares} from "../../lib/raas-historical-sec-entry-bridge";
import {raasFull903Overview} from "../../lib/raas-full-90-3-window-policy";
import expansionSource from "../../data/raas-2024-2025-expanded-candidate-source-leads.json";
import expandedCoverShares from "../../data/raas-2024-2025-expanded-candidate-sec-snapshots.json";
import fdaDecisionAccuracy from "../../data/raas-fda-three-way-accuracy-site-snapshot.json";
import v2Readiness from "../../data/raas-v2-candidate-source-readiness-site-snapshot.json";
import v2Top8Sources from "../../data/raas-v2-top8-2026-source-intake.json";
import nov14Triangulation from "../../data/raas-v2-nov14-review-cycle-triangulation.json";
import nov14IssuerGoalContinuity from "../../data/raas-v2-nov14-issuer-goal-continuity.json";
import goal2025Research from "../../data/raas-2025-nine-archived-goal-original-source-triage.json";
import type {RaasStage} from "../../lib/raas-metric-specs";
import css from "./page.module.css";

export const metadata:Metadata={
 title:"RAAS TOP/BOTTOM · 60 Metric Validation Worklist | PDUFA",
 description:"All 60 risk-adjusted appreciation assessment metrics, exact-trial source evidence and unapproved calibration gaps."
};
type Params={stage?:string|string[];nctId?:string|string[];ticker?:string|string[];
 drug?:string|string[];indication?:string|string[]};
const first=(x:string|string[]|undefined)=>typeof x==="string"?x:"";
const safe=(x:string)=>x.length<=200?x:"";
function hrefForTrial(t:RaasWorklistTrial|null,stage:RaasStage):string{
 const args=new URLSearchParams({stage});
 if(t){
  args.set("nctId",t.nctId);args.set("ticker",t.ticker);
  if(t.drug)args.set("drug",t.drug);
  if(t.indication)args.set("indication",t.indication);
 }
 return "/raas-worklist?"+args.toString()+"#raas-"+(stage==="pre"?"top":"bottom")+"-worklist";
}
/** Historical examples, not exact-trial evidence for a selected current program.
 * FDA outcomes are intentionally absent; dated target versions are the only
 * inputs being evaluated for the two FDA and timing source gates.
 */
/** Search specification only: research outputs remain provisional until validated. */
/** FDA decision-model validation is independent of price-window research and RAAS metric grades. */
function FDAAccuracySection(){
 const x=fdaDecisionAccuracy;
 return <section id="raas-fda-prediction-accuracy" className={css.context}
  data-raas-fda-accuracy="UNVALIDATED_NO_CLAIM">
  <h2>FDA decision accuracy · PASS / CRL / EXTENSION</h2>
  <p><strong>Not independently validated.</strong> This is the three-way first-announced-PDUFA-goal benchmark, not the stock-return study. It separately records FDA approvals, Complete Response Letters, and formally announced goal extensions known before the original deadline.</p>
  <div className={css.stats}>
   <div><strong>{x.legacyRetrospectiveCases}</strong><span>Older selected binary FDA cases · not an unbiased census</span></div>
   <div><strong>{x.legacyRetrospectiveAccuracyPct}%</strong><span>Legacy retrospective model diagnostic</span></div>
   <div><strong>{x.alwaysApproveRetrospectiveAccuracyPct}%</strong><span>Simply guessing approval on the same historical cases</span></div>
   <div><strong>{x.predecisionThreeWayIndependentlyVerifiedForecasts}</strong><span>Independently verified frozen three-way forecasts</span></div>
  </div>
  <p className={css.notice}><strong>Critical finding:</strong> The historical model's {x.legacyCorrect}/{x.legacyRetrospectiveCases} correct calls did not beat predicting approval in all {x.legacyRetrospectiveCases} selected cases ({x.alwaysApproveCorrect} correct). The historical source contains {x.historicalExtensions} independently scored extensions; therefore three-class balanced accuracy and calibration are not established.</p>
  <details>
   <summary>Show what the accuracy scanner checks and what is missing</summary>
   <ul>
    <li>A separately pre-registered application and review-cycle roster, including no calls and abstentions</li>
    <li>Frozen probabilities for PASS / CRL / EXTENSION whose FDA and Phase 3 sources were public before the forecast</li>
    <li>Independent original-goal action dates and official FDA outcome or formal extension evidence</li>
    <li>Issuer-disjoint chronological holdout, per-outcome recall, confusion matrix, multiclass Brier, log loss, calibration, Wilson confidence interval, and coverage</li>
    <li>No approval of prediction models or the 60 RAAS rating metrics unless separate validation succeeds</li>
   </ul>
   <p>Older FDA-DIRECTIONAL V1.9 has {x.priorBinaryCasesInLatestVersion} unique pregoal binary freeze cases, not fully sourced three-way probability forecasts. Snapshot: {x.snapshotAsOf}.</p>
  </details>
  <details id="raas-2025-original-fda-goal-review">
   <summary>Review {goal2025Research.records.length} archived 2025 FDA goal source leads · {goal2025Research.formalExtensionSourceLeads} formal extension candidates</summary>
   <p><strong>Research only, not approved FDA prediction labels.</strong> The first announced PDUFA goal must stay separate from any later revised date or eventual FDA approval. Each source still needs independent exact-cycle and evidence-clock adjudication.</p>
   <ul>{goal2025Research.records.map(r=><li key={r.caseId}>
    <strong>{r.ticker}</strong> · archive date {r.archivedSuggestedGoalDate}; first-cycle goal {r.firstCycleGoalDate}
    {r.revision?<>; formally revised to <strong>{r.revision.newDate}</strong> (disclosed {r.revision.publicDate})</>:null}
    ; classification <em>{r.observedOriginalGoalResearchLabel.replaceAll("_"," ").toLowerCase()}</em>
    {r.goalSourceUrl?<> · <a href={r.goalSourceUrl} target="_blank" rel="noopener noreferrer">Dated goal source</a></>:<> · first contemporaneous goal source unresolved</>}
    {r.revision?<> · <a href={r.revision.url} target="_blank" rel="noopener noreferrer">SEC formal extension source</a></>:null}
   </li>)}</ul>
   <p className={css.notice}>These source leads do not change the independent forecasting denominator, the verified three-class accuracy, or RAAS metric approvals.</p>
  </details>
  <p><a href={x.workflowUrl} target="_blank" rel="noopener noreferrer">Open daily FDA accuracy audit and downloadable report</a>. The site displays a dated snapshot; the GitHub Action's latest report is the refreshed audit.</p>
 </section>;
}
/** V2 candidate is a research-only source intake; V1 remains the active score specification. */
function V2CandidateReadiness(){
 const x=v2Readiness;
 return <section id="raas-v2-source-readiness" className={css.context}
  data-raas-v2-status="RESEARCH_CANDIDATE_NOT_CALIBRATED">
  <h2>RAAS V2 · prospective source-readiness candidate</h2>
  <p><strong>Foundation V1 remains installed.</strong> V2 candidate stage 0 now checks which future FDA application leads can be sourced before their original deadlines. It does not manufacture PASS, CRL or EXTENSION probabilities or change the 60 research metric ratings.</p>
  <div className={css.stats}>
   <div><strong>{x.remainingLegacyFutureCaseSourceLeadsAtSnapshot}</strong><span>Future-dated legacy case source leads (snapshot {x.sourceAsOf})</span></div>
   <div><strong>{x.verifiedOriginalGoalProspectiveThreeWayForecasts}</strong><span>Verified predecision three-way forecasts</span></div>
   <div><strong>{x.approvedMetricCalibrations} / 60</strong><span>Approved RAAS metric calibrations</span></div>
   <div><strong>V1</strong><span>Active RAAS foundation; V2 not released</span></div>
  </div>
  <p className={css.notice}>Of {x.remainingLegacyFutureCaseSourceLeadsAtSnapshot} old future-dated binary case leads, {x.issuerDocumentedNearTermCycleSourceLeads} have issuer goal or formal-revision sources. <strong>{x.knownRevisedGoalExcludedFromOriginalDeadlineQueue} formally extended case dates</strong> (CAPR, SVRA, PRAX and EXEL) are excluded from the unresolved original-goal prediction count; {x.legacyCasesStillUnreviewedByIssuerSources} cases still lack this source review. The remaining {x.remainingUnexcludedLegacyDateResearchLeads} are not independently certified original-goal forecasts.</p>
  <details id="raas-v2-daily-openfda-application-watch">
   <summary>Nightly public FDA application-ID watch · CYTK and SMMT (not a prediction)</summary>
   <p><strong>Official FDA database sources:</strong> <a href="https://api.fda.gov/drug/drugsfda.json?search=application_number%3A%22NDA219083%22&amp;limit=1" target="_blank" rel="noopener noreferrer">CYTK NDA 219083 history</a> · <a href="https://api.fda.gov/drug/drugsfda.json?search=products.active_ingredients.name%3A%22IVONESCIMAB%22&amp;limit=25" target="_blank" rel="noopener noreferrer">SMMT ivonescimab ingredient search</a>. The nightly report records each source's status, dataset freshness, and any publicly indexed *candidate* applications, without certifying the exact pending FDA review cycle.</p>
   <p><strong>CYTK:</strong> The already-approved S-001 is a February REMS-only action, <strong>not</strong> the pending MAPLE-HCM efficacy supplement. Another FDA-listed supplement cannot be assigned to MAPLE-HCM without a matching FDA letter or label. <strong>SMMT:</strong> the public ingredient lookup may reveal a BLA candidate, but its sponsor, specific HARMONi review cycle, and November goal must be independently matched before it can be considered verified. Absence from the FDA public approvals database does not mean no pending BLA exists. The <a href="https://purplebooksearch.fda.gov/" target="_blank" rel="noopener noreferrer">FDA Purple Book</a> lists licensed biologics, not a census of pending applications.</p>
   <p className={css.notice}>Live results are in the <a href={x.nightlySourceReadinessAuditUrl} target="_blank" rel="noopener noreferrer">nightly GitHub RAAS FDA artifact</a>, not this dated website snapshot. A missing, delayed or failed public FDA lookup never proves an approval, CRL, extension or absence of an application. This does not freeze PASS / CRL / EXTENSION probabilities or approve RAAS V2.</p>
  </details>
  <details id="raas-v2-nov14-issuer-goal-continuity">
   <summary>November 14 · {nov14IssuerGoalContinuity.latestDatedIssuerGoalContinuityCases} later issuer goal confirmations and source-age review</summary>
   <p>These dated issuer records repeated the November 14, 2026 FDA target. They do <strong>not</strong> independently establish that the FDA never revised the deadline, identify the pending application number, or authorize a PASS/CRL/EXTENSION forecast. Both located confirmation documents are more than 30 days old as of the November 3 snapshot; newer sources require rechecking.</p>
   <ul>{nov14IssuerGoalContinuity.records.map(r=><li key={r.researchCaseKey}>
     <strong>{r.ticker} · {r.reviewSpecificStudy}</strong> — later issuer source <strong>{r.issuerPublicSourceDate}</strong>,
     still lists <strong>{r.reportedGoalDate}</strong>;
     <a href={r.issuerPublicSourceUrl} target="_blank" rel="noopener noreferrer">SEC issuer filing</a>;
     publicly reported application update {r.firstSelectedIssuerPublicApplicationUpdateDate}
     ({r.firstSelectedIssuerPublicApplicationUpdateType.replaceAll("_"," ").toLowerCase()})
     versus actual application submission period <strong>{r.issuerReportedActualApplicationSubmissionMonth}</strong>
     {r.ticker==="CYTK"?<> — January is the actual filing month, February 24 was the public announcement, not the filing date</>:null};
     independently numbered current FDA cycle <strong>not verified</strong>
   </li>)}</ul>
   <p className={css.notice}>Source continuity is not a live FDA deadline guarantee. The nightly RAAS audit retains research-only dates and flags sources older than 30 days without treating the lack of a newer public filing as evidence of no extension.</p>
  </details>
  <details id="raas-v2-nov14-cross-source-registry">
   <summary>November 14 research · {nov14Triangulation.casesCrossChecked} Phase 3 trial registries cross-checked against issuer FDA dates</summary>
   <p><strong>Verified study Phase 3, not verified FDA decision cycle.</strong> Trial registry identity and study phase are independently published by ClinicalTrials.gov. Issuer-reported goal dates are November 14, 2026; neither pending FDA review cycle has been independently certified or prospectively forecast.</p>
   <ul>{nov14Triangulation.records.map(r=><li key={r.researchCaseKey}>
    <strong>{r.ticker} · {r.drug}</strong> · {r.applicationClass.replaceAll("_"," ").toLowerCase()} · {r.underReview}
    ; reported FDA action goal <strong>{r.issuerReportedFirstGoalDate}</strong>
    ; Phase 3 <strong>{r.clinicalTrialsGovStudyName} · {r.clinicalTrialsGovId}</strong>
    ; <a href={r.clinicalTrialsGovUrl} target="_blank" rel="noopener noreferrer">Independent trial registry</a>
    ; <a href={r.issuerGoalSourceUrl} target="_blank" rel="noopener noreferrer">Issuer goal announcement</a>
    {r.usFDAParentOriginalNdaNumber?<>; FDA-approved <strong>parent original NDA {r.usFDAParentOriginalNdaNumber}</strong>, approval {r.usFDAParentOriginalNdaApprovalDate}
     ; <a href={r.usFDAParentOriginalApprovalLetterUrl!} target="_blank" rel="noopener noreferrer">FDA original NDA approval package</a>
     ; <strong>this does not verify the pending supplement number</strong></>:<>; pending BLA number not independently verified</>}
    ; current FDA review-cycle certification <strong>not complete</strong>
   </li>)}</ul>
   <p className={css.notice}><strong>CYTK FDA mismatch guard:</strong> NDA 219083 <strong>S-001 was already approved February 5, 2026 for REMS changes only</strong>, not MAPLE-HCM. The company publicly reported the separate MAPLE-HCM submission February 24 and review goal May 5. <a href={nov14Triangulation.records[0].fdaPreviouslyApprovedUnrelatedSupplementSourceUrl} target="_blank" rel="noopener noreferrer">FDA S-001 REMS-only letter</a> · <a href={nov14Triangulation.records[0].mapleHcmSubmissionPublicSourceUrl} target="_blank" rel="noopener noreferrer">MAPLE-HCM submission SEC source</a>. The November review supplement number remains unverified.</p>
   <p className={css.notice}><strong>SMMT FDA evidence gap:</strong> The company's 10-Q reported the FDA requires statistically significant overall-survival evidence, but the HARMONi primary OS analysis reported <strong>p = 0.057</strong> without meeting significance. <a href={nov14Triangulation.records[1].fdaOSStatisticalSignificanceRequirementPublicSourceUrl} target="_blank" rel="noopener noreferrer">Issuer 10-Q regulatory disclosure</a> · <a href={nov14Triangulation.records[1].pivotalPrimaryOverallSurvivalSourceUrl} target="_blank" rel="noopener noreferrer">Primary OS disclosure</a>. This is a documented risk, <strong>not a CRL forecast or FDA outcome</strong>.</p>
   <p className={css.notice}>No PASS / CRL / EXTENSION probabilities were frozen, no FDA outcome was adjudicated and no eligibility for the $300M–$10B post-Phase-3 Pipeline or calibrated RAAS rating was inferred.</p>
  </details>
  <details id="raas-v2-source-verified-eight">
   <summary>{v2Top8Sources.goalSourceLeads} dated issuer source leads · original, supplemental, revised and licensed sponsor distinctions</summary>
   <p><strong>Contemporaneous issuer and SEC publications located; not independently certified FDA application identities or predictions.</strong> CAPR's first target already passed and was extended, CYTK is a supplemental NDA, CORT is a post-CRL resubmission, and ANAB receives financial rights to a Vanda-licensed program.</p>
   <ul>{v2Top8Sources.records.map(r=><li key={r.legacyCaseKey}>
    <strong>{r.ticker}</strong> · {r.drug} · currently listed goal {r.legacyGoalDate}
    ; {r.applicationType.replaceAll("_"," ").toLowerCase()}
    {r.formalGoalRevision?<>; original first-cycle goal <strong>{r.firstCycleGoalDate}</strong> → revised {r.formalGoalRevision.revisedGoalDate}</>:null}
    {r.ticker==="ANAB"?<>; FDA-facing licensed sponsor <strong>{r.clinicalSponsor}</strong>, stock exposure: {r.stockExposure}</>:null}
    ; source published {r.sourcePublicationDate} · <a href={r.issuerSourceUrl} target="_blank" rel="noopener noreferrer">Open original dated source</a>
   </li>)}</ul>
   <p className={css.notice}>These {v2Top8Sources.records.length} source leads remain research-only: no independent review-cycle certification, no immutable three-way forecast receipts, no approved V2 model.</p>
  </details>
  <details id="raas-v2-additional-original-goals">
   <summary>{v2Top8Sources.additionalOriginalGoalIssuerSourceLeads} new issuer-sourced original FDA goal leads · NDA/BLA review-cycle separation</summary>
   <p><strong>Source research only, not independent FDA application verification.</strong> GILD anito-cel and COGT nonadvanced mastocytosis cite pivotal Phase 2 studies: they are not automatically eligible for the Phase 3-only Pipeline. Cogent's GIST and nonadvanced mastocytosis NDAs are separate review-cycle cases.</p>
   <ul>{v2Top8Sources.additionalOriginalGoalIssuerSourceCases.map(r=><li key={r.legacyCaseKey}>
    <strong>{r.ticker}</strong> · {r.drug} · reported original goal <strong>{r.issuerReportedFirstGoalDate}</strong>
    ; {r.applicationType.replaceAll("_"," ").toLowerCase()} · pivotal evidence {r.pivotalPhaseEvidence.replaceAll("_"," ").toLowerCase()}
    ; original announcement {r.sourcePublicationDate} · <a href={r.issuerSourceUrl} target="_blank" rel="noopener noreferrer">Dated issuer source</a> · <a href={r.phaseEvidenceSourceUrl} target="_blank" rel="noopener noreferrer">Study evidence</a>
    ; no certified Phase 3 qualification or three-way prediction
   </li>)}</ul>
   <p className={css.notice}>Issuer evidence does not certify the earliest publicly disclosed deadline, exact numbered FDA application, absence of extensions, or independence of FDA outcome. No RAAS score has been approved.</p>
  </details>
  <details id="raas-v2-formally-revised-goals">
   <summary>{v2Top8Sources.additionalFormallyExtendedLegacyReviewLeads} additional formal FDA goal revisions · exclude stale or moved deadlines</summary>
   <p><strong>Issuer-documented research findings, not independently certified FDA results or model predictions.</strong> SVRA and PRAX have legacy revised dates; EXEL retains the old December 3 original date even though an extension to March 3, 2027 was reported before that deadline.</p>
   <ul>{v2Top8Sources.additionalFormalRevisionCases.map(r=><li key={r.legacyCaseKey}>
    <strong>{r.ticker}</strong> · {r.drug} · original first-cycle goal <strong>{r.firstCycleGoalDate}</strong> → issuer-reported revised goal <strong>{r.revisedGoalDate}</strong>
    ; legacy spreadsheet goal {r.legacyGoalDate} {r.legacyGoalDate===r.firstCycleGoalDate?"(old original date; already formally extended)":"(revised date, not original)"}
    ; extension disclosed {r.formalExtensionAnnouncementDate} · <a href={r.originalGoalSourceUrl} target="_blank" rel="noopener noreferrer">Original dated goal source</a> · <a href={r.formalExtensionSourceUrl} target="_blank" rel="noopener noreferrer">Dated extension source</a>
   </li>)}</ul>
   <p className={css.notice}>These records do not establish independent review-cycle verification or frozen PASS/CRL/EXTENSION probabilities. No revised goal is a new original FDA action deadline.</p>
  </details>
  <details>
   <summary>See the seven V2 research-to-validation gates</summary>
   <ol>
    <li>Verify original publicly disclosed PDUFA goal and all FDA revisions</li>
    <li>Verify NDA or BLA application, drug, indication and exact review cycle</li>
    <li>Verify efficacy, safety, manufacturing and regulatory sources predate the freeze</li>
    <li>Verify complete application denominator and independent issuer-family identity</li>
    <li>Freeze independent PASS / CRL / EXTENSION probabilities before FDA action</li>
    <li>Independently adjudicate FDA actions or formally announced extensions</li>
    <li>Beat prespecified baselines on untouched issuer-disjoint holdouts, calibration and coverage</li>
   </ol>
   <p className={css.notice}>Current status: source review only. The daily report lists unresolved cases by approaching deadline. No V2 FDA accuracy percentage can yet be reported.</p>
  </details>
  <p><a href={x.nightlySourceReadinessAuditUrl} target="_blank" rel="noopener noreferrer">Open the nightly V2 source readiness CSV and JSON report</a>. The website uses a dated snapshot; GitHub contains the current scan output.</p>
 </section>;
}
function FullRange903History(){
 const x=raasFull903Overview();
 return <section id="raas-full-t90-t3-study" className={css.context}
  data-raas-full-window-study="T90-to-T3-all-combinations">
  <h2>Full entry / exit study · anywhere from T−90 to T−3</h2>
  <p><strong>Any entry and exit combination is allowed</strong> when the entry occurs before the exit. Neither T−79 nor T−14 is a benchmark or required date.</p>
  <div className={css.stats}>
   <div><strong>{x.availablePairs.toLocaleString("en-US")}</strong><span>Entry/exit combinations per PDUFA goal version</span></div>
   <div><strong>{x.sampleCaseCount}</strong><span>2024–2025 historical source-traced trial cases (not full FDA census)</span></div>
   <div><strong>{x.historicalGoalVersionCaseSets}</strong><span>Goal-version case sets (including two revisions)</span></div>
   <div><strong>{x.scenarioEvaluations.toLocaleString("en-US")}</strong><span>Total case-window comparisons in research scan</span></div>
  </div>
  <div className={css.reviewGrid}>
   <div><span>Entry day range</span><strong>{x.entryRange}</strong></div>
   <div><span>Exit day range</span><strong>{x.exitRange}</strong></div>
   <div><span>Calendar and price alignment</span><strong>Next actual session at entry / preceding actual session at exit, at most 4 calendar days</strong></div>
   <div><span>Minimum source-quality safeguards</span><strong>Point-in-time FDA target and Phase 3 date, SEC cover-share publication, and early FDA-action censoring</strong></div>
   <div><span>2024 vs 2025</span><strong>Separate exploratory training and descriptive holdout; no pooling into a claimed optimal result</strong></div>
   <div><span>Approved best entry / exit</span><strong>None — historical evidence not yet independently validated</strong></div>
  </div>
  <p className={css.notice}>Full pairwise research is generated in the 2024–2025 historical source workflow as JSON/CSV; the displayed counts represent configured comparisons, <strong>not verified profitable trades</strong>. Results use separate raw Alpaca prices for provisional $300 million–$10 billion capitalization and adjusted bars for provisional returns. Independent prices, stock split/share-continuity checks, the full FDA event census, trading costs, and out-of-sample replication remain required. <a href="https://github.com/pdufa/pdufa-command-center/actions/workflows/raas-active-2024-2025-original-source-research.yml" target="_blank" rel="noopener noreferrer">View historical comparison scan and artifacts</a>.</p>
  <p className={css.muted}>The T−79 to T−14 source-date entries further down this page are older single-window audit examples only. The full research configuration does not privilege or optimize around them.</p>
 </section>;
}
/** Dated source research queue: neither counts as an approved stock backtest. */
function ExpandedHistoricalCandidates(){
 const x=expansionSource;
 return <section id="raas-historical-expansion-candidates" className={css.context}
  data-raas-expanded-candidates="source-leads-only">
  <h2>Expand the historical 2024–2025 research sample</h2>
  <p><strong>{x.records.length} additional Phase 3-linked FDA case leads</strong> are now recorded for independent eligibility review. They do not increase the nine-stock research results, the validated-trade count or the RAAS score.</p>
  <p><strong>Four dated SEC share-count disclosures</strong> are now tracked across the two additional cases. The historical scan checks all 3,828 entry/exit calendar combinations for each stock using only shares published before entry, plus Alpaca raw and adjusted price bars. All results remain research-only.</p>
  <div className={css.stats}>
   <div><strong>{x.records.length}</strong><span>New dated FDA and Phase 3 case leads</span></div>
   <div><strong>{x.approvedAdditionsTo2024To2025Backtest}</strong><span>Eligible cases added to the approved return sample</span></div>
  </div>
  {x.records.map(c=><details key={c.caseId}>
   <summary><strong>{c.ticker} · {c.drug}</strong> · {c.pdufaTargetDate} FDA target · source review only</summary>
   <p>{c.indication}. Review type: {c.reviewCycleType}; trial {c.nctIds.join(", ")}.</p>
   <p>Phase 3 source date: <strong>{c.phase3EvidenceDate}</strong> · PDUFA target publicly announced <strong>{c.targetAnnouncementDate}</strong> · recorded retrospective FDA action <strong>{c.actualFDAActionDate}</strong> ({c.actualFDAOutcome}).</p>
   <p><a href={c.phase3EvidenceSourceUrl} target="_blank" rel="noopener noreferrer">Phase 3 readout source</a> · <a href={c.targetAnnouncementSourceUrl} target="_blank" rel="noopener noreferrer">Published PDUFA target</a> · <a href={c.outcomeSourceUrl} target="_blank" rel="noopener noreferrer">FDA outcome source</a>.</p>
   {expandedCoverShares.records.filter(share=>share.caseId===c.caseId).map(share=><div key={share.caseId}>
    <h4>Historical SEC share-count evidence (source only)</h4>
    <ul>{share.snapshots.map(s=><li key={s.accession}>
     <strong>{s.sharesOutstanding.toLocaleString("en-US")} shares</strong> as of {s.sharesMeasurementDate}; filed {s.filedDate}; conservative first use {s.firstConservativeEntryDate}.
     {" "}<a href={s.sourceUrl} target="_blank" rel="noopener noreferrer">Open original SEC filing</a>
    </li>)}</ul>
   </div>)}
   <p className={css.notice}><strong>Research status:</strong> Published share snapshots found, daily share continuity not verified. Market-cap classification requires Alpaca historical RAW prices. Adjusted price returns and splits require independent verification. No calibrated study result is approved.</p>
   <p><a href="https://github.com/pdufa/pdufa-command-center/actions/workflows/raas-active-2024-2025-original-source-research.yml" target="_blank" rel="noopener noreferrer">Open nightly historical source &amp; price scan</a></p>
   <p className={css.notice}>Not yet approved for the $300M–$10B study. Missing: {c.missingChecks.join("; ")}. No adjusted price return or validated historical market cap has been computed for this candidate.</p>
  </details>)}
 </section>;
}
function GoalAsOfHistory(){
 const audit=activePdufaGoalAsOfAudit();
 return <section id="raas-pdufa-asof-history" className={css.context}
   data-raas-pdufa-asof-metric-research="research-only">
  <h2>Legacy T−79/T−14 date-source example · 2024–2025 (not preferred)</h2>
  <p><strong>{audit.sourceCases} source-traced cases</strong> · <strong>{audit.revisedGoalCases} formal goal revisions</strong> · <strong>{audit.finalGoalPublishedBeforeFinalEntryCases}/{audit.sourceCases}</strong> target sources published by the provisional T−79 entry · <strong>{audit.stageMetricHistoricalApprovedCases}</strong> approved historical RAAS metric grades.</p>
  <p>For <strong>post-3-5</strong> (PDUFA date and review risks), <strong>post-6-1</strong> (exact-program target) and <strong>post-6-2</strong> (tradable exit calendar). These are historical examples only, <strong>not</strong> source evidence or scores transferred to the selected trial. No FDA outcomes or post-decision facts are used as entry features.</p>
  <div className={css.stats}>
   <div><strong>{audit.reviewYears[2024]}</strong><span>2024 FDA target-year selected cases</span></div>
   <div><strong>{audit.reviewYears[2025]}</strong><span>2025 FDA target-year selected cases</span></div>
   <div><strong>{audit.calendarWeekendEntryCases}</strong><span>Calendar T−79 entries falling on weekends</span></div>
   <div><strong>{audit.calendarWeekendExitCases}</strong><span>Calendar T−14 exits falling on weekends</span></div>
  </div>
  <p className={css.notice}>Calendar offsets and proposed next-entry / prior-exit Nasdaq sessions are not executable trading sessions, verified prices, or independent historical returns. Market closures include the exceptional January 9, 2025 shutdown; <a href="https://classic.nasdaqtrader.com/TraderNews.aspx?id=ETA2025-1" target="_blank" rel="noopener noreferrer">Nasdaq closure notice</a>. Issuer announcements do not independently validate FDA chronology or capitalization. No 0–100 RAAS grade is approved. SLNO's separately saved original announcement URL remains missing.</p>
  {audit.cases.map(c=><details key={c.caseId} className={css.group}
    data-raas-goal-asof-case={c.ticker}>
    <summary><strong>{c.ticker} · {c.application}</strong>
     <span>{c.revised?"Revised FDA target":"Original FDA target"} · {c.eventTargetDate} · T−79 {c.current.calendarEntryDate} · {c.finalTargetKnownAtFinalT79Entry?"dated source exists":"entry blocked"}</span>
     <i aria-hidden="true">▸</i>
    </summary>
    <div className={css.metricBody}>
     <div className={css.reviewGrid}>
      <div><span>Original publicly stated goal</span>
       <strong>{c.initialGoalDate} · first dated announcement {c.initialGoalAnnouncementDate}</strong></div>
      <div><span>Original T−79 → T−14 calendar window</span>
       <strong>{c.initial.calendarEntryDate} → {c.initial.calendarExitDate}</strong></div>
      <div><span>{c.revised?"Revised":"Current saved"} goal and announced-on date</span>
       <strong>{c.eventTargetDate} · {c.revised?c.revisedGoalAnnouncementDate:c.initialGoalAnnouncementDate}</strong></div>
      <div><span>Current T−79 → T−14 calendar window</span>
       <strong>{c.current.calendarEntryDate} → {c.current.calendarExitDate}</strong></div>
      <div><span>Indicative Nasdaq regular sessions · enter next / exit prior</span>
       <strong>{c.current.indicativeEntrySessionDate} → {c.current.indicativeExitSessionDate}</strong></div>
      <div><span>Calendar-to-session adjustment</span>
       <strong>Entry +{c.current.entrySessionShiftCalendarDays} days · exit {c.current.exitSessionShiftCalendarDays} days</strong></div>
      <div><span>Abbreviated session close flags</span>
       <strong>Entry {c.current.entrySessionIsEarlyClose?"early close":"normal calendar"} · exit {c.current.exitSessionIsEarlyClose?"early close":"normal calendar"}</strong></div>
      <div><span>FDA goal revision, calendar day shift</span>
       <strong>{c.sourceShiftCalendarDays} days</strong></div>
      <div><span>Pre-entry source gate for post-3-5 / post-6-1</span>
       <strong>{c.reviewState==="POINT_IN_TIME_SOURCE_LEAD_ONLY"?"Issuer source known; not graded":"BLOCKED — announcement/evidence not known at entry"}</strong></div>
     </div>
     <p className={css.muted}><strong>Original source:</strong> {c.initialGoalSourceUrl?
      <a href={c.initialGoalSourceUrl} target="_blank" rel="noopener noreferrer">Open dated original announcement</a>:
      "No separate original announcement URL retained; historical attribution not independently verified."}</p>
     {c.revised&&c.revisedGoalSourceUrl&&<p className={css.muted}><strong>Target revision:</strong> <a href={c.revisedGoalSourceUrl} target="_blank" rel="noopener noreferrer">Open dated revised target source</a> · originally announced target moved {c.sourceShiftCalendarDays} calendar days.</p>}
     <p className={css.muted}><strong>Phase 3 public-result source listed:</strong> {c.phase3ReadoutListedDate} · <a href={c.phase3ReadoutSourceUrl} target="_blank" rel="noopener noreferrer">Original clinical source</a>. Independently audited source publication chronology: <strong>not complete</strong>.</p>
     {(c.current.entryIsWeekend||c.current.exitIsWeekend)&&<p className={css.notice}>At least one proposed T−79/T−14 date is a weekend. Exact trading-session normalization, real price verification and slippage are required before any return claim.</p>}
     <p className={css.muted}><strong>Market-session limitations:</strong> Session dates are calendar proposals, not proof of ticker-level open trading, independent daily bars, adjusted prices, slippage, financing or market cap. Verify actual Alpaca/independent price data before any return comparison.</p>
     <p className={css.muted}><strong>Metric-grade status:</strong> —/100 for post-3-5 and post-6-1. Post-6-2 cannot be graded using calendar dates alone. Historical outcome decisions have not been used in this source-time calculation.</p>
    </div>
  </details>)}
 </section>;
}
/** Historical SEC shares only, never an approved 2024/25 PDUFA capitalization score. */
function SECAsOfHistory(){
 const audit=activeSECAsOfEntryShares();
 return <section id="raas-sec-entry-asof" className={css.context}
  data-raas-sec-entry-asof="research-only">
  <h2>Legacy single-window SEC share-source example · proposed T−79 (not preferred)</h2>
  <p><strong>{audit.coverFactsPublicAtProposedEntry}/{audit.caseCount}</strong> cases have a dated, pre-entry SEC share-count source lead. <strong>{audit.laterSnapshotsUnavailableAtEntry}</strong> later cover filings cannot be used at their proposed entry. <strong>0</strong> independently verified entry market caps; <strong>0</strong> independently verified adjusted entry/exit price pairs.</p>
  <p className={css.notice}>A historical cover-page share count is a dated disclosure, not a continuous or fully diluted day-of-trade share count. The $300 million–$10 billion market-cap restriction is still <strong>unverified</strong> for every case. Revised targets and proposed Nasdaq sessions are handled by the separate goal-date audit above.</p>
  {audit.rows.map(x=><details key={x.caseId} className={css.group} data-raas-sec-entry-case={x.ticker}>
   <summary><strong>{x.ticker} · {x.application}</strong>
    <span>Proposed entry {x.proposedEntrySession} · {x.currentSECShares===null?"SEC source missing":x.currentSECShares.toLocaleString("en-US")+" dated SEC shares (not verified cap)"}</span>
    <i aria-hidden="true">▸</i>
   </summary>
   <div className={css.metricBody}>
    <div className={css.reviewGrid}>
     <div><span>Proposed entry → exit regular sessions</span>
      <strong>{x.proposedEntrySession} → {x.proposedExitSession}</strong></div>
     <div><span>Cover-page outstanding common shares available at entry</span>
      <strong>{x.currentSECShares?.toLocaleString("en-US")??"No eligible pre-entry SEC source"}</strong></div>
     <div><span>Share-count observation date → conservative first public use</span>
      <strong>{x.currentSECSharesMeasurementDate??"—"} → {x.currentSECFirstConservativeUse??"—"}</strong></div>
     <div><span>Share measurement age at proposed entry</span>
      <strong>{x.currentSECDisclosureAgeDays===null?"—":x.currentSECDisclosureAgeDays+" calendar days"}</strong></div>
     <div><span>Earlier / later saved SEC share observations</span>
      <strong>{x.earlierCoverShares.toLocaleString("en-US")} / {x.laterCoverShares.toLocaleString("en-US")}</strong></div>
     <div><span>Later SEC source usable at original entry?</span>
      <strong>{x.laterCoverAvailableAtEntry?"Yes, conservative as-of date passed":"No — later filing excluded from entry source"}</strong></div>
     <div><span>Same-day market cap eligibility</span><strong>Unverified · no USD calculation promoted</strong></div>
     <div><span>Independent adjusted entry/exit prices</span><strong>Not verified · return and RAAS score withheld</strong></div>
    </div>
    <p className={css.muted}>Earlier cover shares <a href={x.earlierSECUrl} target="_blank" rel="noopener noreferrer">SEC filing</a> · Later cover shares <a href={x.laterSECUrl} target="_blank" rel="noopener noreferrer">SEC filing</a>{x.currentSECSourceUrl?<> · <a href={x.currentSECSourceUrl} target="_blank" rel="noopener noreferrer">Source eligible at proposed entry</a></>:""}</p>
    <p className={css.notice}>Source review still required: exact-day common share continuity, splits and financing, independent adjusted vendor closes and full FDA event census. Later cover difference: {x.shareSnapshotDifference.toLocaleString("en-US")} shares; this is not a proven change on the entry day.</p>
   </div>
  </details>)}
 </section>;
}
export default async function RaasWorklistPage({searchParams}:{searchParams:Promise<Params>}){
 const q=await searchParams;
 const anchorStage:RaasStage=first(q.stage)==="post"?"post":"pre";
 const rawNct=first(q.nctId),rawTicker=first(q.ticker);
 const trial= /^NCT\d{8}$/.test(rawNct)&&/^[A-Z0-9.\-]{1,12}$/.test(rawTicker)?
  {nctId:rawNct,ticker:rawTicker,drug:safe(first(q.drug)),indication:safe(first(q.indication))}:null;
 const invalidContext=!!(rawNct||rawTicker)&&trial===null;
 const data=buildRaasMetricValidationWorklist(trial);
 const available=raasDocumentedTrialOptions();
 return <main className={css.root} data-raas-validation-worklist={data.scope}>
  <header className={css.header}>
   <Link href="/tools" className={css.back}>← TOP / BOTTOM spreadsheets</Link>
   <h1>RAAS · 60-metric validation worklist</h1>
   <p>Thirty TOP pre-readout metrics and thirty BOTTOM post-readout metrics, each with its required source, current evidence leads, missing verification and calibration status.</p>
  </header>
  <div className={css.stats}>
   <div><strong>60 / 60</strong><span>Metric requirements inventoried</span></div>
   <div><strong>{data.approvedCalibrations} / 60</strong><span>Independently approved calibrations</span></div>
   <div><strong>{data.sourceMappedMetrics} / 60</strong><span>{trial?"Source-mapped metric areas for the selected trial across both stages":"Source-mapped areas in saved research across both stages"}</span></div>
   <div><strong>— / 100</strong><span>Overall RAAS remains unapproved</span></div>
  </div>
  <p className={css.notice}><strong>Research worklist, not a trading score.</strong> A single source lead does not establish a verified metric assessment, FDA approval probability, or expected stock appreciation. Missing evidence receives no 0/100 grade. Snapshot: {data.sourceAsOf}; all 60 metrics remain subject to historical holdout and source-time checks.</p>
  <nav className={css.stageNav} aria-label="Jump to TOP or BOTTOM RAAS metrics">
   <Link href={hrefForTrial(trial,"pre")} aria-current={anchorStage==="pre"?"location":undefined}>TOP · 30 metrics</Link>
   <Link href={hrefForTrial(trial,"post")} aria-current={anchorStage==="post"?"location":undefined}>BOTTOM · 30 metrics</Link>
   <Link href="/raas-scan">Full 60-metric readiness scan</Link>
   <Link href="#raas-fda-prediction-accuracy">FDA decision accuracy</Link>
   <Link href="#raas-v2-source-readiness">V2 candidate readiness</Link>
  </nav>
  <FDAAccuracySection/>
  <V2CandidateReadiness/>
  <FullRange903History/>
  <ExpandedHistoricalCandidates/>
  <GoalAsOfHistory/>
  <SECAsOfHistory/>
  <section className={css.context} aria-label="Trial source filter">
   <h2>Evidence context</h2>
   {invalidContext&&<p className={css.notice}>Invalid trial identity in the URL. Showing global source examples; no trial-specific score is inferred.</p>}
   <p>{trial?
    <>Exact trial <strong>{trial.ticker} · {trial.nctId}</strong>{trial.drug?" · "+trial.drug:""}{trial.indication?" · "+trial.indication:""}. Sources are matched by NCT, issuer, stage and supplied therapy identity.</>:
    <>All saved example programs. A source attached to another trial is never an approved grade or a source for the trial you are researching.</>}</p>
   <div className={css.trials}>
    <Link href="/raas-worklist" className={!trial?css.selected:undefined}>All source examples</Link>
    {available.map(t=><Link key={(t.stage||"")+"|"+t.nctId+"|"+t.ticker}
      href={hrefForTrial(t,t.stage||"pre")}
      className={trial?.nctId===t.nctId&&trial.ticker===t.ticker?css.selected:undefined}>
      {t.stage==="pre"?"TOP":"BOTTOM"} · {t.ticker} · {t.nctId}
     </Link>)}
   </div>
  </section>
  {(["pre","post"] as const).map(stage=>{
   const stageItems=data.items.filter(x=>x.stage===stage);
   const stats=data.byStage[stage];
   const groups=[...new Map(stageItems.map(x=>[x.groupId,{id:x.groupId,name:x.group,weight:x.groupWeight}])).values()];
   return <section id={"raas-"+(stage==="pre"?"top":"bottom")+"-worklist"} className={css.stage} key={stage}
    data-raas-worklist-stage={stage}>
    <div className={css.stageTitle}>
     <div><span className={css.eyebrow}>{stage==="pre"?"TOP · BEFORE PHASE 3 RESULTS":"BOTTOM · AFTER PHASE 3 RESULTS"}</span>
      <h2>{stage==="pre"?"TOP-RAAS":"BOTTOM-RAAS"} · all 30 metrics</h2></div>
     <strong>{stats.mapped}/30 linked to source examples · {stats.calibrated}/30 calibrated</strong>
    </div>
    <p className={css.muted}>Six scored categories, each with five metric requirements. Expand any category and then any metric to inspect source evidence, blockers and the exact requirements for approval.</p>
    {groups.map(group=>{
     const g=stageItems.filter(x=>x.groupId===group.id);
     const linked=g.filter(x=>x.sourceCount>0).length;
     return <details key={group.id} className={css.group} data-raas-validation-group={stage+"|"+group.id}>
      <summary><strong>{group.name}</strong><span>{linked}/5 source-linked · {group.weight}% category weight · 0 approved trial grades</span><i aria-hidden="true">▸</i></summary>
      <div className={css.groupBody}>
       {g.map(metric=><details key={metric.id} className={css.metric}
         data-raas-validation-metric={metric.id}>
        <summary>
         <span className={css.metricName}><small>{metric.id}</small><strong>{metric.name}</strong></span>
         <span className={metric.sourceCount?css.sourceLinked:css.sourceMissing}>{metric.sourceCount?metric.sourceCount+" source lead(s)":"No mapped sources"}</span>
         <span className={css.unapproved}>Grade pending</span>
         <i aria-hidden="true">▸</i>
        </summary>
        <div className={css.metricBody}>
         <div className={css.infoRow}><strong>Required evidence</strong><p>{metric.requiredEvidence}</p></div>
         <div className={css.infoRow}><strong>Proposed scoring interpretation (not calibrated)</strong><p>{metric.scoreRule}</p></div>
         <div className={css.infoRow}><strong>Critical risk to investigate</strong><p>{metric.criticalRisk}</p></div>
         <div className={css.infoRow}><strong>Preliminary assessment</strong><p>{metric.sourceCount?"Dated research leads identified; effect, quality, uncertainty and rating still unreviewed.":"No metric-specific lead in the selected saved source context. Nothing has been graded."}</p></div>
         <div className={css.reviewGrid}>
          <div><span>Validated metric score</span><strong>— / 100 · pending</strong></div>
          <div><span>Calibration approval</span><strong>{metric.calibrationApproved?"Approved, trial assessment still pending":"Not approved"}</strong></div>
          <div><span>Issuer-disjoint train / holdout</span><strong>{metric.historicalTrainIssuers} / 30 · {metric.historicalHoldoutIssuers} / 30</strong></div>
          <div><span>Held-out high / low groups</span><strong>{metric.historicalHighHoldoutIssuers} / 5 · {metric.historicalLowHoldoutIssuers} / 5</strong></div>
         </div>
         {["post-3-5","post-6-1","post-6-2"].includes(metric.id)&&<p><a href="#raas-pdufa-asof-history">Review 2024–2025 original vs revised PDUFA goal dates, evidence known at entry and trading-session gaps (historical research only)</a></p>}
         <h4>Recorded metric-specific sources · {metric.sourceCount}</h4>
         {metric.sourceLeads.length===0?<p className={css.muted}>No dated source linked to this metric for the selected context. Other trials' evidence is not substituted.</p>:
          <ul className={css.evidenceList}>{metric.sourceLeads.map(source=>
           <li key={source.origin+"|"+source.nctId+"|"+source.id}>
            <strong>{source.ticker} · {source.nctId} · {source.title}</strong>
            <span>{source.date} · {source.origin==="PROSPECTIVE"?"Recorded prospective source lead":"Historical pilot observation"}</span>
            <p>{source.note}</p>
            <a href={source.sourceUrl} target="_blank" rel="noopener noreferrer">Open dated source</a>
           </li>)}</ul>}
         <h4>What is missing before an approved grade?</h4>
         <ol className={css.missingList}>{metric.missingRequirements.map((s,i)=><li key={i}>{s}</li>)}</ol>
         <p className={css.muted}><strong>Historical audit:</strong> {metric.readinessReason}</p>
        </div>
       </details>)}
      </div>
     </details>;
    })}
   </section>;
  })}
  <footer className={css.footer}>
   <strong>Release gate: not passed</strong>
   <p>Historical FDA target-year census, same-issuer share continuity, independent price confirmation, predeclared metric thresholds, 30/30 disjoint holdout and exact trial reviews are still required. This page is generated from the dated, committed RAAS research feeds; it does not claim live FDA or brokerage market updates.</p>
   <Link href="/tools#tools-phase3-release-sheets">Return to TOP and BOTTOM spreadsheets</Link>
  </footer>
 </main>;
}
