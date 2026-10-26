# OUTCOME FDA review-cycle adjudication — Abeona BL 125807, pass 1 (2026-10-26)

**Purpose:** move beyond identity crosswalk to a strictly bounded, source-supported regulatory event chain. This is NOT a certified complete historical cycle, cohort, or training label.

## FDA primary documents
- FDA April 16, 2024 Complete Response Letter: https://download.open.fda.gov/crl/CRL_BLA125807_20240416.pdf — BL 125807/0, Abeona Therapeutics, prademagene zamikeracel. FDA says partial responses do not start new review cycles.
- FDA April 28, 2025 approval letter: https://www.fda.gov/media/186513/download — BL 125807/0, Abeona Therapeutics, ZEVASKYN; original BLA received September 25, 2023.
- Abeona October 29, 2024 SEC-filed announcement: https://www.sec.gov/Archives/edgar/data/318306/000149315224042775/ex99-1.htm — sponsor reports BLA resubmission after the April 2024 CRL. Sponsor statement is not independent FDA confirmation of a completed resubmission acceptance.

## Event ledger (not an inferred sequence of complete cycles)

| Event date | Event | Source tier | Evidence scope |
|---|---|---|---|
| 2023-09-25 | Original BLA receipt | FDA approval letter | FDA-stated receipt date |
| 2024-04-16 | Complete Response Letter | FDA original CRL | Confirmed FDA action; original review did not approve |
| 2024-10-29 | Sponsor announces resubmission | SEC-filed company statement | Claimed resubmission; FDA receipt/acceptance not independently verified |
| 2025-04-28 | FDA approval | FDA approval letter | Confirmed approval of ZEVASKYN |

## Provisional action-level outcomes

- FDA action at **2024-04-16**: `complete_response` (source verified).
- FDA action at **2025-04-28**: `approval` (source verified).
- **No** claim that the above is the complete set of FDA cycles or that the resubmission was accepted on a particular date.
- The FDA action labels above must **not** be used as independent trial observations; they share an application, and the source collection may omit actions.

## Outstanding adjudication checks

1. Obtain FDA primary evidence of October 2024 resubmission **receipt/acceptance**, plus any intervening amendments and clock changes.
2. Determine action letter types, review-cycle boundaries, and whether any corrected letters supersede the published dates.
3. Confirm original and resubmitted application cohort membership and full denominator, including approvals and nonapprovals not captured in the CRL-publication subset.
4. Lock feature as-of timestamps before backtesting to avoid future information leakage.

**Gate:** `event_actions_verified=2` (not `review_cycles_verified`); `review_cycles_verified=0`; `complete_application_denominator_verified=false`; `model_eligible=false`; `prediction_probability=null`.
