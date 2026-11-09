# ASSESMENTS — FDA decision accuracy charts

The two pie panels on /predictions/assessment represent **different measures**:

1. **Overall prediction validity against actual FDA action**: correct versus incorrect, only among a predecision-frozen, completed approval-or-CRL prediction whose exact FDA application cycle has a later independently verified FDA decision. The denominator excludes pending, other, unavailable and unverified actions. Each cycle contributes the **first** frozen completed prediction, even if later revisions exist, to prevent cherry-picking.
2. **Most recently completed prediction**: identifies the last completed/frozen prediction by its timestamp, exact application cycle, ticker, linked NCT(s), drug and indication. After a verified FDA decision, its pie shows a one-case comparison as **Accurate** or **Not Accurate**. Before the actual decision is verified, it displays an independently calibrated approval/CRL probability split only if one exists. Otherwise it displays a neutral, labeled zero-data placeholder. FDA review-delay risk is separate from this binary outcome.

**Evidence required** to add rows to `frontend/data/fdaPredictionDecisionAudit.json`:

- Signed immutable prediction ID, exact FDA application/review-cycle ID, issuer, drug, indication and linked NCT IDs.
- A completion/freeze timestamp with timezone, recorded **before** the official decision; a categorical approval/CRL call, not ABSTAIN; status `COMPLETED`.
- Verified official FDA outcome source URL, actual decision timestamp and explicit verification flag. A sponsor filing target, ClinicalTrials.gov status, PDUFA date, press speculation, and result posting are *not* a decision.
- Numerical probabilities only when independently calibrated and validated. Approval and CRL components must each be between 0 and 1 and sum to 1. Delay forecasts must be tracked separately.
- Cohort origin `PROSPECTIVE` or `HISTORICAL_LOCKED`. Historical predictions must be reproducibly frozen using only information available before the FDA decision; hindsight reconstruction does not qualify.

The chart legends always display **Accurate** (green) and **Not Accurate** (orange), including when the real audited counts are both zero. A neutral placeholder with explicit zero comparison count is not a 50/50 accuracy pie and does not imply any accuracy percentage. Historical retrospective-development counts from old models are **not** ingested into the live accuracy report.

The current registry is deliberately empty because the present medical analysis output records evidence collection and ABSTAIN outcomes, **not** verified frozen FDA predictions. The charts must remain empty until real records pass these gates. This frontend ledger is an interim display contract, not an automatic database sync. A future backend integration must use the same data provenance and immutable event controls; never count registry source scans, archived RAAS material, or retrospective forecasts created after actual decisions as successes.

The overall chart measures crude directional hit rate, not probabilistic calibration, performance against a baseline, sensitivity, specificity, or a guarantee of future FDA prediction reliability.

## Line charts below the pies

Two separate responsive, SVG-based line charts sit directly below their
matching pie-chart panels.

- **Total · overall competitiveness trend:** cumulative **Accurate %** (green)
  against **Not Accurate %** (orange) after each *dated, independently verified*
  FDA action. The exact first frozen prediction per application cycle is
  used, so repeated revisions and post-decision forecasts cannot inflate the
  historical hit rate. Multiple FDA decisions on the same calendar date form
  a single dated checkpoint. The final point must equal the accuracy pie's
  fraction. Both percentages use the same resolved-case denominator; pending
  decisions are excluded and listed separately above.
- **Latest · outlook trend:** **Approval %** (green) against **CRL %** (orange)
  over independently validated and chronologically saved versions of the
  *same FDA application cycle* as the latest completed prediction. Distinct
  NCTs or company tickers are not silently pooled; uncalibrated, incomplete,
  non-complementary or post-action versions are excluded. The trend measures
  movement in predicted outcomes, **not** a trend in FDA decision accuracy
  for one trial. Delays are separate from binary approval-versus-CRL outcomes.

At least **two distinct dated observations** are required to draw each line.
When none or only one exists, display the axes, legend and an explicit
insufficient-history explanation. No synthetic baseline, fabricated 50/50
probability, or interpolated historical result is supplied.

These are presentation-only computations over the same existing read-only
audit registry. A completed frontend installation is not evidence that the
clinical assessment workers or prediction calibration have finished.
