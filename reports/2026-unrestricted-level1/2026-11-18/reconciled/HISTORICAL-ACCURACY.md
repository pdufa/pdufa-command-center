# Historical Level 1 accuracy

| Measure | Count |
| --- | ---: |
| Verified historical decisions | 69 |
| Outcome-aware retrospective assessments | 69 |
| Correct eligible predecision predictions | 0 |
| Incorrect eligible predecision predictions | 0 |
| Eligible predecision prediction and outcome pairs | 0 |
| Blind accuracy | HISTORICAL BLIND ACCURACY NOT MEASURABLE |
| Calibration | Unavailable |

A comparison requires an immutable exact-cycle Level 1 prediction with contemporaneous evidence and a subsequently verified FDA decision. The freeze must predate both the earliest observed action and public disclosure. The separately documented HARMONi model belongs to another research series.

Two verified future records for deramiocel and relacorilant retain their original model version, freeze timestamp, cutoff and evidence receipts. Both freezes are INDETERMINATE. [Assessment JSON](assessments.json) · [Scoring and archive counters](completion-manifest.json)


## Calibration method for future data

Before observing outcomes, freeze one eligible directional probability per exact application cycle and preserve all later versions. Record the model version, public evidence cutoff and earliest decision and disclosure times. Predefine whether approvals with restrictions count as approvals and handle CRLs, withdrawals, changed goals and abstentions explicitly. Report frozen forecast coverage and abstention rates separately.

Once there are eligible directional probabilities and binary outcomes, score held-out forecasts using the Brier score and log loss. Compare against an approval-rate baseline estimated from earlier eligible cycles. Use a chronological holdout and report uncertainty with reliability bins whose counts are shown. Avoid fitting or reporting calibration for unsupported bins. Keep subjective qualitative confidence separate. The present dataset has zero eligible historical pairs and zero validated numerical confidence estimates, so no calibration can be fitted or reported.
