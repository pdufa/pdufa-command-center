# Verified one-case FDA backtest pilot

The outcome team independently verified eligibility for PDUFA26-TIMING-035 and isolated its FDA review cycle from related actions. The evidence worker reviewed the [pinned HYPERION source projection](2026-hyperion-registry-projection.md) against the August 22, 2026 cutoff. The package documents 11 sourced criteria and 14 UNKNOWN dispositions.

A separate outcome-unexposed executor froze one scientific report and direction for each level. The [prereveal receipt](../data/backtest/receipts/2026-timing-035-prereveal.json) was committed and pushed at `04f9cc9d` before the outcome comparison. The reporting worker checked the receipt against the [canonical lock](../data/backtest/locks/2026-timing-035.lock.json), then matched the exact FDA application, review cycle and action date in quarantine.

| Level | Eligible | Answered | Correct | Incorrect | Abstained | Coverage | Accuracy and 95% interval |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| L01 | 1 | 0 | 0 | 0 | 1 | 0% | Unavailable |
| L02 | 1 | 0 | 0 | 0 | 1 | 0% | Unavailable |
| L03 | 1 | 0 | 0 | 0 | 1 | 0% | Unavailable |
| L04 | 1 | 0 | 0 | 0 | 1 | 0% | Unavailable |
| L05 | 1 | 0 | 0 | 0 | 1 | 0% | Unavailable |
| L06 | 1 | 0 | 0 | 0 | 1 | 0% | Unavailable |

The pilot verifies the research workflow with observed case evidence. No level answered the directional question, so there are no observations for the accuracy denominator or for confidence calibration. The 196-case universe remains unreconciled. Excel-ready summary and detail files reside in the restricted reporting workspace.
