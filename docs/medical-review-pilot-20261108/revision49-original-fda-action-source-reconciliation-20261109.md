# MAIN Revision 49 — original published FDA source-action metadata reconciled

**2026-11-09.** Existing independent historical research Track B and draft Stage 4 PR #965. Source run [#42685205607](https://github.com/pdufa/pdufa-command-center/actions/runs/42685205607): **SUCCESS, 78 targeted tests passed**, permanent retired-scoring audit passed.

## Real source results (not model results)

| Exact original-source comparison | Result |
| --- | ---: |
| Published FDA selected source-action rows | **412** |
| Exact parent record SHA matched to captured original FDA public-source snapshots | **412** |
| Original NDA/BLA `ORIG` submission AP action/status/date/number matched | **292** |
| Original NDA/BLA `ORIG` tentative approval (`TA`) action/status/date/number matched | **10** |
| Published FDA CRL record SHA, date, type, and application reference matched | **110** |
| Rejected/unmatched rows | **0** |
| Provisional parent source identity groups (R48) | **376** |
| Independently adjudicated original FDA review cycles | **0** |
| Qualified historical forecasts and backtests | **0** |
| Calibrated historical FDA prediction accuracy | **NOT AVAILABLE** |

These counts were reproduced from a **new live GitHub Actions run** that freshly fetched FDA published approval-product records and FDA published CRL metadata, then reconciled the selected action candidates to those exact *captured source snapshot* SHA-256 records. The `sourceProvenance` links in the R38 receipt independently match the approval and CRL snapshot byte hashes and sizes; source action date, original submission number, application identity, and CRL references must match the original captured source record. Missing/mismatching metadata are explicit blockers, never fabricated approval probabilities.

**Critical distinction:** A matching `ORIG` submission record for a published action is not an independently verified original filing *receipt* or a complete regulatory **review-cycle** chronology. CRL source metadata is selected by known published outcomes; pending/withdrawn/censored submissions, unpublished CRLs, original study readout clocks and first-publication dates remain outside this dataset. No source rows are ever handed to the forecaster as blind features. Do not divide accuracy by 412, 376, 292 or 110.

## Code and audit receipts

- Original source metadata join: `new-platform/backend/scripts/crosscheck_historical_fda_action_sources_r49.py`.
- Synthetic/anti-overclaim tests: `new-platform/backend/tests/test_historical_fda_action_source_crosscheck_r49.py`.
- Independent workflow integration: `.github/workflows/main-r47-historical-source-track-b.yml`.
- Source and research audit artifact: [13705410248](https://github.com/pdufa/pdufa-command-center/actions/runs/42685205607/artifacts/13705410248), expires **2027-02-07**, includes the original approved-product and selected CRL captured snapshots, derived selected candidates, R48 identity collision audit, and the R49 `derived/r49_postdecision_fda_original_source_crosscheck.json`.
- Distinct append-only Track B history artifact: [13703719056](https://github.com/pdufa/pdufa-command-center/actions/runs/42685205607/artifacts/13703719056), expires 2027-02-07.
- FOCUS Track A remains separate and unchanged: 29 exact current trial NCTs / 23 provisional application dossiers, with its independent scientific source/evidence-readiness history and no invented FDA predictions.

## Next regulator/clinical validation work

1. Reconstruct a **consecutive original FDA NDA/BLA filing cohort** from independently verified original submission/filed data, including pending, withdrawn, rejected, published or otherwise verifiable CRL cases, and explicitly account for unavailable/private outcomes.
2. Reconcile submission numbers and original filing/review-cycle dates for chosen pilot **drug + indication + exact NCT** groups, by original FDA letter, clinical protocol and public predecision pivotal efficacy/safety source.
3. Freeze separately archived versions of sources publicly available **after pivotal Phase 3 readout but before the review action**, generate the call in a truly blinded forecaster, then adjudicate the original independent FDA outcome in a different stage.
4. Only after sufficient source-reviewed real cases and temporal holdout can the platform measure actual accuracy and scientifically calibrate probabilities. A 100% FDA outcome accuracy guarantee is not possible.

No production promotion, training, autonomous scoring or prediction release occurred. Daily cron execution in these draft branch workflows is still not active on the default branch; isolated development execution has been verified.
