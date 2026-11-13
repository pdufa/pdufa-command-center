# Automated PDUFA research — Levels 4 through 7

## Delivered implementation (draft; not deployed)

One read-only, serial, finite workflow: `scripts/pdufa_automatic_levels4_to7.py`.

- Loads the **dated 32-NCT FOCUS snapshot** already captured from connected Google Sheets. The dated snapshot is not a continuously reconciled or confirmed canonical FOCUS source; live refresh needs separate authenticated Sheets integration before operational acceptance.
- Uses **one** ClinicalTrials.gov v2 fetch per trial. Archives the *raw source bytes* with exact SHA-256 and retrieval UTC; mismatch, late source, partial failure and owner STOP fail closed.
- Generates Level 4 original trial design/endpoint evidence leads, Level 5 contradictory evidence review questions, Level 6 clinical/preclinical/regulatory gap inventory. These are phase-aware source inventories **not completed PDUFA scientific scoring**.
- Audits Level 7 temporal/model-calibration evidence gaps only once the entire batch of 32 exact source receipts passes. Never trains on post-outcome evidence or asserts fitted/calibrated FDA predictions.
- Runs the cumulative Levels 4–20 scientific assessment engine, reporting Level 4–7 readiness for each FOCUS trial. It calculates a provisional research score **only with independently prepared, criterion-specific, cutoff-safe source receipts plus explanatory ratings**; it never invents clinical ratings from unreviewed registry data.
- Emits per-level evidence JSON, 544 per-NCT level coverage rows, a summary status JSON, exact original-source archives and readable job summaries.
- Records source failures per trial without halting remaining trials; respects the local PDUFA STOP token; keeps developer/scientific approval and production deployment separate.

## Schedule

`.github/workflows/pdufa-automatic-levels4-to7.yml` declares a UTC daily schedule at **09:17 UTC**, plus manual workflow dispatch and offline PR tests. Scheduled GitHub Actions runs **only from the default branch after reviewed merge**. This draft PR does **not** activate a nightly scan on the current production branch or Windows PC. GitHub Actions runs in the cloud; it cannot inspect/start the user's Windows worker or deploy to the user's computer.

The workflow runs with read-only repository permissions, uploads result artifacts retained 14 days, and can be paused by setting the repository variable `PDUFA_RESEARCH_AUTOMATION_PAUSED=true`.

### Preview in a reviewed test environment

```bash
python -m unittest discover -s tests -p 'test_pdufa_automatic_levels4_to7.py' -v
python scripts/pdufa_automatic_levels4_to7.py --out-dir /tmp/pdufa-level4-to7
```

A live run requires network access to ClinicalTrials.gov and may return source blockers; no scientific score is synthesized from those gaps.

## Outstanding blockers to a *complete* automatically scoring Level 7 system

1. Authenticating and refreshing current canonical FOCUS membership; verifying matching drug, trial, NDA/BLA/sNDA review cycle and trial phase at each run.
2. Retrieving, comparing and independently adjudicating FDA, SEC, sponsor and scientific primary documents beyond current trial registry; computing exact source hashes.
3. Expert review of each numeric scoring criterion and weighting. Optional `--curated` permits running genuinely provided, cutoff-matched, source-backed ratings; none are fabricated. Independent review is still required.
4. Building and externally validating a real Level 7 prediction/calibration method on frozen outcome-blind historical data, including independent replication and uncertainty; no claim of calibrated FDA approval probabilities now.
5. Completing separate code-authoring/fix/PR automation and explicit review/approval. Current local agent includes bounded draft workflows but no demonstrated autonomous scientific-model coding completion. No automated merge or deploy.
6. Reviewed merge/release of this PR and site/Windows integration. No new version should be marked installed or in production before verification.

## Status distinctions

- **Engineering CI green**: offline automation and safety checks passed.
- **Scheduled job enabled**: after reviewed merge to default branch only.
- **Source ingestion complete**: all exact FOCUS registry receipts retrieved this run.
- **Numerical score present**: requires complete, phase-applicable curated source ratings.
- **Scientific Level 7 completed**: requires independent review and validated calibration; not inferred from source collection or engineering CI.
