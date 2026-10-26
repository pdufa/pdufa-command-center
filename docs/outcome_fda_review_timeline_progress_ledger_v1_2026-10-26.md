# OUTCOME FDA historical-data implementation ledger — 2026-10-26

This versioned research ledger separates observed events, reconstructed timelines, and **certified model-eligible outcomes**. Counts have distinct denominators; do not combine them into a single deceptive installation percentage.

## Counted progress (definitions and denominators)

| Measure | Completed | Denominator | Meaning |
|---|---:|---:|---|
| Priority source-record identity documented | 15 | 17 | FDA source-letter records; two unresolved: DBV and Chiesi |
| Selected research final-action endpoints entered | 19 | 19 selected | Selected sample; not a complete application universe |
| Distinct BLA identifiers in research action sample | 10 | 10 selected | Unique identifiers, not independently certified application cohort |
| Selected final-action endpoints with source-linked structured submission-to-decision timeline | **4** | **19 selected endpoints** | 2 Abeona + 2 Mesoblast; selected-sample progress, **not** full-review-cycle completion rate |
| Distinct sampled applications with structured timeline | **2** | **10 sampled applications** | Abeona BLA 125807; Mesoblast BLA 125706 |
| Independently certified complete priority review cycles | **0** | **17 priority source records** | Priorities count source records, not distinct cycles |
| Model-eligible priority source records | **0** | **17 priority source records** | Remain blocked until cohort, boundary and pre-action audits are complete |

## Four source-supported structured timelines

| Application | Receipt | Final action | Result |
|---|---|---|---|
| 125807 Abeona | 2023-09-25 | 2024-04-16 | CRL |
| 125807 Abeona | 2024-10-28 | 2025-04-28 | Approval |
| 125706 Mesoblast | 2023-01-31 | 2023-08-01 | CRL |
| 125706 Mesoblast | 2024-07-08 | 2024-12-18 | Approval |

Primary FDA SBRA/letters: Abeona https://www.fda.gov/media/186796/download and https://www.fda.gov/media/186513/download and https://download.open.fda.gov/crl/CRL_BLA125807_20240416.pdf ; Mesoblast https://www.fda.gov/media/185192/download and https://download.open.fda.gov/crl/CRL_BLA125706_20230801.pdf and https://www.fda.gov/media/184605/download .

## Open evidence issues

1. **Mesoblast SBRA identifier conflict:** signed approval letter and SBRA regulatory-history table say `125706`, but **the cover page of the same SBRA visibly says `127506`**. Canonicalize to `125706` for this record with discrepancy explicitly preserved; never count a new `127506` application.
2. The original September 30, 2020 Mesoblast CRL direct PDF was not retrievable in the latest pass. Its event remains in research action fixtures, but its independently checked structured review timeline remains OPEN.
3. Missing/undemonstrated FDA document publication timestamps, source snapshot hashes, comprehensive amendments, clock extensions and application denominator prohibit historical prediction feature as-of clearance.
4. DBV and Chiesi priority identities remain unresolved. StemCyte and Ultragenyx FDA date conflicts remain unresolved.
5. This ledger is a **versioned research status**, not a live dashboard or deployment statement; updating tests is not adjudication of cohorts.

## Verified automation

GitHub Actions `OUTCOME historical safety tests` run **40366406996**, head commit `dff936c3d0305315d3ba6624fe9a573e1314d241`, concluded **success**:
- historical/backtest safety suite: **74 passed**;
- FDA action/research export/review timeline modules: **36 passed**;
- published audit still `model_eligible_records=0`, `prediction_probability=null`, `complete_application_denominator_verified=false`.

Code: `outcome_fda_review_timeline_evidence.py`; tests: `test_outcome_fda_review_timeline_evidence.py`.

**Training status:** research-only, `model_eligible=false`, `prediction_probability=null`. No probability, performance metric or numerical model-success estimate is warranted.
