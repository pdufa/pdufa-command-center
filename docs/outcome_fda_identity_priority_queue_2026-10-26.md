# OUTCOME FDA identity reconciliation — priority 17 (2026-10-26)

**Status:** SOURCE-BACKED IDENTITY TRIAGE; NOT FDA ACTION ADJUDICATION. This is a work queue, not an outcome cohort.

Source: GitHub Actions run 40227766457, artifact 12611921051; 124 identity-review records out of 458 published letter records. The source artifact was retrieved and its 17 highest-priority cases extracted to `outcome_fda_identity_priority_17.json` (conversation attachment). Original source record SHA-256 digests and published letter dates are preserved in that attachment. Do not infer that the remaining 107 approved-registry nonmatches represent FDA rejections.

## Identity review priorities

**15 APPLICATION_ID_UNRESOLVED letter records** (14 published BL identifiers; one unreleased letter without an application ID):

| Published identifier | Sponsor as published | Notes |
|---|---|---|
| BL 125845 | Ultragenyx Pharmaceutical Inc. | Preserve BL as published; do not silently convert to BLA |
| BL 125827 | Replimune, Inc. | First source record |
| BL 125806 | Rocket Pharmaceuticals, Inc. | |
| BL 125713 | DBV Technologies S.A. | |
| Unavailable | Chiesi Farmaceutici S.p.A | File marked Under Review for Release; no PDF-derived ID |
| BL 125764 | StemCyte, Inc. | |
| BL 125842 | Capricor, Inc. | |
| BL 125827 | Replimune, Inc. | Second source record; retain separately |
| BL 125745 | Pierre Fabre Pharmaceuticals Inc. | |
| BL 125807 | Abeona Therapeutics, Inc. | |
| BL 125706 | Mesoblast, Inc. | |
| BL 125734 | CellTrans Inc. | |
| BL 125745 | Atara Biotherapeutics, Inc. | Separate sponsor record; do not conflate with Pierre Fabre |
| BL 125743 | Green Cross Corporation | |
| BL 125840 | REGENXBIO, Inc. | |

**2 MULTIPLE_OR_AMBIGUOUS_APPLICATION_LINKS letter records:**

- Samsung Bioepis Co., Ltd.: `BLA 761373/Original 2`, `BLA 761425/Original 2`, `BLA 761373`, `BLA 761425`. Identify which application and submission the letter action actually covers, without assuming one letter = one application outcome.
- Genentech, Incorporated: `NDA 214410/Original 2`, `NDA 210854/S-05`, `NDA 210854/S-09`. Distinguish original applications from supplements and identify each regulatory action before assigning a review-cycle label.

## Required evidence to resolve each case

1. Locate FDA primary-source action letter and verify its exact application/submission identifiers, date, and scope.
2. Establish an official identity cross-reference, including legacy BL/STN to modern registry identifiers where one exists.
3. For multi-application letters, preserve application/submission multiplicity and separate review cycles only when supported by source evidence.
4. Preserve letter provenance and distinguish corrected-letter publication dates from original FDA action dates.
5. Reconcile against a complete application denominator before constructing outcome labels or approval probabilities.

**Safety invariant:** 17 priority cases remain unresolved in this queue. `independently_verified_review_cycles = 0`; `model_eligible_records = 0`; `complete_application_denominator_verified = false`; `prediction_probability = null`. This document does not change those values.
