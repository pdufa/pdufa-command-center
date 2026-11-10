# MAIN Revision 77 — Launch-HTN original H1–H7 multiplicity and missingness source crosswalk

**Stage-4 independent medical intelligence, November 9 2026 (Pacific)**

**Classification:** source-reported original journal evidence research, **NOT** prospectively authenticated signed original SAP, blinded independent scientific assessment, FDA application/label outcome, or calibrated probability. Preserve canonical 29 FOCUS NCT records and 23 provisional application groups. The active system cannot use retired RAAS/GEM scientific scores.

## Exact original sources and page anchors

- Trial: **NCT06153693**, MLYS / lorundrostat Launch-HTN.
- [Original JAMA main article and nine listed supplements](https://jamanetwork.com/journals/jama/fullarticle/2835763), 2025-06-30, DOI **10.1001/jama.2025.9413**.
- [Separate indexed PMC article/supplements](https://pmc.ncbi.nlm.nih.gov/articles/PMC12210145/), Supplement 1 exact filename **jama-e259413-s001.pdf**.
- **Original PDF physical pages** visually verified via publisher PDF: **6** eFigure 2 directional multiplicity graphic; **11** eTable 1 H1–H7 endpoints; **12** imputation methods; **13** eTable 2 analytic methods; **15** eTable 3 sensitivity; **17** eTable 4 safety laboratory tables.
- Permanent signed publisher-CDN query parameters are NOT checked in: source article and supplement filename are stable provenance; source PDF raw-byte SHA-256 receipts remain **0/7** in the separate original-document capture workflows.

## Seven original published hypotheses and source diagram

| Hypothesis | Source-reported statistical target | Material distinction |
| --- | --- | --- |
| **H1** | Week-6 automated office systolic blood-pressure change, lorundrostat pooled 50 mg vs placebo | **Primary**, randomized |
| **H2** | Week-6 proportion with office SBP below 130 mm Hg, 50 mg vs placebo | Key secondary, randomized |
| **H3** | Week-12 change, randomized escalation-option 50→100 mg vs placebo | Randomized to escalation **strategy**, not necessarily escalated individuals |
| **H4** | Week-6 change among patients taking two antihypertensive drugs, 50 mg vs placebo | Key secondary stratum |
| **H5** | Week-6 change among patients taking three or more antihypertensive drugs, 50 mg vs placebo | Resistant-hypertension stratum; eTable 2 models H4/H5 together |
| **H6** | Week-6 treatment interaction with obesity/body-mass index | A treatment-by-BMI comparison, not just an independent efficacy estimate in obese patients |
| **H7** | Week-12 within-person change among those *actually escalated* to 100 mg at week 6 | **Within-participant, non-randomized comparison**; not interchangeable with randomized H3 |

The source eFigure 2 has these **eight directed arrows**: **H1→H4, H1→H5, H4→H3, H5→H3, H3→H2, H2→H7, H2→H6, H7→H6**. The figure annotates **½** only on **H1→H4**, **H1→H5**, **H2→H7** and **H2→H6**. For the other arrows it does not visibly print a numeric transfer fraction. Do **not** infer full recycled-alpha weights, graph continuation if one upstream test fails, or actual FWER significance from arrow topology alone. The methods are source-mapped, **not mathematically recalculated**.

## Published effect and sensitivity, not reproduced by independent reviewers

- Main publication's randomized pooled 50-mg vs placebo Week-6 primary contrast: **−9.1 mm Hg**; 95% CI **−13.3 to −4.9**; author-reported **p<0.001**.
- Supplement 1, eTable 3: author-reported sensitivity 1 **−9.1 mm Hg**, sensitivity 2 **−8.6 mm Hg**, observed-data sensitivity 4 **−9.1 mm Hg**, each p<0.001; the authors report no tipping point within a maximum prespecified ±40 mm Hg shift.
- A claim of statistical robustness still needs verified original estimand/analysis script, exact source population and the relevant regulatory endpoint requirements. These published results do not independently prove an official FDA application-level outcome.

## Source-reported missingness and sensitivity — never a substitute for signed SAP

Supplement 1 physical page 12 describes **1,078 treated** participants and **24 intercurrent events** (23 AE discontinuation events and one death). It reports **10** adverse-event-related missing Week-6 observations and **12** Week-12; **1** death-related Week-12 missing observation. Separately it identifies **56** other Week-6 and **67** other Week-12 missing observations assumed MAR. These categories must not be double counted as pooled denominator-independent events.

The published method uses a retrieved-dropout **treatment-policy MNAR imputation** for AE discontinuations, an adverse outcome handling rule for death, randomized-group MAR imputation for remaining missingness, a fallback **jump-to-reference** approach under nonconvergence, and **1,000 multiply imputed datasets**. Actual seed, analysis script, convergence behavior, treatment interaction and exact regulatory estimand have **not** been independently rerun.

## Published laboratory exposure and potential benefit-risk context

Supplement 1 eTable 4 has separate **exposed-arm** denominators **270** escalation option / **538** fixed 50 mg / **270** placebo, not simply the randomized ITT total of 1,083.

| Source-reported laboratory observation | Escalation arm 270 | Fixed 50-mg arm 538 | Placebo 270 |
| --- | ---: | ---: | ---: |
| Serum sodium below 130 mmol/L | 11 | 14 | 4 |
| Serum potassium observed 5.6–6.0 mmol/L | 29 | 38 | 3 |
| Serum potassium confirmed 5.6–6.0 mmol/L | 24 | 31 | 2 |

The laboratory categories must not be pooled or interpreted as serious-event or causal risk without exposure timing, re-testing criteria, underlying kidney function, blood pressure, dose escalation and all AE records. A lower BP endpoint p-value is **not** a complete benefit-risk or CMC/label assessment.

## Audit gates — status at R77

- Original prospectively **signed and locked SAP before unblinding**: **NOT VERIFIED**; source chronology still has R75 printed-year contradictions.
- Full original PDF source byte SHA and first-public authenticity: **0/7 independently archived**; publisher HTML/PDF access constraints remain.
- Reproduced H1 statistical analysis, H2–H7 exact source graph multiplicity and numeric FWER recycling: **0 independently recalculated**.
- AE safety, renal/electrolyte and secondary sensitivity independent science signoffs: **0**.
- Original FDA CMC, inspections, proposed label/review cycle and regulatory adjudication: **not independently signed**.
- Independent valid historical outcome-blind accuracy test: **0**.
- **Current FOCUS validated application forecasts 0/23, official FDA approval/CRL ABSTAIN, timing UNKNOWN, calibrated accuracy unavailable.** No live clinical scoring/model-training/production writes.

## Implemented developer acceptance

Original-source report: `new-platform/frontend/data/focus-r77-launch-htn-published-multiplicity-crosswalk.json`. Fail-closed source validator: `new-platform/frontend/lib/focus-r77-launch-htn-published-methods.ts`. Visible source-research panel: `new-platform/frontend/app/predictions/evidence-gaps/LaunchHtnMethodsR77.tsx`, in Launch-HTN's existing evidence-gaps detail only. Adversarial source/grade tests: `new-platform/frontend/tests/focus-r77-launch-htn-published-methods.test.cjs`. Distinct source-only CI and existing desktop/390px Chromium acceptance check exact data, lack of grades, correct display and no production writes.

**Next**: acquire original signed statistical plans and database lock/unblinding correspondence; independently reproduce all seven endpoint analyses from source statistical datasets/code; perform subject-level missingness/safety adjudication; then assign qualified independent review with immutable evidence signatures. A published positive p-value is not a qualified FDA application decision and should never be counted as backtested predictive accuracy.
