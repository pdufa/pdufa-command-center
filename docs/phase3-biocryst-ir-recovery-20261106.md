# Phase 3 IR recovery — second batch, BioCryst

Starts from latest main `891ece3325c13e99c73da378dc782620d1db73d2`, after PR #846 passed all checks, merged, and was verified on the production audit and 762-by-190 CSV.

One additional company searched (BioCryst), three trials enriched. One official IR release, two SEC 8-K filings and the SEC release exhibit reviewed; these represent two distinct historical issuer disclosures. APeX-J primary publication, original FDA label and FDA approval package cross-checked. Three exact-NCT/protocol/acronym registry identities verified live.

20 documentary assessment facts added. Two new primary successes (APeX-2 and APeX-J), one failure (OPuS-2), zero new nonbinary classifications. One FDA application link added: cumulative 14 links across six drug/indication programs. Zero PDUFA goal dates or numerical predictions added.

APeX-J success is specifically the 150 mg comparison in a separate Japanese trial; 110 mg success is not asserted. Avoralstat OPuS-2 remains failed and unlinked to the different drug berotralstat FDA approval. FDA adverse-reaction discontinuations are distinguished from extension retention.

| Question | Facts added | Remaining research |
|---|---:|---:|
| Q01 | 3 | 404 |
| Q02 | 0 | 747 |
| Q03 | 2 | 396 |
| Q04 | 1 | 757 |
| Q05 | 1 | 756 |
| Q06 | 1 | 755 |
| Q07 | 0 | 6 |
| Q08 | 0 | 11 |
| Q09 | 0 | 1 |
| Q10 | 0 | 1 |
| Q11 | 0 | 160 |
| Q12 | 1 | 1 |
| Q13 | 0 | 760 |
| Q14 | 0 | 760 |
| Q15 | 0 | 761 |
| Q16 | 0 | 758 |
| Q17 | 1 | 145 |
| Q18 | 0 | 684 |
| Q19 | 1 | 758 |
| Q20 | 0 | 761 |
| Q21 | 0 | 759 |
| Q22 | 1 | 492 |
| Q23 | 1 | 455 |
| Q24 | 1 | 485 |
| Q25 | 0 | 0 |
| Q26 | 2 | 758 |
| Q27 | 0 | 405 |
| Q28 | 0 | 759 |
| Q29 | 3 | 406 |
| Q30 | 1 | 747 |

Unscored slots: **14,648**, down seven from batch 1 and 27 from the original baseline. Cumulative endpoint classifications: **41 met / 7 failed / 3 nonbinary / 711 unadjudicated**. Four prediction-bearing trials and 61 existing prediction slots are preserved.

The company/NCT queue remains partial. No unreviewed trial or inaccessible source is classified as NOT_PUBLICLY_DISCLOSED. Remaining source blockers and exact URLs/checksums are saved in `phase3BiocrystSourceValidation20261106.json`. The issuer APeX-2 IR URL returned 503 to shell acquisition after a successful web-tool read; the same SEC Exhibit 99.1 was read and selected as stable evidence URL.

Validation: actual audit/CSV route regression, TypeScript and production build; full frontend suite and PR checks before merge. Production verification must follow merge. The first batch generator now preserves later companies’ queue reviews when resumed.
