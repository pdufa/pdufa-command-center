# Mesoblast RYONCIL BLA 125706 — FDA regulatory-cycle evidence pass 1 (2026-10-26)

**Status:** three FDA action endpoints documented; review-cycle completeness and model eligibility NOT certified.

## FDA original evidence

- FDA clinical review: https://www.fda.gov/media/184952/download — **BLA 125706/0**; explicitly describes the first CRL September 30, 2020, January 31, 2023 resubmission, August 1, 2023 CRL, July 8, 2024 Class 2 resubmission, January 7, 2025 PDUFA goal, and December 18, 2024 review completion. Its regulatory-history table also documents earlier 2019 rolling submissions and an older withdrawn **BLA 125334**; that withdrawn application is NOT the same denominator member.
- FDA second CRL: https://download.open.fda.gov/crl/CRL_BLA125706_20230801.pdf — **BL 125706/0**, action August 1, 2023, explicitly refers to the September 30, 2020 CRL.
- FDA SBRA: https://www.fda.gov/media/185192/download — receipt January 31, 2020; resubmissions January 31, 2023 and July 8, 2024; PDUFA due January 7, 2025; approval recommendation December 18, 2024. **Data quality alert:** this SBRA search text prints **BLA STN 127506/0**, conflicting with FDA clinical review, CRL, product registry, and approval listing (**125706/0**). Preserve and flag the discrepancy, do not silently correct source text.
- FDA approval registry: https://www.fda.gov/vaccines-blood-biologics/development-approval-process-cber/2024-biological-license-application-approvals — RYONCIL, **125706/0**, approved December 18, 2024.

## Evidence-supported events (one application; multiple FDA actions)

| Date | Event | Primary support |
|---|---|---|
| 2020-01-31 | BLA original receipt | FDA clinical review + SBRA |
| 2020-09-30 | CRL #1 | FDA clinical review; original CRL referenced by 2023 letter |
| 2023-01-31 | Resubmission #1 | FDA clinical review + SBRA |
| 2023-08-01 | CRL #2 | FDA original CRL + clinical review |
| 2024-07-08 | Resubmission #2, Class 2 | FDA clinical review + SBRA |
| 2025-01-07 | PDUFA goal (not action) | FDA clinical review + SBRA |
| 2024-12-18 | Approval | FDA approval registry + clinical review |

## Outcome safeguards

- **Three action endpoints documented**: two CRLs, one approval; do not treat them as three independent applications.
- **Source anomaly:** FDA SBRA appears to print `127506/0`; authoritative cross-check against actual PDF should confirm whether typo is in source or text extraction before any normalization.
- The historical review-cycle boundaries and unbiased full denominator have NOT been independently signed off. CRL-only source sampling would create selection bias.
- `review_cycle_verified=false`; `complete_application_denominator_verified=false`; `model_eligible=false`; `prediction_probability=null`.
