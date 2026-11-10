# MAIN Revision 33 — ACACIA-HCM provisional evidence direction and FDA pathway scenarios

**Date / source cutoff:** November 8, 2026. **Exact pilot:** NCT06081894, ACACIA-HCM (CY 6033), nonobstructive HCM. **Release boundary:** Draft PR #965, preview only. No FDA prediction, clinical-grade writes or production rollout.

## Current verified engineering and scientific boundaries

The Stage 4 preview has an authenticated 40 × 20 read-only assessment matrix. [Normal-session readback run 42564594358](https://github.com/pdufa/pdufa-command-center/actions/runs/42564594358) passed on November 9, 2026 at 04:58 UTC: correct NCT, 800 source-audit receipts, unchanged clinical review history, zero independent grades, FDA decisions ABSTAIN, accuracy NOT_CALIBRATED. Auditing 800 source *positions* is **not** conducting 800 scientific grades.

Existing source data in `acacia-pilot-prediction-workup-20261108.json` give a strictly descriptive, source-linked pilot interpretation:

- [Published primary report, PubMed 42663312](https://pubmed.ncbi.nlm.nih.gov/42663312/) reports both co-primary endpoints statistically favorable: KCCQ-CSS difference +3.0 points (95% CI 0.5–5.5), peak VO₂ +0.67 mL/kg/min (95% CI 0.22–1.11). Original locked pivotal statistical plan and independent clinical-importance review remain open.
- LVEF below 50%: 27/258 aficamten versus 2/259 placebo; all serious AEs: 52/258 versus 38/259. Unadjusted arm differences are +9.69 and +5.48 percentage points respectively. These are not causal estimates, a benefit-risk grade or FDA approval probabilities.
- Heart failure SAE counts conflict between secondary reporting (11/1) and [issuer documentation](https://www.sec.gov/Archives/edgar/data/1061983/000119312526447408/cytk-20260930.htm) (12/3). Original event definitions, populations, follow-up windows and corrections remain unresolved.
- The issuer's November 4, 2026 report says the exact *nonobstructive* HCM supplemental filing was planned for Q4; an accepted ACACIA-specific application/date was **not established by that report**. Never substitute an obstructive-HCM review deadline.

## Installed development feature

`new-platform/frontend/lib/acacia-provisional-decision.ts` exposes an exact-trial, fail-closed, source-identity-gated qualitative synthesis. It validates the reported pivotal effect/CI, participant counts, source identities, current unreviewed clinical grade state, 18 mapped research leads and the exact nonobstructive-HCM filing state. It yields six evidence domains and a high **unquantified** uncertainty label, not a learned model.

`PilotProvisionalResearchModel.tsx` is embedded above the prior scientific analysis on the exact trial's PREDICTIONS/assessment page. Four user-editable assumptions (filing, locked SAP, safety adjudication, independent review) produce named conditional pathways: PRE_FILING, CONDITIONAL_APPROVAL_PATH, REGULATORY_CONCERN_PATH and ADDITIONAL_REVIEW_PATH. All inputs are explicitly hypothetical. They never write to an evidence source, ledger, grade, review-signoff or prediction history. The live output remains APPROVAL/CRL/REVIEW_DELAY **ABSTAIN**, FDA probability **null** and accuracy **NOT_CALIBRATED**.

`new-platform/frontend/tests/acacia-provisional-decision.test.cjs` covers exact-NCT source gates, tampered source/phase/grade refusal, all scenario paths and non-release of probability or accuracy. Initial feature-head build [CI run 42566789877](https://github.com/pdufa/pdufa-command-center/actions/runs/42566789877) passed backend, frontend (824/824) and retired-asset regressions. Production and isolated Render service are unchanged.

## Live screen acceptance

The existing protected `main-medical-preview-auth-readback.yml` checks normal dashboard authentication and no clinical writes. This revision extends its existing HTTP/HTML readback to **require** the visibly rendered new pilot panel, reset control, explicit hypothetical label and permanent actual ABSTAIN / uncalibrated wording. A green build is not itself a signed-in user-device test. Check the separate exact-commit hosted readback before declaring this screen operational.

## Next *real* scientific milestone

Acquire and authenticate the locked CY 6033 SAP, reconcile heart-failure SAE source data and safety populations, qualify independent phase/method reviewers, record append-only signed findings, then build an outcome-labeled historical FDA cohort with frozen forward holdout predictions and audited calibration metrics. Until then, display source-supported directional research separately from regulatory predictions. **Do not invent 0–5 clinical grades or FDA percentages, deploy this draft to production, or enable reviewer-write/vault secrets automatically.**
