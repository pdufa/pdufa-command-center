# StemCyte REGENECYTE BLA 125764 — FDA review-cycle pass 1 (2026-10-26)

Status: FDA regulatory action chronology documented, with unresolved internal resubmission date discrepancy. No model eligibility.

## FDA original source

FDA November 20, 2024 Summary Basis for Regulatory Action: https://www.fda.gov/media/184484/download

- PDF page 1 header: BLA 125764/0, StemCyte Inc.; original receipt **January 7, 2022**; resubmission receipt **November 29, 2023**; non-PDUFA action due **May 10, 2024**; recommendation for approval.
- PDF page 4, Regulatory History: FDA issued a **January 20, 2023 Complete Response Letter** for the original submission, citing CMC deficiencies in donor screening/testing, viability and flow-cytometry assays, process validation and stability. The same narrative says StemCyte responded with a resubmission **November 9, 2023**.
- FDA approval letter: https://www.fda.gov/media/183774/download — BL 125764/0, November 20, 2024.
- FDA Purple Book: https://purplebooksearch.fda.gov/index.cfm?blaNo=125764&event=productdetails — original approval listed November 21, 2024.

## Source-attributed events

| Date | Event | Evidence |
|---|---|---|
| 2022-01-07 | Original BLA received | FDA SBRA |
| 2023-01-20 | FDA CRL, CMC concerns | FDA SBRA regulatory history |
| 2023-11-09 | Resubmission date in FDA narrative | FDA SBRA narrative; conflicts with header |
| 2023-11-29 | Resubmission receipt date in FDA header | FDA SBRA header; conflicts with narrative |
| 2024-05-10 | Non-PDUFA action due date, NOT outcome | FDA SBRA header |
| 2024-11-20 | Approval letter / SBRA date | FDA original approval letter and SBRA |
| 2024-11-21 | Purple Book original approval date | FDA Purple Book; discrepancy preserved |

## Open anomalies and gating

- `FDA_INTERNAL_RESUBMISSION_DATE_CONFLICT`: November 9 vs November 29, 2023. Do NOT silently choose either; obtain independent FDA receipt evidence.
- `FDA_APPROVAL_DATE_SOURCE_CONFLICT`: approval letter November 20 vs Purple Book November 21, 2024. Preserve source-specific dates and investigate.
- `NON_PDUFA_GOAL_VS_APPROVAL_DATE`: May 10, 2024 non-PDUFA due date and November 20 approval; do not infer extension or delay cause without documentary evidence.
- Original January 2023 CRL not directly reviewed here; SBRA regulatory-history description is FDA primary evidence of the action.
- One BLA with CRL and approval, not two independent application samples. Full amendment/clock chronology, source-as-of controls and complete application denominator not verified.

`fda_action_endpoints_documented=2`; `complete_review_cycles_adjudicated=false`; `model_eligible=false`; `prediction_probability=null`. Immutable source export unchanged.
