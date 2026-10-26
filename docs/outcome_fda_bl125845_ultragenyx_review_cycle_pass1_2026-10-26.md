# Ultragenyx FAYUVI BLA 125845 — review-cycle evidence pass 1 (2026-10-26)

**Status:** FDA-source-supported original submission, CRL linkage, resubmission and approval. Complete cycle adjudication and model eligibility remain OPEN.

## Original FDA sources

- FDA approval letter (September 17, 2026): https://www.fda.gov/media/194921/download — **BL 125845/0**, Ultragenyx Pharmaceutical, FAYUVI (rebisufligene etisparvovec-hopf). Original BLA received **December 18, 2024**; March 20, 2026 amendment explicitly constituted complete response to **July 7, 2025 action letter**; approved September 17, 2026.
- FDA SBRA (September 17, 2026): https://www.fda.gov/media/195198/download — **BLA 125845/0**; original receipt **December 18, 2024**, resubmission **March 20, 2026**, PDUFA action due **September 19, 2026**.
- FDA clinical review: https://www.fda.gov/media/195731/download — **BLA 125845/0**, priority-review resubmission submitted **March 20, 2026**, PDUFA goal **September 18, 2026**, review completion **September 17, 2026**.
- Prior identity report: `docs/outcome_fda_bl125845_primary_source_reconciliation_2026-10-26.md` records the July 7, 2025 CRL.

## Event chronology

| Date | Event | Provenance |
|---|---|---|
| 2024-12-18 | Original BLA receipt | FDA approval + SBRA |
| 2025-07-07 | Earlier FDA action, identified as CRL in prior source note | FDA approval references action; original CRL should be inspected for full detail |
| 2026-03-20 | Complete-response resubmission | FDA approval + SBRA + clinical review |
| 2026-09-17 | Approval | FDA approval letter |
| 2026-09-18 | PDUFA goal **as printed in clinical review** | FDA clinical review |
| 2026-09-19 | PDUFA due date **as printed in SBRA** | FDA SBRA |

## Explicit conflict and limits

**FDA internal PDUFA discrepancy:** September 18 vs September 19, 2026. Store both as source-specific fields with anomaly `FDA_PRIMARY_SOURCE_PDUFA_DATE_CONFLICT`; do not pick a canonical goal without further evidence. Neither date is a regulatory action.

These are regulatory events for **one application**, not independent approval/rejection observations. The July 2025 original CRL's exact contents, full amendment and clock history, correction notices, pre-action feature timestamps and unbiased cohort denominator remain to be adjudicated.

`fda_resubmission_receipt_verified=true`; `fda_approval_verified=true`; `pdufa_goal_conflict_documented=true`; `complete_review_cycles_adjudicated=false`; `model_eligible=false`; `prediction_probability=null`. Immutable source audit unchanged.
