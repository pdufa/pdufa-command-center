# Point-in-time FDA outcome validation

This evaluator is research infrastructure. It does not authenticate sources,
train a validated model, create missing historical forecasts, or establish
independent predictive accuracy.

## Binary target and nonbinary actions

The target is approval versus a documented complete response at the specified
application/review-cycle decision. `OUTCOME_TAXONOMY` in `hop_outcome_cohort.py`
defines only `APPROVED` (1) and `COMPLETE_RESPONSE` (0) as binary labels.
`POSTPONED`, `REVISED_PDUFA`, `WITHDRAWN`, `REFUSE_TO_FILE`,
`OTHER_NONAPPROVAL` and `UNRESOLVED` remain excluded from that binary model.
Unknown categories are excluded too. A delay, withdrawal, pre-review refusal or
generic legacy nonapproval is never silently turned into a rejection label.
Target revisions and unresolved events require separate dated histories and a
prespecified censoring/evaluation policy before defining another estimand.

## Three clocks, with no imputation

`decision_date` is the FDA action date. `public_features_as_of` is the frozen
predecision feature-snapshot cutoff. **`outcome_public_as_of` is when the action
label became publicly available**, based on reviewed source evidence. It is not
the document's printed date or this researcher's later retrieval time.

The new publication field defaults to `None`. Older records without it are
ineligible, not silently migrated to their decision date. A source reviewer must
establish the original public-availability date and exact action identity. The
CSV intake's feature and outcome evidence clocks likewise remain distinct;
schema-valid metadata, URLs and caller verification flags do not prove truth.
Raw CRL observations and the approved-product registry remain quarantined.

At every forecast, both the training features and training outcome-publication
dates must precede its feature cutoff. Dates have day precision, so same-day
label publication is conservatively excluded from training. The training window
also remains bounded by the fold's left boundary. A past action with a later
published label cannot leak into an earlier model fit.

`evaluation_as_of` controls when held-out ground truth can be used for metrics;
it defaults to the final fold boundary. It must cover all folds. Set it explicitly
to the documented later dataset snapshot when evaluating decisions whose source
labels became public after their decision window. This later audit date never
makes a label available to an earlier training prediction.

## Masked scoring boundary and application dependence

The scorer now receives a frozen `PredictionCase` containing only application ID,
review cycle and predecision snapshot date, plus the constant `outcome=WITHHELD`.
The actual decision date, outcome-publication date and postdecision cohort
metadata are absent. Evaluation reveals the true label only after scoring.
Callbacks must not look up labels through closures, external files or APIs;
the function cannot independently enforce a blinded research organization.

Duplicate application/cycle rows still reject the backtest input. Repeated
applications are counted once per training fit and once across the held-out folds, with
training/test application overlap excluded. The latest eligible training cycle
is selected **after** the forecast cutoff filter, so a future cycle cannot hide
an earlier known cycle. This does not establish independence between related
programs or populations; cohort construction and untouched partition proof
remain required upstream. The earliest eligible held-out cycle is selected
without consulting its prediction or label. It remains selected even if the
model abstains; a later correlated cycle cannot replace it to improve coverage.

The cohort audit reconciles all action claims before counting a cycle. Opposing
labels or conflicting action dates quarantine the entire cycle in either input
order. Identical duplicates cannot increase its count. No first-row label wins.

## Interpretation and tests

Missing, impossible or not-yet-public labels produce explicit exclusions. Missing
training support causes abstention. Brier loss stays unavailable when no cases
are scored. These outputs must not be presented as independently verified FDA
accuracy; no real source records, decisions, cohort signoffs or probabilities
are introduced by this engineering change.

Existing synthetic fixtures now explicitly declare their publication dates for
their software-contract scenarios. These declarations are not real FDA evidence.
Regressions cover late labels, same-day cutoffs, delayed evaluation, outcome/date
masking, invalid dates/support, repeated cycles, conflicts and nonbinary actions.

```sh
cd new-platform/backend
python -m pytest -q tests/test_hop_point_in_time_labels.py tests/test_hop_backtest.py tests/test_hop_outcome_cohort.py
```

## Verified development snapshot — 2026-10-28

The complete backend suite passed **618 tests**, with five existing
dependency/Pandas warnings and no failures. A separate code review found no
material defects in these changes; it was a software review, not independent
adjudication of FDA source records. This increment starts at main `7a88764c`
and changes only the evaluator, metadata gate, tests, their PR safety check and
this documentation.

The actual repository readiness snapshot remains `RESEARCH_ONLY`: one staged
record, **zero model-eligible historical cycles**, no connected training data,
no validated model and no available probability. There are **zero independently
tested real cases**. Accuracy, balanced accuracy, sensitivity/specificity, Brier
score, log loss, AUROC and calibration are therefore **not measured**; no real
prediction-coverage estimate is available. Synthetic test losses do not change
these counts.

The separate PEAK research increment in draft PR #507 retains **0/40 independently
certified assessments**, 0/20 certified depths and unavailable probabilities.
Its supporting source contexts are not eligible training or evaluation labels.

Next, reviewers must establish exact application/cycle identities, original
outcome-publication dates, complete approval/nonapproval cohort ascertainment,
frozen predecision features and an untouched final partition. Only then can
reproducible baselines and empirical calibration be evaluated. Current runtime
policy does not permit direct FDA/ClinicalTrials.gov/Render source retrieval,
the internal API key is not bound, and external staging SQL access is blocked
by its existing allowlist. Reviewed offline evidence or authorized scoped access
is needed for those checks. No deployment, live schedule, spreadsheet write,
list membership, FS/FA association or trading behavior is changed.
