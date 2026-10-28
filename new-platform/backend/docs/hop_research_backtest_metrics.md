# Historical FDA OUTCOME — auditable research metric contracts

This increment adds meaningful mathematical evaluation measures to the
existing chronological, application-disjoint `hop_backtest.py` without
changing its FDA source/adjudication eligibility rules.

The metric engine, `app/hop_forecast_metrics.py`, computes on the
**covered** (not abstained) test cases in each walk-forward fold:

- Brier score and log loss (proper probability scoring rules).
- Threshold-0.5 accuracy and balanced accuracy.
- Tie-correct AUROC; undefined when one outcome class is absent.
- Five-bin predicted-versus-observed calibration summary and
  expected calibration error (ECE).
- 95% Wilson interval for covered-case accuracy, a descriptive
  sampling interval that does **not** correct selection bias.
- Prediction coverage, eligible count, abstentions and excluded cases.
- Same-covered-cases baseline Brier score, using a simple
  **historical training-approval proportion** computed on dates
  preceding each test feature snapshot.
- Brier skill score relative to that baseline, only when its
  denominator is positive and meaningful.

Scores are only **research mathematics on caller-supplied data**.
Neither a synthetic test outcome nor a self-declared
`COMPLETE_APPLICATION_COHORT` makes a real case independently certified.
All fold outputs retain:

`independent_fda_validation_complete = false`

and each metrics object contains:

`modelHistoricallyValidated = false` and status
`MATH_METRICS_ONLY_NOT_INDEPENDENT_FDA_VALIDATION`.

The metrics contract refuses NaN, infinite or boolean probabilities,
nonbinary labels, invalid coverages and mismatched baseline lengths.
No future test label is passed to the scoring callback.
The training baseline uses only previously published training labels;
it must not use any held-out outcomes, post-decision evidence or later
historical annotations.

**Real model eligibility remains 0 and historical validated cases remain 0.**
Consequently **no empirical FDA PASS/FAIL performance score or calibrated
probability is presently available**. Metrics computed by synthetic unit
tests demonstrate software correctness only; they are not FDA trial
results or investment/trading guidance.

Future work requires an independent, complete FDA NDA/BLA application
cohort, original cycle adjudication, frozen dated features, a
pre-registered model/threshold, a program-disjoint holdout, uncertainty
under source revision, and performance comparisons to multiple baselines.
Only after independent validation should MAIN report actual predictive
accuracy, calibration, confidence intervals or actionable decision
probabilities.

No new scans, sheet/database writes, existing FS/FA membership changes,
or broker trades are enabled.
