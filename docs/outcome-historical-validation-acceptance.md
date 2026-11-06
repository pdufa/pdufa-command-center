# OUTCOME historical validation acceptance checklist

Status: RESEARCH ONLY. This checklist does not certify any review cycle, authorize predictions, or enable trading.

## Evidence certification (per application and review cycle)
- [ ] Stable application ID, submission type, review cycle, and final FDA action identity independently matched.
- [ ] Exact FDA receipt date supported by dated primary agency evidence; sponsor-only dates cannot substitute.
- [ ] Final FDA action and date independently sourced.
- [ ] Historical feature snapshot timestamp precedes the decision.
- [ ] Each feature source publication timestamp is no later than its snapshot timestamp.
- [ ] Independent reviewer, review date, and supporting evidence recorded.
- [ ] Duplicate cycles and contradictory records rejected.

## Cohort and evaluation
- [ ] Complete, unbiased eligible application denominator independently verified (not the selected 20-action research sample).
- [ ] Eligibility, exclusions, and missingness pre-registered before outcomes are inspected.
- [ ] Chronological train/validation/test split with no overlapping application or review-cycle leakage.
- [ ] Frozen model version, cutoff date, feature manifest, and decision threshold.
- [ ] Held-out counts of TP, TN, FP, FN with sensitivity, specificity, PPV, NPV and uncertainty intervals.
- [ ] Brier score, log loss, calibration bins/plot and subgroup stability reported.
- [ ] Baseline comparison, drift monitoring, and independent reproduction completed.

## Existing blockers at checklist creation
- Three open receipt-boundary actions (two BLA 125745, one BLA 125840).
- No independently verified complete application denominator.
- No certified historical as-of source publication and review-cycle set.
- No held-out chronological calibration.
- Model eligible records: zero in the current research-only readiness contract.

## Release gates
No probability, PASS/NO PASS recommendation, prediction accuracy percentage, or trading recommendation may be labeled validated until all required evidence and testing gates pass. CI passing is necessary but not sufficient. Preserve existing GEM JR/GEM FS/FA associations.
