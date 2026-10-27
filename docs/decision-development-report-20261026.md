# DECISION development report — October 26, 2026 (Pacific)

Repository: `pdufa/pdufa-command-center`. Work stayed on `feature/decision-workstream-20261026`, starting at PR #498 head `e1fed0bf36c421bdf665a18c07e744d428bd6cc8`. Existing PR changes were preserved. The cloud environment is running and usable; shell networking needed the command's network permission enabled to reach the configured proxy.

## Completed engineering

- Added openFDA request provenance and an application/submission ledger joining manual indication/outcome classifications, original linked FDA documents and cutoff-safe source chronology. Missing classifications and public-source coverage gaps remain explicit; approval metadata never assigns a CRL/withdrawal outcome automatically.
- Hardened original document URLs, calendar dates, trial phases, outcomes, source-review attestations and empty imports.
- Fixed the existing calibration test failure caused by treating a research warning as a blocking error. Added outcome-observation cutoff checks and a frozen chronological holdout evaluator with prespecified membership, model version, application-level partition isolation, training-only baseline, Brier/log-loss metrics, reliability bins and subgroup diagnostics. These are research diagnostics, not a fitted or validated FDA predictor.
- Composed SCIENCE → Historical FDA → OUTCOME → MAIN → DECISION behind exact program/trial/ticker/stage identity and cutoff gates. MAIN market observations and capture timestamps must precede the target cutoff. Missing evidence stays `NOT_READY`; complete manifests can only reach `RESEARCH_REVIEW_REQUIRED`, always with `modelValidated: false`, `probability: null` and `tradeAuthorized: false`.
- Replaced the static dashboard placeholder with a per-trial readiness table. It connects the existing candidate-assessment adapter, authenticated aggregate HOP source audit and stage-specific MAIN source endpoint. Aggregate archive counts and existing seven-category scores cannot certify a trial's independent SCIENCE/OUTCOME review. Late responses from other trials/stages are withheld. The independently reviewed manifest input exists in the composer but is not populated from unverified source counts.
- Expanded frontend CI coverage to all frontend regression files and added composition, identity, source chronology, leakage, holdout and rendering regressions.
- Fixed an existing financing-report bug that confused Phase-3-only GEM research membership with two verified financings. This changes the report's financing certification denominator, not GEM membership or optional funding rules. Corrected stale/offline Python fixtures without modifying scan configuration or scan workflows.

## Verification

| Check | Result |
| --- | --- |
| Frontend `npm test` | 86 test files passed |
| Direct execution of each frontend test file, in separate Node processes | 583 individual tests passed across all 86 files |
| Frontend TypeScript | Passed |
| Isolated local Next.js build, `npm run build -- --webpack` | Passed against the committed frontend sources; no deployment |
| Backend pytest suite and reconciliation evidence test | 501 passed, 1 skipped |
| Focused Python regressions covering the fixes | 61 passed, 51 subtests passed |
| Full legacy/root outcome pytest suites | 1,635 passed, 43 failed, 541 subtests passed |
| Whitespace/diff checks | Passed |

The installed Node runtime's default `node --test` output reports file-level results; separate direct runs provide the individual test count above. The new financing-denominator regression was collected after the full legacy run and is included in the separately passing focused suite. No failing tests were removed or skipped to produce these results. The unrestricted `pytest -q` discovery also cannot collect `smoke_test.py`, which reads the retired root `app.py` during import; the named suites above run independently of that obsolete smoke script.

Intermediate logs are under the uncommitted `work/` directory: `final-frontend-direct-summary.json`, `final-frontend-direct-tests.log`, `final-frontend-tests.log`, `final-frontend-build.log`, `baseline-backend-network-tests.log`, `final-python-regressions.log`, and `final-legacy-tests.log`.

## Milestone status and remaining work

| Milestone | Status |
| --- | --- |
| 1. Existing tests and failures | All named suites run; relevant fixes verified. Legacy baseline remains blocked as detailed below. |
| 2. Historical FDA integration | Retrieval/ledger/provenance software completed; independent historical evidence adjudication remains incomplete. |
| 3. Calibration and validation | Leakage controls and holdout diagnostics completed; real predictive validation is blocked by missing original evidence. |
| 4. Connect the workstreams | Composer and existing source connections completed; independent reviewed trial manifests remain absent. |
| 5. Existing dashboard | Per-trial readiness panel integrated and tested. |
| 6. Regression verification | Frontend/backend and focused regressions pass; broad legacy failures remain visible. |
| 7. Commit verified changes | DECISION integration committed locally as `dd4f9f65`; financing fixes, fixture updates and this report are committed separately on the same branch. |
| 8. Continue autonomously | Continued through all safe engineering work; stopped at evidence and legacy-migration decisions. |

## Blockers requiring decisions or evidence

1. Forty-two remaining legacy failures depend on deliberately retired `app.py` (40 ordinary failures plus two subtest failures). README points to the legacy archive; the app was not resurrected. Decide how to migrate or archive those tests against the supported dashboard.
2. One remaining failure detects saved scan configuration at **22:00 Pacific**, while the existing launcher uses **20:00 Pacific**. Confirm the intended saved setting. Neither configuration nor production schedules were changed.
3. Supply independently reviewed 20-level SCIENCE/OUTCOME records, original FDA application/indication/review-cycle outcomes including nonapprovals, complete cohort membership, original predecision forecasts and their frozen plan/model versions, plus audited historical market snapshots. Current HOP source metadata is quarantined with zero model-eligible cycles. Source metadata and self-declared review flags do not independently verify records. No validated accuracy or approval probability is established.
4. The environment's enforced network allowlist lacks official FDA hosts. Further direct FDA collection needs the supported environment configuration workflow to allow `api.fda.gov`, `www.fda.gov` and `www.accessdata.fda.gov` (and any other specifically reviewed FDA source host needed), or independently reviewed offline source exports. The proxy policy was not bypassed.

GEM JR/GEM/WT restrictions, membership logic and FS/FA associations were preserved. No production changes, merges, deployments, order routing or trading enablement occurred. Commits remain local because PR #498 has an existing Vercel integration that could deploy on push. To roll back, revert the new local commits on this development branch; the prior PR head remains in history.
