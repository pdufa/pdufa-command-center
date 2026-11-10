# MAIN Revision 56 — Savara original current protocol/SAP methodological reconciliation

**Date:** November 9, 2026 (PST). **Workflow:** [R56 PASS, GitHub Actions #42699626055](https://github.com/pdufa/pdufa-command-center/actions/runs/42699626055), **79 targeted tests passed**; permanent retirement guard passed, feature-only draft PR #965. Exact original registry (29 NCT/23 provisional FDA applications), 23 current protocol/SAP PDFs, R54 eight-domain page leads, and R55 current efficacy/safety evidence packets all rebuilt successfully. **Source artifact**: [13711910107](https://github.com/pdufa/pdufa-command-center/actions/runs/42699626055/artifacts/13711910107) (expires 2027-02-07); source report: `SAVARA_PRIMARY_METHODS_AND_SAP_EXCEPTIONS_R56.json` in that artifact.

## Current Savara IMPALA-2 sources crosschecked

- [Protocol NCT04544293, `Prot_000.pdf`](https://cdn.clinicaltrials.gov/large-docs/93/NCT04544293/Prot_000.pdf) — current publicly attached **version 10.0**, document dated **October 9, 2024**, **134 PDF pages**, SHA-256 `0748f6e524971b4612eaaf509b61cf1569f0393a3475a6ee172789fa71c0c849`.
- [Statistical analysis plan `SAP_001.pdf`](https://cdn.clinicaltrials.gov/large-docs/93/NCT04544293/SAP_001.pdf) — current publicly attached **version 1.0**, document dated **April 24, 2024**, **89 PDF pages**, SHA-256 `2f3494c191c2038322e0047b040a03ef5f99e1b02be2fb373f477e2930855888`.
- **These printed document dates are not proof of the versions' first public posting times, signed locked versions, original pre-unblinding SAP or FDA acceptance.** The SAP is document-dated earlier than the attached protocol's latest version; earlier protocol revisions and amendment dates must be reconciled.

## Source-anchored method descriptions

Six *paired source descriptions* appear in both documents. This only verifies identifiable source text; it is not proof of prospective agreement or correct implementation:

| Method area | Protocol original PDF lead | SAP original PDF lead |
| --- | --- | --- |
| Week 24 DLCO as primary endpoint | Primary endpoint statistical effect and P-value: pp. ~73–74 | Primary hypothesis: pp. 24–25 |
| Full randomized analysis set | FAS definition: p. 69 | FAS definition: p. 24 |
| Mixed model for repeated measurements | Primary MMRM: p. 73 | Treatment-policy MMRM: p. 27 |
| Sequential alpha control | Type I error control: p. 70 | Multiple testing/alpha splitting: pp. 25–27 |
| Missing-data imputation | Control-based rule: p. 74 | Two-stage, 50 completed sets: p. 40 |
| As-treated safety population | Safety analysis set: pp. 69–70 | SAFS: p. 24 |

**Explicit self-described differences in SAP Section 11, PDF p. 65:**

1. DLCO measurement averaging. The SAP says a protocol-described average of **two best efforts** was updated to an average of **all acceptable DLCO observations** under overreading guidelines. This requires examining original protocol versions and the calculation's potential clinical effect. It is not automatically an integrity breach.
2. Type-I-error diagram. The SAP acknowledges the earlier protocol's \(\alpha_1,\alpha_2,\alpha_3\) schematic did not fully agree with the written hierarchy/Hochberg description, and says the figure was corrected. Need to verify hierarchy and original first-available timeline.
3. Serious safety terminology. The SAP changes a **serious adverse drug reaction** objective to **serious treatment-related adverse events**, leaving ADRs for an integrated safety summary. Need independent definitions, coding and exposure review.

## Observed current public ClinicalTrials.gov reported outcome

- Primary endpoint current source-reported P-value **0.0007**, treatment difference **6.0 percentage points**, CI **2.5 to 9.4**.
- Its reported numerical P-value is below the SAP's nominal two-sided 0.05 primary testing threshold, **conditional on the endpoint, data, model and SAP prespecification being confirmed**. The primary outcome has not been statistically independently recalculated.
- Current posted serious adverse event affected/at-risk values are **14/81 and 20/83**, as arm-level registry reporting, **not causal safety estimates or a pooled treatment-risk inference**.
- Neither these numbers nor the method text resolves independent benefit-risk, manufacturing/CMC, FDA inspections, original locked SAP or regulator outcome. **Official FDA outcome and delay forecasts ABSTAIN, grade/probability null, independent signoff 0**.

## Implementation and validation

- Source script: `new-platform/backend/scripts/reconcile_savara_methods_r56.py`
- Regression tests: `new-platform/backend/tests/test_savara_methods_reconciliation_r56.py`
- Existing original-PDF workflow extended with exact source byte and R54/R55 source joins, method-page verification, explicit SAP differences and research report output.
- The comparator rejects forged PDF hashes, changed source numbers, missing Section 11 text, incorrect 29/23 membership, false clinical signoffs and any training/prediction permission. All 29 NCTs and 23 application IDs remain unchanged.
- Across all 29 trial records, an auxiliary audit identifies current SAP-document dates earlier than any attached protocol document (needs version chronology). **Absence of a current attached SAP in 17 trials does not prove another source is unavailable.**

## Next strictly necessary scientific steps

1. Recover earliest **authenticated dated** protocol revisions, SAP signatures, original first-public snapshots and **pre-unblinding/database-lock timeline**; blocked ClinicalTrials.gov internal-history API attempts must not be circumvented.
2. Independently adjudicate the DLCO averaging rule's effect on the reported Week 24 estimate, exact alpha family/gate behavior, missing-data assumptions, statistical population, and case-specific serious AE exposure/coding.
3. Seek independently verifiable FDA application/CMC/inspection sources. Run separate historical original-filing cohort and **sealed predecision/outcome-blind** validation on Track B; without this no credible measured accuracy or 100% target claim.
