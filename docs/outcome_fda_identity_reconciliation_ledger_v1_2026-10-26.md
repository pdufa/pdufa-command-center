# OUTCOME FDA identity reconciliation ledger v1 — 2026-10-26

This is a **versioned research ledger**, NOT a modification of the immutable FDA source export or an approved-outcome cohort. Denominator = **17 priority published-letter records**, NOT 17 unique applications. All records remain **model-ineligible** until review cycles and the complete application denominator are independently adjudicated.

## Status definitions
- **FDA identity documented**: a published identifier is supported by an FDA source and/or official application cross-reference. This does NOT certify the entire regulatory cycle.
- **Open**: application identity or letter scope still requires evidence.
- **Repository note**: a source-backed case note committed to this repository. An uncommitted finding is explicitly identified.

| # | Published sponsor | Identifier | Identity state | Evidence note / remaining issue |
|---:|---|---|---|---|
| 1 | Ultragenyx | BL 125845 | Documented | `outcome_fda_bl125845_primary_source_reconciliation_2026-10-26.md` |
| 2 | Replimune (letter 1) | BL 125827 | Documented | `outcome_fda_bl125827_primary_source_reconciliation_2026-10-26.md`; distinct letter, same application |
| 3 | Rocket | BL 125806 | Documented | `outcome_fda_bl125806_primary_source_reconciliation_2026-10-26.md` |
| 4 | DBV Technologies | BL 125713 | **Open** | Original CRL URL located: https://download.open.fda.gov/crl/CRL_BLA125713_20200803.pdf ; direct document verification still pending |
| 5 | Chiesi | Unavailable | **Open** | FDA letter marked Under Review for Release; no safe application ID |
| 6 | StemCyte | BL 125764 | Documented; **note committed** | `outcome_fda_bl125764_stemcyte_primary_source_2026-10-26.md`; FDA approval: https://www.fda.gov/media/183774/download ; FDA review: https://www.fda.gov/media/184484/download ; reconcile conflicting dates |
| 7 | Capricor | BL 125842 | Documented; **note committed** | `outcome_fda_bl125842_capricor_primary_source_2026-10-26.md`; FDA CRL: https://download.open.fda.gov/crl/CRL_BLA125842_20250709.pdf ; regulatory history: https://www.fda.gov/media/193912/download |
| 8 | Replimune (letter 2) | BL 125827 | Documented | Same case note as #2; retain second source record |
| 9 | Pierre Fabre | BL 125745 | Documented | `outcome_fda_bl125745_atara_pierre_fabre_reconciliation_2026-10-26.md`; related to #13 |
| 10 | Abeona | BL 125807 | Documented | `outcome_fda_bl125807_abeona_primary_source_2026-10-26.md` |
| 11 | Mesoblast | BL 125706 | Documented | `outcome_fda_bl125706_mesoblast_primary_source_2026-10-26.md` |
| 12 | CellTrans | BL 125734 | Documented | `outcome_fda_bl125734_celltrans_primary_source_2026-10-26.md` |
| 13 | Atara | BL 125745 | Documented | Same case note as #9; retain distinct letter |
| 14 | Green Cross | BL 125743 | Documented | `outcome_fda_bl125743_green_cross_primary_source_2026-10-26.md` |
| 15 | REGENXBIO | BL 125840 | Documented published ID; **registry crosswalk not verified** | `outcome_fda_bl125840_regenxbio_primary_letter_2026-10-26.md` |
| 16 | Samsung Bioepis | BLA 761373 / 761425 | Documented | `outcome_fda_samsung_bioepis_dual_bla_scope_2026-10-26.md`; two Original 2 submission targets, not two source records |
| 17 | Genentech | NDA 214410 / 210854 | Documented | `outcome_fda_genentech_xofluza_multi_submission_scope_2026-10-26.md`; three CR-targeted submissions across two NDAs |

## Progress denominators

- FDA published identity documented or cross-referenced: **15/17 source records** (includes #15 published-ID-only; does not imply registry crosswalk).
- Still open: **2/17 source records** (#4, #5).
- Documented cases with repository notes: **15/17**; all documented cases have committed notes.
- Independently verified complete review cycles: **0/17**.
- Model eligible: **0/17**.
- Verified complete application denominator: **false**.
- Prediction probability: **null**.

**Critical distinction:** 15/17 is identity triage progress, **not 88% completion of the OUTCOME prediction system**. No record here is authorized for training, backtesting, or trading.

## v1 revision note
Updated after StemCyte, Capricor, Samsung Bioepis, and Genentech reports were committed. Direct retrieval of DBV FDA PDF remains blocked (web reader inaccessible; container DNS unavailable). Chiesi source remains unreleased. **No inferred progress on either open identity record.**
