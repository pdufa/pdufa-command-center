# MAIN Revisions 54–55 — Source-linked FOCUS scientific methods and clinical review packets

**Recorded:** 2026-11-09. **Branch:** `feature/medical-stage4-verified-method-matrix-20261108`. **Draft PR:** #965.

## Executed scientific source work, not a validated FDA forecast

[Original verified Revision 54 source-methods run #42695295081](https://github.com/pdufa/pdufa-command-center/actions/runs/42695295081): **SUCCESS**, 53 target tests pass, entire original 29 NCT / 23 application membership preserved, all 23 originally registered currently attached original protocol/SAP PDFs SHA-verified; every PDF inspected for **eight** methodological review dimensions with page-cited links. The source excerpts are machine-readable *leads*, not correctly adjudicated statistical or FDA methodology.

**Original verified Revision 55 clinical review-packet run [#42696796318](https://github.com/pdufa/pdufa-command-center/actions/runs/42696796318): SUCCESS**, **67 tests PASS**, with original SHA-256 receipts, full public-source archive in [artifact #13710081166](https://github.com/pdufa/pdufa-command-center/actions/runs/42696796318/artifacts/13710081166), expiring 2027-02-07. This contains:

- `FOCUS_23_APPLICATION_METHOD_SOURCE_CROSSWALK_R54.json` — all 29 unique NCTs / 23 application IDs, original protocol/SAP PDF document IDs and SHA, one-based page-linked leads for primary endpoints, estimands/populations, statistical models, multiplicity control, missingness/intercurrent events, sensitivity methods, adverse event safety, and protocol/SAP amendments. **12 trials have attached current protocol/SAP PDFs; 17 do not**, and absence in the CURRENT registry is not absence from all published sources.
- `FOCUS_23_APPLICATION_EFFICACY_SAFETY_SOURCE_REVIEW_PACKETS_R55.json` — all **23** application research packets, references to each of the **29** original trial records without counting a shared trial twice, original current public registry SHA receipts, **16** actually POSTED primary tables across **12** NCTs, **20** reported primary statistical comparisons, **244** serious-adverse-event term rows and **202** other-adverse-event term rows with trial-specific arm-level serious AE denominators. There are **12** NCTs with posted adverse-event arms. The 244/202 are term rows, not patients and not pooled comparative rates.

All primary effect estimates, confidence intervals, `pValue` values, sample-group and safety denominators remain **exactly as currently publicly reported**, not statistically recalculated or independently signed. An absent current result is not a failed study.

## First case-specific primary efficacy and methods cross-check: Savara IMPALA-2 / NCT04544293

**Current ClinicalTrials.gov original study response**: [NCT04544293](https://clinicaltrials.gov/study/NCT04544293), archived SHA-256 `35ae34b6edb0d1d9cdec897d73a4058cb63cd0e0594b0eda8f5f9be0b75f8b55`.

- **Current registered-and-posted primary title and timeframe:** *Change from baseline in percent-predicted diffusing capacity of the lung for carbon monoxide (DLCO), adjusted for hemoglobin, at Week 24*. The currently registered and posted title/timeframe text matches, but historical prereadout title/timing and original analysis-plan lock remain unverified.
- **Reported primary statistical comparison:** molgramostim vs placebo, **estimated mean difference 6.0**, **reported 95% CI 2.5 to 9.4**, and **reported p-value 0.0007**, using mixed-model repeated-measures analysis (MMRM) adjusted for baseline predicted DLCO, treatment, visit, region, severity stratum and treatment-by-visit. These are the public registry's source-reported numbers, **not independently recalculated, multiplicity-verified, sponsor-independent or FDA-endorsed**.
- **Current posted serious adverse event participants:** molgramostim **14 of 81** at risk and placebo **20 of 83** at risk. **Reported deaths: 0/81 and 0/83**. These are trial-arm denominators and participant counts, **not a causal safety verdict**. The complete AE event terms, duration and other safety signals require independent review; do not extrapolate pooled risk or conclude that approval is certain.
- **Current registry-attached [Savara original protocol v10](https://cdn.clinicaltrials.gov/large-docs/93/NCT04544293/Prot_000.pdf#page=68)**, document dated **October 9, 2024**, describes Week 24 DLCO primary efficacy estimand, analysis population and missingness/treatment-policy handling on approximate PDF pages **67–70**, with further multiple-imputation detail on PDF page **74**.
- **Current registry-attached [Savara statistical analysis plan v1.0](https://cdn.clinicaltrials.gov/large-docs/93/NCT04544293/SAP_001.pdf#page=25)**, document dated **April 24, 2024**, describes Week 24 DLCO primary hypothesis, sequential testing, family alpha-splitting and conditional secondary tests on approximate PDF pages **25–27**; missing-data treatment and SAP-to-protocol differences require formal section-by-section reconciliation.
- **Critical unresolved chronology:** the attached SAP is document-dated *before* the latest attached protocol version. The original public posting date of each, intermediate protocol/SAP amendments, signed final SAP lock before unblinding, and any final prespecified estimand/multiplicity shifts have **NOT** been authenticated. Source-document printed dates alone must not be called prospective prespecification.

This Savara comparison supplies concrete primary efficacy and arm-level safety evidence to **scientific review**. It is not a reviewer-signed clinical grade, an FDA application review-cycle conclusion, a CMC review or a defensible approval probability. **Official pending FDA prediction: ABSTAIN** until those gates are satisfied.

## Other priority application source limitations

- CAPR/deramiocel `NCT05126758`: no posted primary results or attached protocol/SAP in the CURRENT registry snapshot; alternate sponsor papers, dated regulatory releases and accessible historical sources must be examined. Not necessarily negative evidence.
- COGT/GIST `NCT05208047`: current trial record focuses on earlier pharmacokinetic parts; no current attached protocol/SAP or posted pivotal primary efficacy result. The correct pivotal application-specific trial(s) must be crosschecked before treating this NCT as the sole efficacy evidence; no unverified approval/CRL inference.
- Other attached protocols/SAPs are prepared with exact page links across all 12 document-bearing trials for a real scientific reviewer.

## Technical change and independent Track B status

New scripts:
- `new-platform/backend/scripts/build_focus_methods_crosswalk_r54.py`
- `new-platform/backend/scripts/assemble_focus_clinical_review_packets_r55.py`
- Dedicated regression and provenance tests `tests/test_focus_methods_crosswalk_r54.py` and `tests/test_focus_clinical_review_packets_r55.py`.
- Both steps in the existing **read-only R53 GitHub Actions job**, retaining two independent output JSONs alongside unchanged original source bytes. No writes to authoritative reviewer/clinical ledger or production.

Historical Track B retains its independent run [#42689302249](https://github.com/pdufa/pdufa-command-center/actions/runs/42689302249), 412 selected source-action records and 186 approved-only report actions; these do **not** establish an unbiased consecutive NDA/BLA filing population. **0 independently adjudicated historical FDA review-cycle holdouts, no genuinely calibrated accuracy, and no automatic prediction improvement yet**. Track B was not suspended or reactivated through retired RAAS/scans.

**Research readiness:** 29/29 unique trials and 23/23 current evidence packets, **0** independent scientific review signoffs, **0** independently verified original locked pre-readout SAPs, **0/23** validated FDA application outcome forecasts, **0** legitimate outcome-blind historical FDA backtests. Claiming 100% proficiency or accuracy is prohibited.

**Next work:** independent clinical result reproducibility and multiplicity/SAP version reconciliation beginning with Savara; obtain original dated Phase 3 source evidence and sponsor/regulator documents for CAPR and COGT; separate historical original NDA/BLA consecutive cohort from outcome-selected case sources before any backtest or calibrated probability.
