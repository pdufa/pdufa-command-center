# Company-by-company manufacturer recovery — 2026-11-06

Started main `2fc7d7c75c25a27cf2c1de05a6603cfb79daf7f3`; rebased onto latest main `6f717e2ff11a8f79a799296c7a3043d20e2196c7` after PR #850 added the ranked outstanding-data page. That page/API is preserved and checked against this recovered dataset. Live baseline reconciled: 762 trials, 190 columns, 13,124 unscored slots, 50 met / 8 failed / 5 nonbinary, 23 FDA-linked trials / 12 programs, 61 numerical slots in four trials.

## Coverage and result

The queue contains **137 companies**. This batch conducted partial manufacturer/IR source reviews for **8 companies / all 23 of their census trials**: Abivax, ADMA, Agenus, Alector, Alumis, Altimmune, Annexon and Aquestive. Each received an official manufacturer-page pass and exact-NCT registry check. Four user-provided discovery calendars were revisited before manufacturer searches; calendar probabilities and unverified outcomes were not imported. FDA Tracker enhanced content requires login; accessible manufacturer/FDA/registry alternatives were used.

Reviewed 14 issuer/science documents (three Abivax archived disclosures; ADMA's 2014 readout; four Agenus historical releases/updates; Alector's readout; Alumis readout and presentation; Altimmune initiation release; Annexon readout and exact-NCT PRO poster), with additional FDA/registry/publication cross-checks logged separately. URL transport blockers and successful alternatives are in `phase3CompanyBatchSourceValidation20261106.json`.

Added **241 normalized assessment records: 238 documented and 3 interpretation flags**. Much of this provides exact-trial provenance for previously source-only design fields: the net reduction in unscored slots is **28**, not 241. Added four primary successes, three failures and one nonbinary safety study. No forecasts were created. FDA links rise by two to **25 trial records / 14 programs**. The entire census and 190-column export remain intact.

The cumulative queue now has **13 companies with partial website reviews and 124 still awaiting a reconstructed website review**. No company is claimed fully complete across all 30 scientific assessments. The companion CSV lists every company, trial count, documentary coverage, missing assessment slots, official IR URL where verified, review status and blockers. Previous Aclaris and other source batches remain intact.

## Hard cases requiring further direction

These are specific data problems, not assertions that the company website cannot be found or that the information is genuinely unavailable.

| Company | Trial / problem | What would resolve it |
|---|---|---|
| Abivax (ABVX) | NCT02249988 / ABX203-002: 2016 interim futility and 2017 suspension located; final trial-specific primary endpoint table not located | Final CSR, endpoint table or original study publication. Later obefazimod/UC results cannot fill this HBV record. Sources: https://ir.abivax.com/news-releases/news-release-details/analysis-ongoing-abx203-phase-iibiii-trial-chronic-hepatitis-b and https://ir.abivax.com/news-releases/news-release-details/2016-full-year-results-and-progress-report |
| Agenus (AGEN), formerly Antigenics | NCT00126178 / C-100-12 Part 2: separate results not located; Part I has a different NCT and published failure | A Part 2-specific report or documented protocol-part/result crosswalk. Searched current pipeline, archived Antigenics SEC releases, registry and publications. https://www.agenusbio.com/pipeline/ ; https://clinicaltrials.gov/study/NCT00126178 |
| ADMA (ADMA), historical Nabi/Biotest study | NCT00538915 / NABI-7101: archived FDA clinical review located but undated; registry rate .035 and later label .037 with different CI need reconciliation | Dated original study report/analysis version or dated FDA clinical review. Not a claim that the product failed. Sources: https://www.fda.gov/media/106661/download (ZIP, Final Clinical Review - Bivigam.pdf), https://www.fda.gov/media/84782/download and https://clinicaltrials.gov/study/NCT00538915 |

Temporary shell 403/503 errors at manufacturer IR pages were resolved through the web reader or SEC originals. An obsolete Aquestive slide URL returned 404; exact-NCT FDA review and registry results supplied alternatives. Annexon's `www` pipeline URL failed, but https://annexonbio.com/pipeline/ and its publication archive worked. These are not unresolved company-access failures.

## Important trial distinctions

- Agenus C-100-12 Part I NCT00033904 has an exact-NCT Lancet publication: RFS HR .923, p=.506. Its failure does not establish the outcome of Part 2. Melanoma C-100-21 overall ITT result is separate from selected >=10-dose subgroup signals.
- Abivax miR-AGE has an interim futility disclosure and registry results. No final binary verdict is invented. Withdrawn ABX464-201 has zero enrollment and points to redesigned NCT06456593 outside this census; the original NCT is preserved.
- Alector's clinical co-primary failure survives a significant progranulin biomarker change. Continuation termination does not become an independent efficacy failure.
- Alumis states both named ONWARD trials met their primary endpoints. Program-average response rates and pooled safety are not assigned to individual trials; ONWARD3 does not inherit their success.
- Annexon's original GBS trial success is limited to the 30 mg/kg comparison. Nominal secondary p-values remain nominal. Its PRO poster includes significant day-8 PGIC but nonsignificant week-8 PGIC (p=.2917); newer GA and FORWARD studies do not inherit GBS-02 outcomes.
- Aquestive's open-label safety trial is nonbinary. FDA documents PedsQL/caregiver usability measures, but this is not a meaningful-benefit score. Registry serious-TEAE count 18 versus AE-module SAE count 17/130 remains an explicit definition/window interpretation issue. FDA supportive-trial linkage is not itself an approval letter.
- ASCENIV original FDA approval letter explicitly names NCT01814800, dated April 1, 2019. Historical approval does not erase the program's prior CRL history or become a future PDUFA date.

