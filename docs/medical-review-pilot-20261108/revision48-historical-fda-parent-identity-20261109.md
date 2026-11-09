# MAIN Revision 48 — Historical FDA source identity reconciliation before prediction backtesting

Date: 2026-11-09. Draft branch `feature/medical-stage4-verified-method-matrix-20261108`, PR #965, historical workstream issue #980.

## Actual independent live source run

[Track B historical source and identity audit #42674556624](https://github.com/pdufa/pdufa-command-center/actions/runs/42674556624) **SUCCESS**, 52 target tests passed, original FDA published approvals/CRLs re-collected, source integrity and permanent retirement audit passed. Immutable research original-source artifact [13699507674](https://github.com/pdufa/pdufa-command-center/actions/runs/42674556624/artifacts/13699507674), expires 2027-02-07.

From the fresh 2026-11-09 official Drugs@FDA **approved-product registry** and selected FDA-published complete-response-letter data:

| Research source audit measure | Actual |
| --- | ---: |
| Selected original source-action candidate records | 412 |
| Provisional grouped parent-application source identities | 376 |
| Distinct standard NDA/BLA parent IDs in that source sample | 369 |
| Unresolved application ID/source identity groups | 7 |
| Standard parent groups appearing in multiple published source action records | 33 |
| Parent ID groups with approval **and** CRL source-action records | 15 |
| Parent groups with multiple CRL source records | 10 |
| Parent groups with same-day multiple source action entries | 4 |
| Independently adjudicated review cycles and eligible historical backtests | **0** |
| Measured predictive accuracy / calibration | **UNAVAILABLE** |

**Do not divide or treat 412 or 376 as independent FDA decision cycles.** FDA action records are selected based on a publication/outcome source. They lack the complete original application filing denominator including pending, withdrawn, not yet approved, or not independently publicized decisions.

Example: original FDA source candidates linked to `BLA761303` include two **different Original submission numbers** with a 2024-03-22 selected published CRL action date, plus another selected published CRL source record dated 2025-07-30. These are **one provisional parent-source identity grouping** with potentially multiple filings/review cycles; not an adjudicated single decision nor automatically three independent prediction cases. Many other parents have both a reported earlier CRL and a later reported approval, requiring original application/amendment/resubmission chronology.

## Implementation

- Script: `new-platform/backend/scripts/build_historical_source_identity_audit_r48.py`.
- Tests: `new-platform/backend/tests/test_historical_source_identity_r48.py`.
- Integrated into independently queued Track B GitHub workflow `.github/workflows/main-r47-historical-source-track-b.yml` after current original FDA source capture.
- Output `derived/postdecision_fda_source_identity_audit.json` stores source-action research data. Separate `derived/source_selected_identity_research_worklist_NOT_MODEL_INPUT.json` intentionally excludes source action labels and action dates from per-parent research rows, but is still **outcome-selected**, neither blind nor suitable as a prediction feature. The separation is logical source hygiene, not access-controlled isolation.
- Validation rejects forged outcome labels, future action dates, missing source hashes, invalid FDA identifiers, duplicate source entries, fake cycle certification, and model eligibility; 0 clinical scores, 0 training authorization or forecast release.

## Work left before a real historical backtest

1. Construct a **consecutive original NDA/BLA filing cohort** independent of selected published outcomes; account for all pending, withdrawn, and CRL cases and unit amendments.
2. Establish original application/review-cycle IDs, first publicly available pivotal Phase 3 results, source-available-before-decision proof, and NCT/indication mapping.
3. Freeze prediction evidence, generate predictions *without access to outcome source*, then separately adjudicate original FDA action/review timing labels, with a genuinely untouched temporal holdout.
4. Only then compute coverage, accuracy, errors, and calibration. Do not promise 100% accuracy or publish predictions for inadequately reviewed current applications.

## Parallel track A intact

[Current 29-FOCUS evidence run #42672583926](https://github.com/pdufa/pdufa-command-center/actions/runs/42672583926) **SUCCESS**, all 29 NCTs / 23 provisional applications retained, 12 current posted-primary-table NCTs and 12 current registry SAP-attachment NCTs, with current source receipts and explicit unknown historical versions.

**Scheduling limitation:** Two independent GitHub jobs have been run and verified in the draft branch. Recurring `schedule` triggers require GitHub workflow files on the default `main` branch, and therefore are **not yet live** until reviewed acceptance/merge. No production or authoritative reviewer ledger mutation.
