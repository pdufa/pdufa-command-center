# Daily SCIENCE / OUTCOME / MAIN progress reporting

Run `python -m unittest tests.test_audited_daily_progress` and
`python scripts/audited_daily_progress.py yesterday.json today.json`.

Each daily JSON snapshot must contain `as_of` and exactly three keys under
`systems`: `SCIENCE`, `OUTCOME`, `MAIN`. Each system is either `null`
(not verified) or an object with integer `completed`, integer `total`,
HTTPS `evidence_uri`, and a stable `scope` naming the audited population.

Example **schema only, not measured progress**:
```json
{"as_of":"2026-10-26","systems":{"SCIENCE":null,"OUTCOME":null,"MAIN":null}}
```

Report the measured percentage only for a defensible, complete denominator.
Daily percentage-point change is shown only when yesterday and today have
the **same scope and denominator**. Otherwise report BASELINE_ONLY and no
change. Do not silently treat missing observations as zero or rebase to
a different denominator. A change in audited scope requires a new baseline.

SCIENCE numerator: fully source-verified 40-investigation units for a
predeclared exact-trial cohort; denominator: 40 times the cohort size.
Existing P/J/G seven-category heuristics are **not** SCIENCE-40.

OUTCOME numerator: independently certified, point-in-time, model-eligible
FDA review cycles in a predeclared complete application cohort; denominator:
all review cycles in that cohort. Selected CRL or approval samples do not
qualify as a complete denominator. Historical research timeline coverage,
such as 17/20, is a **separate metric**, not OUTCOME completion or accuracy.

MAIN numerator: individually accepted production requirements from a frozen,
versioned acceptance inventory; denominator: all requirements in that inventory.
Do not equate 741 source-linked trials with 741 fully qualified trials.

Prediction accuracy is **never** derived from completion. Report it only
from independently held-out labeled decisions with the model version,
sample size, uncertainty, and metric (e.g. Brier score) shown.

The script is an auditable comparison utility. It is **not** a nightly
scheduler, an automatic source collector, a deployed dashboard widget, or
a certification that the three systems are complete. Those require separately
approved integration and independently sourced snapshots.
