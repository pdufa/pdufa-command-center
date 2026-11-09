# MAIN R60 — original-registry efficacy/statistical/safety cross-source challenge

**Observed and executed 2026-11-09 PST.** Existing draft development PR [#965](https://github.com/pdufa/pdufa-command-center/pull/965), branch `feature/medical-stage4-verified-method-matrix-20261108`. Production, authoritative FOCUS/POOL membership and independent historical Track B remain unchanged.

## Verified execution

- **[Exact development source audit run #42709199117](https://github.com/pdufa/pdufa-command-center/actions/runs/42709199117) — SUCCESS**, on source head `b7a5e951a9a7bdea935bc658dcafcd6e43c07efe`. Targeted synthetic original-byte and adversarial invalid-source/reviewer/prediction tests passed; permanent-retirement guard passed. No production deploy or clinical ledger write.
- **[Research-only artifact #13715890359](https://github.com/pdufa/pdufa-command-center/actions/runs/42709199117/artifacts/13715890359)** retained through **2027-02-07T22:09:04Z**. Contains exactly:
  1. `FOCUS_29_ORIGINAL_PRIMARY_AND_AE_SOURCE_CHALLENGE_R60.json` (source-checked exact-NCT evidence, complete primary comparison rows and individual-arm adverse-event denominators, with exceptions and 23 linked application reviews).
  2. `FOCUS_29_ORIGINAL_PRIMARY_AND_AE_SOURCE_CHALLENGE_R60.md` (29-row readable exception/coverage report).
- The workflow retrieved the previously saved R53/R54/R55 original public source archive and **separately successful R59 reviewer-queue artifact**, matched the exact R46/R55 SHA-256 receipts, re-derived primary outcome titles/analyses and arm-level adverse-event counts directly from the 29 immutable original ClinicalTrials.gov JSON records, then compared all original-derived values against existing R55 reports. Divergent source hash, NCT, mismatched reported analysis or fake clinical signoff fail closed.

## Source evidence actually reconciled

- **29/29 unique NCTs; 23 provisional application-review groups**, including correct shared-trial references without 29+ application double counting.
- **12/29** have current ClinicalTrials.gov posted primary tables; **12/29** have posted safety-arm data. This does **not** mean remaining records lack sponsor/journal/CSR/other original efficacy data, or that missing records failed a trial.
- Across those original records: **16 posted primary tables, 20 as-reported statistical comparison entries, 244 reported serious-AE term rows, 202 other-AE term rows**. Term rows are *not* numbers of affected people, pooled causality evidence or rates.
- Original source challenge surfaces current registration-vs-posted primary title/time mismatches, comparisons with no reported p literal, missing posted primary/safety sections, missing AE arm risk denominators and original-source review tasks. Those are independently **source-derived exceptions**, not clinically adjudicated failures.
- Savara IMPALA-2 `NCT04544293` retains **source-reported** primary p-value and effect, SAE arm denominators from earlier R56/R57; R58 region-specific multiplicity research remains a *threshold arithmetic exercise*, not signed prespecification or patient-level reanalysis.

## Files installed on existing development branch

- [Source challenge builder](https://github.com/pdufa/pdufa-command-center/blob/feature/medical-stage4-verified-method-matrix-20261108/new-platform/backend/scripts/build_focus_original_result_challenge_r60.py)
- [Tamper and no-promotion regression tests](https://github.com/pdufa/pdufa-command-center/blob/feature/medical-stage4-verified-method-matrix-20261108/new-platform/backend/tests/test_focus_original_result_challenge_r60.py)
- [Isolated read-only GitHub workflow](https://github.com/pdufa/pdufa-command-center/blob/feature/medical-stage4-verified-method-matrix-20261108/.github/workflows/main-r60-original-efficacy-safety-challenge.yml)

## Separation of evidence maturity

**Verified engineering:** archived source provenance, exact-NCT identity, R46/R55/R59 cross-version source conformance, R60 original registry re-derivation and auditable absence/discrepancy tasks.

**Not independently validated science:** raw individual patient efficacy/safety analysis, original locked preunblinding protocol/SAP, causal or duration-adjusted adverse-event analysis, primary/secondary estimand reconciliation, method correctness, original application-level FDA/CMC/inspection status, qualified multidisciplinary review.

**Not an outcome-validated prediction system:** `qualifiedClinicalOrStatisticalSignoffs=0`, `independentlyValidatedFdaForecasts=0/23`, `fdaApprovalProbability=null`, `measuredPredictionAccuracy=null`, official approval/CRL/timing outputs `ABSTAIN`, training and production/reviewer writes `false`.

**Next:** authenticated read-only R60 research result display with case-specific exception drilldown, and independently source-reviewed Phase 3 endpoint/safety assessments for all application groups. The original R60 research JSON is currently a GitHub Actions artifact, not operationally connected to the production dashboard. Preserve and do not merge draft until full acceptance gates pass.
