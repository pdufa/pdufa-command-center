# Dashboard integration draft for the 2026 six-level FDA backtest

The selected assessment family is the installed scientific Levels 1–6: trial identity, design, statistics and efficacy, safety, indication-specific relevance, and regulatory readiness. The installed scientific assessments can report evidence and readiness. They currently supply no validated level-specific FDA decision rule. Historical dashboard values therefore remain in research status pending a reconciled cohort, documented predecision evidence, and an eligible locked evaluation.

| Surface | Draft integration point | Data to display |
| --- | --- | --- |
| FOCUS | `new-platform/frontend/app/focus/page.tsx`, alongside the existing scientific readiness panel | Link to the PAST historical research status. Keep the live FOCUS roster and saved assessment evidence as their own view. |
| PAST | `new-platform/frontend/app/past/page.tsx`, above the existing historical intake table | Reconciled actions and explicit exclusions, with verified action date and original PDUFA goal date shown as separate fields. Key rows by verified FDA application, submission/review cycle, and action identity. Show unavailable evidence and pending reviews explicitly. |
| ASSESSMENTS | `new-platform/frontend/app/assessments/page.tsx`, in a dedicated historical evaluation panel | One row each for L01–L06, with assessment-family and prediction-protocol labels, eligible cohort size, answered count, abstained, correct, incorrect, coverage, accuracy, and Wilson interval. Display unavailable metrics until an eligible verified report exists. |

## Export contract

The score command validates the independently retained digest before opening the outcomes file, validates the assessment grid and outcome event IDs, and writes an aggregate JSON array. It can also write `--summary-csv` (six rows) and `--results-csv` (one row per event and level). The CSVs use UTF-8 with BOM for spreadsheet import. Detailed results contain outcomes and belong in the authorized post-lock reporting environment.

The aggregate has `level`, `events`, `predicted`, `abstained`, `correct`, `incorrect`, `coverage`, `accuracy`, `accuracy_ci95_wilson_low`, `accuracy_ci95_wilson_high`, the always-approve comparisons, six actual/predicted cross-tab counts, `protocol`, `rule_set`, and `lock_sha256`. Interpret accuracy and its interval over answered cases and coverage over eligible cases. Display null accuracy and intervals as unavailable. Report the actual reconciled cohort denominator and label 196 only as the requested target. Treat nonbinary actions as explicit ledger exclusions.

Before any future wiring, require a reconciled eligible FDA decision cohort and a report whose scientific assessment family, prediction protocol, and lock receipt match the independently verified run. Validate all six rows and check that counts balance. The branch's experimental gate baseline and prior outcome-aware examples are outside the installed scientific Levels 1–6 accuracy display. Preserve the existing historical charts and active dashboards while the cohort and forecasting rules are still under development.