## Current Q01–Q30 coverage

Counts cover the 30 analytical assessments, not all cells in 190 export columns. Verified facts include observed results; the observed column is a subset. Research pending includes 1,477 registered-design facts still needing scientific interpretation. No blocked or unlocated material is labeled genuinely unavailable.

| Q | New documented records | Verified facts | Numerical | Observed | Research pending | Not publicly available |
|---|---:|---:|---:|---:|---:|---:|
| Q01 | 9 | 361 | 4 | 71 | 397 | 0 |
| Q02 | 0 | 11 | 4 | 0 | 747 | 0 |
| Q03 | 7 | 363 | 4 | 0 | 395 | 0 |
| Q04 | 1 | 4 | 4 | 0 | 754 | 0 |
| Q05 | 0 | 3 | 4 | 0 | 755 | 0 |
| Q06 | 0 | 758 | 4 | 0 | 755 | 0 |
| Q07 | 23 | 757 | 1 | 0 | 4 | 0 |
| Q08 | 23 | 753 | 1 | 0 | 8 | 0 |
| Q09 | 23 | 760 | 1 | 0 | 1 | 0 |
| Q10 | 23 | 760 | 1 | 0 | 1 | 0 |
| Q11 | 20 | 607 | 1 | 0 | 154 | 0 |
| Q12 | 23 | 760 | 1 | 0 | 1 | 0 |
| Q13 | 0 | 6 | 1 | 0 | 755 | 0 |
| Q14 | 0 | 8 | 1 | 0 | 753 | 0 |
| Q15 | 0 | 5 | 1 | 0 | 756 | 0 |
| Q16 | 0 | 0 | 4 | 0 | 758 | 0 |
| Q17 | 19 | 613 | 4 | 0 | 145 | 0 |
| Q18 | 2 | 79 | 3 | 0 | 680 | 0 |
| Q19 | 0 | 2 | 3 | 0 | 757 | 0 |
| Q20 | 0 | 0 | 1 | 0 | 761 | 0 |
| Q21 | 0 | 5 | 1 | 0 | 756 | 0 |
| Q22 | 0 | 269 | 1 | 0 | 492 | 0 |
| Q23 | 7 | 307 | 1 | 0 | 454 | 0 |
| Q24 | 7 | 274 | 4 | 0 | 484 | 0 |
| Q25 | 23 | 761 | 1 | 0 | 0 | 0 |
| Q26 | 0 | 725 | 1 | 0 | 758 | 0 |
| Q27 | 11 | 356 | 1 | 0 | 405 | 0 |
| Q28 | 1 | 6 | 1 | 0 | 755 | 0 |
| Q29 | 13 | 364 | 1 | 71 | 397 | 0 |
| Q30 | 3 | 26 | 1 | 0 | 735 | 0 |

Current totals: **13,096 unscored; 14,573 requiring research/interpretation; 691 trials without endpoint adjudication; 54 met / 11 failed / 6 nonbinary.** Existing 61 numerical slots in four trials remain unchanged.

## Resumption and verification

The idempotent `recover_phase3_company_batch_20261106.py` preserves earlier curated facts, validates exact NCT/protocol matches, and stores 23 registry snapshots with source dates/hashes. Its batch tag allows repeatable updates without duplicate slots. The live audit now exposes company source passes and hard cases, and existing integrity tests derive growing totals from actual records rather than obsolete literals. Dedicated tests protect futility/no-enrollment distinctions, continuation and pooled-result boundaries, failed clinical versus successful biomarker endpoints, and negative later PROs.

The next company passes remain in the saved 137-company queue. The current ranked API identifies ALKS (546 unscored), SVA (539), AXSM (509), IONS (456) and ACAD (358) as the largest outstanding company totals. Prior evidence is preserved while these companies receive further review. This batch does not claim to have exhausted their sources or the full 762-trial research queue. Validation: all 1,253 frontend tests, TypeScript and the production build passed. Two isolated full batch replays produced byte-identical JSON outputs. Actual-route CSV checks verify all 762 unique identities, 190 columns on every row, and parity with per-question audit totals. After rebase, the ranked-page tests and actual API reconcile 762 trials, 137 companies and 13,096 unscored slots; TypeScript and production build passed again. PR and live deployment status are reported after CI and production checks.
