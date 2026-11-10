# MAIN Revision 43 — ACHV cytisinicline paired Phase 3 scientific desk assessment

**Prepared:** 2026-11-09 (research source review). **Status:** SOURCE-LINKED / PRELIMINARY / OUTCOME-EXPOSED / NOT AN AUTHORIZED CLINICAL GRADE. **Location:** Stage 4 draft feature branch, PR #965; not production. **Canonical trial IDs:** ORCA-2 `NCT04576949`; ORCA-3 `NCT05206370`. **Application:** cytisinicline for smoking cessation, NDA 218995 (historical FDA review outcome known). **Dossier:** `achv-cytisinicline`.

This document is an *incremental, evidence-first research assessment*, not an independently reviewed or signed assessment event. It does not replace R40 or R42 source receipts, modify the 29-FOCUS/23-application snapshot, populate any of the 40 × 20 scientific-grade positions, update the immutable clinical-review ledger, assert FDA probabilities, or create new retrospective/blind accuracy observations. FDA outcome was known while writing: **exclude this workpaper from all blinded/historical prediction-accuracy denominators**.

## 1. Verify phase and trial identities first

- ClinicalTrials.gov exact identities: [ORCA-2 NCT04576949](https://clinicaltrials.gov/study/NCT04576949); [ORCA-3 NCT05206370](https://clinicaltrials.gov/study/NCT05206370). Both were classified Phase 3 in the project's R40 29-trial snapshot. This is **record-reported phase**, not an independent phase verification or a claim about completion of every earlier phase.
- Both compared cytisinicline 3 mg three times daily for 6 or 12 weeks against placebo with behavioral support in randomized, double-blind US trials. They are **two distinct RCTs**, not two reports of the same participants: ORCA-2 810 randomized at 17 sites; ORCA-3 792 randomized at 20 sites.
- R42 independently pinned original current ClinicalTrials.gov outcome tables and statistical strings for these two NCTs in a run dated 2026-11-09, but that source-access/extraction receipt itself is not an efficacy validity audit. Source: `new-platform/frontend/data/focus-r42-primary-result-fields.json`, receipt SHA-256 `9ebfac62e6d99e105d63c107bc0aa9a52803293eba915ba4a43be3fba93f15cf`.

## 2. Source-reported primary efficacy: compare matched endpoints, not FDA outcomes

Published primary-outcome percentages, *not an independent re-analysis*:

| Study (original publication) | Treatment and endpoint window | Cytisinicline | Placebo | Absolute difference (percentage points, calculated from rounded source percentages) | Publication-reported primary evidence |
| --- | --- | ---: | ---: | ---: | --- |
| ORCA-2 | 6-week course, abstinence weeks 3–6 | 25.3% | 4.4% | +20.9 | OR 8.0, 95% CI 3.9–16.3, P < .001 |
| ORCA-3 | 6-week course, abstinence weeks 3–6 | 14.8% | 6.0% | +8.8 | OR 2.9, 95% CI 1.5–5.6, P < .001 |
| ORCA-2 | 12-week course, abstinence weeks 9–12 | 32.6% | 7.0% | +25.6 | OR 6.3, 95% CI 3.7–11.6, P < .001 |
| ORCA-3 | 12-week course, abstinence weeks 9–12 | 30.3% | 9.4% | +20.9 | OR 4.4, 95% CI 2.6–7.3, P < .001 |

**Source interpretation:** both separate studies reported favorable primary smoking abstinence outcomes for both courses, but the 6-week effect estimate varied materially between studies (20.9 versus 8.8 percentage-point absolute differences). Do not collapse the four comparisons into an unvalidated pooled effect, or treat the different populations, dates or placebo responses as interchangeable.

The 12-week course's prolonged abstinence through week 24 was 21.1% vs 4.8% (ORCA-2) and 20.5% vs 4.2% (ORCA-3). These are secondary observations, not additional independent trials or approvals.

**Primary references:**
- Rigotti et al., 2023 JAMA ORCA-2 trial https://jamanetwork.com/journals/jama/fullarticle/2807079 ; PMID 37432430 https://pubmed.ncbi.nlm.nih.gov/37432430/
- Rigotti et al., 2025 JAMA Internal Medicine ORCA-3 replication https://pmc.ncbi.nlm.nih.gov/articles/PMC12012700/ ; PMID 40257755 https://pubmed.ncbi.nlm.nih.gov/40257755/

## 3. Methodological desk findings and unresolved verification

1. **Endpoint identity — reported/linked, not independently locked.** Both publications describe biochemically verified continuous abstinence over weeks 3–6 and 9–12 as primary outcomes; obtain and compare the original protocol/SAP versions and ClinicalTrials.gov historical versions to verify prespecification and amendments. ORCA-3 article links separate original trial protocol and SAP supplements; *their full files, version signatures and locking chronology were not inspected in this workpaper*.
2. **Multiplicity — procedure reported, not reconstructed.** Both papers describe the Hochberg procedure to control two primary comparisons. Independently replay the approved analysis specifications and exact multiplicity-adjusted p-values before assigning a statistical-integrity grade. ORCA-3's paper states trial success required either primary endpoint meeting the statistical criterion.
3. **Analysis population and missingness — major sensitivity question.** Both primary efficacy analyses are intention-to-treat. ORCA-2 trial follow-up was completed by 618/810 (76.3%); ORCA-3 by 628/792 (79.3%). Missing smoking status was classified as smoking in published analyses; the ORCA-3 method allows a single missed visit under the primary abstinence definition. Verify full CONSORT flow, differential missingness, missing-not-at-random sensitivity and implementation from locked SAP, not just abstract summaries.
4. **Replication — supportive but heterogeneous.** The ORCA-3 paper explicitly compares prior ORCA-2 findings and discusses possible pandemic-period external behavioral conditions as one unproven explanation for 6-week between-trial effects. That speculation is not a calibrated adjustment. Compare site/country, demographics and adherence before pooling.
5. **Safety — reported trial data, not independently adjudicated causality.** ORCA-2 publication reports any serious adverse event in 8/270 (12-week), 10/269 (6-week), versus 3/270 treated placebo recipients. ORCA-3 reports serious treatment-emergent adverse events in 8/260 (12-week), 8/263 (6-week), versus 8/262 treated placebo. Authors report zero serious treatment-related events in both trials. Treatment-relatedness is author/investigator-attributed; actual SAE narratives, exposure, discontinuations and updated postsubmission safety require re-review.
6. **Denominators — distinguish randomized and dosed sets.** ORCA-3 randomized 792 while 785 took at least one dose; its safety denominators are 260, 263 and 262. ORCA-2 randomized 810 while 809 were in safety analysis; its placebo safety denominator is 270. Never silently use the randomized denominator for safety percentages.
7. **Generalizability — unreviewed.** Both enrolled motivated cigarette smokers ready to quit with behavioral support. ORCA-3 excluded several high-risk conditions and certain concurrent cessation medications. Sponsor population broader than the study inclusion criteria remains a separate FDA labeling question.
8. **Nonclinical/CMC/FDA review-cycle — separate from clinical efficacy.** Historical outcome is independently visible in the FDA's publicly disclosed redacted Complete Response Letter for **NDA 218995**, signed **2026-06-20**. Visible approvability items include manufacturing facility CGMP remediation and prescribing-information/labeling changes. It also requests an updated safety package on resubmission. Do not equate statistically favorable trials with FDA approval, or claim all future factory/labeling barriers are resolved.

## 4. FDA historical decision and leakage prevention

The [FDA original redacted Complete Response Letter](https://download.open.fda.gov/crl/CRL_NDA218995_20260620_Redacted.pdf) says it could not approve the application in its current form and identifies facility-inspection and prescribing-information corrective work. Achieve's [June 22, 2026 disclosure](https://ir.achievelifesciences.com/news-events/press-releases/detail/264/achieve-life-sciences-receives-complete-response-letter-from-fda-for-cytisinicline-nda) says no clinical efficacy or safety deficiencies were identified. The *agency letter* and the *sponsor interpretation* are kept distinct.

**Observed historical result:** CRL, June 20, 2026, NDA 218995. **Outcome-awareness:** YES. **Blind replay eligible:** NO. **FDA model forecast from this workpaper:** NONE. **Calibrated probability or accuracy:** NONE. **Subsequent review cycle:** requires exact new FDA acceptance/resubmission evidence, not an inferred PDUFA date.

Research-only readout: favorable source-reported clinical efficacy in distinct RCTs can coexist with a negative FDA approval decision for manufacturing/labeling reasons. An FDA decision engine therefore needs independent CMC, labeling and exact-cycle review beyond a Phase 3 efficacy score. This is a post-outcome methodological lesson, not a backtested predecision prediction.

## 5. Next evidence work / no grading

| Research action | Current status | Promotion gate |
| --- | --- | --- |
| Identify Phase 3 exact-NCT source/provisional registry phase | SOURCE_REPORTED | Independent identity and dated phase check |
| Compare four paper-reported primary efficacy cells | PRELIMINARY_SOURCE_REVIEW | Original outcome table, endpoint hierarchy, protocol/SAP lock |
| Review missing-data/ITT and full CONSORT | PARTIAL | Original supplementary SAP, trial-level flow and sensitivity replay |
| Reconcile SAEs and treatment-related attribution | PARTIAL | Original narratives, coding, exposure, protocol-defined windows |
| Separate FDA historical NDA and manufacturer/labeling | DOCUMENTED_OUTCOME_EXPOSED | Exact new cycle and independently verified CMC remediation |
| Independent science/medical method review | NOT_STARTED | Authorized independent reviewer, immutable evidence/version ledger |
| Calibrated approval/CRL/delay forecast | ABSTAIN | Qualified method scores, source chronology, valid out-of-time test |

**No change to authoritative counters:** 29 FOCUS source records; 23 provisional application profiles; 16 registry primary tables from 12 current posted result studies; 0 authorized method grades; 0 reviewer signoffs; 0 validated FDA forecasts; 0 independently valid blind historical tests. This workpaper must not increment the original 800-method positions for either trial.

**Next candidate after ACHV paired evidence:** process an outcome-unrevealed or current predecision candidate through the same phase-first evidence order (e.g., SVRA NCT04544293 for efficacy/AE tables), while retaining separate original time cutoffs for any true historical blind testing.
