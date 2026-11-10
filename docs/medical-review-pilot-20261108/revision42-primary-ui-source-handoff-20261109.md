# MAIN Revision 42 — live FOCUS original primary result sources pinned to PREDICTIONS

**Run:** [Original source extraction #42658620560](https://github.com/pdufa/pdufa-command-center/actions/runs/42658620560), November 9, 2026 16:49 UTC, GitHub Actions source artifact [13693571338](https://github.com/pdufa/pdufa-command-center/actions/runs/42658620560/artifacts/13693571338), temporary archive expires February 7, 2027.

## Actual live evidence recovered

- All **29/29 exact ClinicalTrials.gov NCT registry JSON responses** retrieved and hashed.
- **12/29** have current registry outcome results sections with primary tables; **17/29** have no deposited results section at the time of source retrieval, **not** proof of absent published Phase III efficacy or a negative finding.
- **16 source-reported primary endpoint tables** captured in the archive, including arm-level result values, denominators, statistical analysis fields and p-value strings where the registry includes them. Current registry outcome records can contain more than one primary outcome, including *safety* primary entries or different subgroups. Do not infer drug approval from a posted statistical value.
- Source extraction tests and prior source-replay tests: **34 passed**. Pinned live reviewer receipt SHA-256: \`9ebfac62e6d99e105d63c107bc0aa9a52803293eba915ba4a43be3fba93f15cf\`.
- The pinned read-only frontend source metadata conservatively lists the *titles, reported posting date and p-value text only* for the 12 result-posting NCTs. The complete original JSON plus all extracted quantities remain in the archived source artifact, not in production or an authorized clinical grade ledger.

Current original primary report postings identified for ABVX (2 NCTs), ACHV (2), APMD (2), CORT (2), CYTK obstructive HCM (1), SVRA (1), URGN (1), and VERA (1). ACACIA-HCM (NCT06081894) does not have a current registry results section; published Phase III readout analyses are tracked elsewhere and must not be treated as absent.

## PREDICTIONS deployment preview integration

\`new-platform/frontend/data/focus-r42-primary-result-fields.json\` contains a source-pinned 12-row summary, exact receipt and artifact IDs, metadata date and unchanged gates. \`lib/focus-r42-primary-research.ts\` fails closed if the receipt, 12/16/29/23 counts, original R40 trial membership, source state or clinical release gates change. \`FocusRegistryPrimaryEvidenceR42.tsx\` adds an expandable source table to PREDICTIONS, linking registry primary outcomes and full original archive for each trial. The other 17 appear separately with links and an explicit absence-is-not-failure warning. A signed-in deployment verification is separate from source extraction and requires the exact Vercel preview build.

**Safety:** 0 independent clinical grades; 0 qualified clinical signoffs; 0 independently validated application-level approval/CRL/delay forecasts; 0 independently verified historical out-of-time backtests; calibrated FDA accuracy unavailable. Revision 39 research approval/CRL leans remain versioned *research-only*, not model forecasts. No production deployment or reviewer writes authorized by this update.
