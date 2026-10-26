# OUTCOME FDA primary-source reconciliation: BL 125845 (2026-10-26)

**Evidence status: OFFICIAL FDA LETTER CHAIN FOUND; NOT AUTOMATIC COHORT CLEARANCE.**

## Primary sources

1. FDA July 7, 2025 complete response letter: https://download.open.fda.gov/crl/CRL_BLA125845_20250707.pdf . The document identifies **Our STN: BL 125845/0**, Ultragenyx Pharmaceutical Inc., and rebisufligene etisparvovec. It states that the BLA could not receive final approval at that review.
2. FDA September 17, 2026 approval letter: https://www.fda.gov/media/194921/download . The document identifies **Our STN: BL 125845/0**, Ultragenyx Pharmaceutical Inc., rebisufligene etisparvovec-hopf (FAYUVI). It expressly states that the March 20, 2026 amendment was a complete response to the **July 7, 2025 action letter**, and approves the application effective September 17, 2026. Its internal page headers also use **BLA 125845/0**.

## Source-supported reconciliation

- Original legacy identity: `BL 125845/0`; retain verbatim in the source record.
- FDA approval-letter internal BLA identity: `BLA 125845/0`; this is **explicit FDA-document evidence**, not a silent algorithmic conversion.
- Linked application and sponsor: Ultragenyx, rebisufligene etisparvovec(-hopf).
- Explicitly linked FDA action sequence: **2025-07-07 complete response** → **2026-03-20 response amendment** → **2026-09-17 approval**.
- Source-backed conclusion: the legacy BL identity has an official FDA-document cross-reference, and these letters concern a linked application history.
- **Do not treat this as two independent application outcomes**; review-cycle boundaries and the full submission history still require adjudication.

## Remaining requirements

Verify full FDA action history, contemporaneous submission data and feature availability, event identity and review-cycle boundaries, and the complete unbiased application denominator. No probability or training eligibility follows from this identity cross-reference.

**Model safeguards:** `model_eligible = false`; `review_cycle_verified = false`; `complete_application_denominator_verified = false`; `prediction_probability = null`.

This note supersedes only the *unresolved identity-cross-reference* aspect of the BL 125845 queue item. It does **not** imply that the other 16 priority cases are resolved or that the original 124-case audit summary has been recomputed.
