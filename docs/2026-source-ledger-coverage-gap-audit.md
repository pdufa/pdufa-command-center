# 2026 pre-decision source-ledger coverage audit — 2026-11-19

## Measured repository coverage

Read the current development-branch files `data/backtest/2026-provisional-source-research.csv` and `data/backtest/2026-clinical-evidence-backlog.csv`.

| Metric | Count |
|---|---:|
| Provisional research source rows | 98 |
| Candidate events represented in source ledger | 30 |
| Candidate events tracked in clinical evidence backlog | 89 |
| Tracked candidates not represented in provisional source ledger | **59** |
| Event-to-NCT links found in source-ledger text | 35 |
| Distinct NCT IDs found in source-ledger text | 35 |

**Important qualification:** 59 means *no record in this particular provisional source ledger*, **not** that these candidates have no public scientific data. The source ledger's research leads are provisional and not necessarily cutoff-authenticated.

The separate claim of **296 total PDUFA events for 2026 is not yet independently verified** and should not be used as the denominator of validated blind accuracy.

## Immediate execution order

1. Enumerate the 59 tracked candidates lacking source-ledger entries and establish exact application, indication, review-cycle and pivotal-study identities; do not invent NCT IDs.
2. Retrieve original pre-cutoff clinical publications, registry history and sponsor disclosures. The current ClinicalTrials.gov API response is a **current snapshot**, not a historical cutoff snapshot.
3. Confirm dated source versions and trial-to-application linkage; quarantine all post-cutoff sources from prediction inputs.
4. Produce substantive scientific assessments at Levels 1–6 and record abstentions where evidence is insufficient.
5. Obtain outcome-unexposed independent reviewers and immutable prediction locks **before** exposing FDA decisions.
6. Reconcile outcomes and calculate accuracy on an explicitly eligible denominator, reporting abstention and coverage separately.

## Collector correction

Commit `486ed58` corrected the ClinicalTrials.gov collector to use `lastUpdatePostDateStruct.date` for `registry_last_update_posted` instead of `studyFirstPostDateStruct.date`. This avoids incorrectly representing the first posted date as the most recent update.

**Status:** This is a coverage audit and code correction, not completed trial retrieval, a prediction, or a blind score. No production deployment.
