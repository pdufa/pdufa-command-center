# MAIN Revision 23 — first reproducible quantitative scientific analyses

**Scope:** ACACIA-HCM (NCT06081894, CY 6033). Date of research evidence snapshot: November 8, 2026. Draft PR #965 only.

## Progress beyond source-document checklist counts

This revision introduces **actual clinical-trial numerical research calculations**, not another document-availability index. It is intentionally confined to two exact scientific positions that already appear among the 18 source-mapped pilot handoffs:

| Position | Reproducible metric | Scientific interpretation |
| --- | --- | --- |
| Assessment 5.1, method 12 (multi-method adjudication) | Both published primary endpoint effect estimates, reported 95% CIs, reported P values, approximate standard errors from rounded intervals, **2/2 primary estimates with CIs above zero and sponsor's 0.025 threshold** | Directional published statistical finding only; does not independently validate locked SAP, clinical importance or endpoint hierarchy |
| Assessment 5.3, method 19 (independent reproducibility audit) | Exact treated and placebo numerators/denominators, raw rates and arithmetic risk differences for LVEF below 50% and any serious adverse event; **2/2 outcomes show higher unadjusted treated-arm frequencies** | Descriptive imbalance, not confounder/time-adjusted causal risk, hypothesis test or independent safety signoff |

The first two co-primary effects published in the [NEJM trial report](https://doi.org/10.1056/NEJMoa2603021) are **KCCQ-CSS +3.0 points (95% CI +0.5 to +5.5, reported P=0.02)** and **peak VO2 +0.67 mL/kg/min (95% CI +0.22 to +1.11, P=0.003)**. The new code reproduces approximate SEs **1.2755** and **0.2270** by dividing rounded 95% CI widths by 3.92. These estimates are imprecise arithmetic summaries; they do not independently reproduce the original statistical model.

The same report gives LVEF below 50% **27/258 versus 2/259** and serious adverse events **52/258 versus 38/259**. The new engine independently calculates raw treated-minus-control risk differences **+9.69 percentage points** and **+5.48 percentage points**. Safety monitoring and causality must be independently examined. An unreconciled serious heart-failure adverse-event discrepancy **11/1 versus 12/3** is explicitly excluded from any safety composite, and no such composite score is created.

## Files

- `new-platform/frontend/lib/acacia-quantitative-science.ts`: strict source-, exact-NCT-, phase-, numerical-value- and reviewer-state-pinned evaluator. A missing original input or any incompatible phase, reviewer, source or FDA status **withholds** outputs instead of imputing a clinical grade or deriving approval probability.
- `new-platform/frontend/app/predictions/assessment/PilotScientificSignalPanel.tsx`: two quantitative research cards inserted ahead of the older 3/5, 3/5, 2/5 document-readiness checks. Each shows original estimates, denominators, uncertainty, source link, limitations and why official grades are withheld.
- `new-platform/frontend/tests/acacia-quantitative-science.test.cjs`: verifies both numerical effects, rates, method identities, positive-directional counts, source integrity, unchanged clinical ledger, no FDA numbers, tampering rejection and UI copy.

**Unchanged:** Phase-first work; mapped research source leads 18/800; 782 remaining positions unexamined; official human clinical grades **0/800** for pilot and **0/23,200** total potential method positions; forecast approval/CRL/delay **ABSTAIN** and calibrated accuracy **NOT_CALIBRATED**. The two new research-method calculations are **NOT 0–5 clinical efficacy/safety scores** and must not be copied into the independent scientific ledger. Provisional documentary scores (3/5, 3/5, 2/5) continue separately.

## Future implementation gates

1. Reconcile the final dated and locked CY6033 statistical analysis plan, prespecified multiplicity and sensitivity results.
2. Authenticate clinical-importance thresholds and conduct independent endpoint robustness review.
3. Independently adjudicate serious heart-failure adverse-event definitions, line listings, safety populations, follow-up windows and causality.
4. Develop method-specific clinical quality rubric, inter-rater agreement and authorized append-only reviewer events; do not auto-promote these descriptive numbers to clinical grades.
5. Calibrate held-out historical FDA outcomes before declaring a prediction or accuracy number.
6. Adapt the tested rubric and source evaluator to all phase-appropriate FOCUS methods and the remaining 28 trials.

**Release boundary:** Draft PR #965 only; no Render deployment, production application change or reviewer write permissions. The separate read-only nightly source monitor installed on default branch remains independent.
