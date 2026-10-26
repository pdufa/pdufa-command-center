# Replimune BLA 125827 — FDA first-resubmission date conflict adjudication (2026-10-26)

**Decision:** FDA source evidence supports **October 9, 2025** as the first resubmission, while the FDA SBRA header erroneously lists **April 10, 2026**, which is the second Complete Response Letter action date. Preserve the contradictory source field verbatim.

## Original primary-source triangulation

1. FDA August 6, 2026 SBRA: https://www.fda.gov/media/194230/download
   - Summary header: `First resubmission: April 10, 2026`.
   - Detailed regulatory-history table: `First Resubmission Date: October 9, 2025`, `Second CRL: April 10, 2026`, `Second Resubmission Date: June 2, 2026`.
   - These two entries are internally inconsistent.
2. FDA April 10, 2026 original CRL: https://download.open.fda.gov/crl/CRL_BLA125827_20260410.pdf
   - Explicitly identifies the **October 9, 2025** amendment as the complete response to the **July 21, 2025** action letter.
3. FDA July 21, 2025 original CRL: https://download.open.fda.gov/crl/CRL_BLA125827_20250721.pdf
   - Explicitly dated July 21, 2025 and identifies `BL 125827` and the Complete Response action.

## Adjudicated date fields

| Field | Value | Evidence |
|---|---|---|
| First CRL action date | 2025-07-21 | Original FDA CRL |
| First complete-response resubmission | **2025-10-09** | Original 2026 CRL + FDA SBRA detailed history |
| Second CRL action date | 2026-04-10 | Original FDA CRL + FDA SBRA detailed history |
| Second resubmission date | 2026-06-02 | FDA SBRA |
| FDA SBRA header conflicting 'first resubmission' | 2026-04-10 | Preserve as source anomaly, not canonical event |

**Anomaly:** `FDA_PRIMARY_SOURCE_INTERNAL_RESUBMISSION_DATE_CONFLICT`. This resolves the specific date discrepancy by original-action-letter corroboration; it does not prove a full review-clock history or eligibility for model training.

`first_resubmission_date_adjudicated=true`; `complete_review_cycles_adjudicated=false`; `complete_application_denominator_verified=false`; `model_eligible=false`; `prediction_probability=null`. Do not mutate immutable FDA source export.
