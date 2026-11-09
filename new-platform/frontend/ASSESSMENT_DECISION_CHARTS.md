# ASSESMENTS — FDA decision accuracy charts

The two pie panels on /predictions/assessment represent **different measures**:

1. **Overall prediction validity against actual FDA action**: correct versus incorrect, only among a predecision-frozen, completed approval-or-CRL prediction whose exact FDA application cycle has a later independently verified FDA decision. The denominator excludes pending, other, unavailable and unverified actions. Each cycle contributes the **first** frozen completed prediction, even if later revisions exist, to prevent cherry-picking.
2. **Most recently completed prediction**: identifies the last completed/frozen prediction by its timestamp, exact application cycle, ticker, linked NCT(s), drug and indication. If its independently calibrated approval/CRL probabilities were saved, its pie displays those two complementary probabilities. Without that calibration, the pie is blank rather than fabricating proportions. FDA review-delay risk is separate from this binary outcome.

**Evidence required** to add rows to `frontend/data/fdaPredictionDecisionAudit.json`:

- Signed immutable prediction ID, exact FDA application/review-cycle ID, issuer, drug, indication and linked NCT IDs.
- A completion/freeze timestamp with timezone, recorded **before** the official decision; a categorical approval/CRL call, not ABSTAIN; status `COMPLETED`.
- Verified official FDA outcome source URL, actual decision timestamp and explicit verification flag. A sponsor filing target, ClinicalTrials.gov status, PDUFA date, press speculation, and result posting are *not* a decision.
- Numerical probabilities only when independently calibrated and validated. Approval and CRL components must each be between 0 and 1 and sum to 1. Delay forecasts must be tracked separately.
- Cohort origin `PROSPECTIVE` or `HISTORICAL_LOCKED`. Historical predictions must be reproducibly frozen using only information available before the FDA decision; hindsight reconstruction does not qualify.

The current registry is deliberately empty because the present medical analysis output records evidence collection and ABSTAIN outcomes, **not** verified frozen FDA predictions. The charts must remain empty until real records pass these gates. This frontend ledger is an interim display contract, not an automatic database sync. A future backend integration must use the same data provenance and immutable event controls; never count registry source scans, archived RAAS material, or retrospective forecasts created after actual decisions as successes.

The overall chart measures crude directional hit rate, not probabilistic calibration, performance against a baseline, sensitivity, specificity, or a guarantee of future FDA prediction reliability.
