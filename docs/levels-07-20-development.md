# Levels 7–20 development checklist

## Baseline at `5c02c3f7`

Each level earns 35 points for its defined method and abstention behavior, 20
for passing level-specific automated tests, 25 for verified integrated
execution (10 for its operational entry point and immutable result handling,
15 for dashboard/history and applicable reassessment or historical flow), and
20 for validating real evidence and limitations for the initial cohort (10 for
exact 32-trial reconciliation, 10 for end-to-end verified evidence readiness).
Points are earned only for demonstrated gates. The overall percentage is the
mean of the fourteen level percentages.

| Level | Baseline verified % | Evidence of progress or acceptance gap |
|---|---:|---|
| 7 | 75 | Provenance and storage, 42 passing local tests, opt-in monitor/report path, and 32 exact roster matches. Persistent real evidence and browser flow pending. |
| 8 | 0 | Readiness criteria exist in a standalone module. Test execution and end-to-end integration pending. |
| 9 | 0 | Verify phase and indication hierarchy with exact-NCT data and phase-appropriate eligibility. |
| 10 | 0 | Validate primary endpoints, populations, comparator and effect reporting. |
| 11 | 0 | Validate adverse-event counts, comparators, follow-up and exposure gaps. |
| 12 | 0 | Validate statistical methods and flag missing or conflicting evidence. |
| 13 | 0 | Evaluate subgroups and unmet need using indication-matched evidence. |
| 14 | 0 | Verify dated regulatory evidence for the exact application and indication. |
| 15 | 0 | Distinguish documented CMC risks from unavailable manufacturing information. |
| 16 | 0 | Verify advisory votes, exceptions and conflicting findings for the exact cycle. |
| 17 | 0 | Separate sourced sponsor capability evidence from unsupported inferences. |
| 18 | 0 | Persist model-versioned forecasts and explanations, with calibrated confidence or abstention. |
| 19 | 0 | Freeze outcome-isolated historical forecasts before joining adjudicated outcomes and computing accuracy/calibration. |
| 20 | 0 | Validate integrated release readiness and display/sort behavior without publishing unverified predictions. |

Overall verified acceptance baseline **5.4%**. Credit is conservative for partial
features and applies to the extended assessment contracts. Existing legacy
runtime levels and the separate Level 16 export do not verify those contracts.
All 13 visible PR-triggered workflows reported success at the baseline SHA.


## Safety and release gates
- Development branch only; no merge, production deployment, or trading action.
- Preserve Levels 1–6 behavior and stored prediction versions.
- Do not fabricate clinical evidence, numerical scores, FDA decisions, confidence, or trends.
- Missing or unverified source material must remain explicitly missing/unverified.
- Gate each level on tests, source provenance, and reproducible evidence before marking complete.

## Level 7 — Evidence collection (first implementation target)
- Inventory existing ingestion, trial identifiers, sources, and database migrations.
- Implement idempotent ingestion keyed by stable trial ID, source URL/document ID, version, and retrieval timestamp.
- Persist source publisher, document date, retrieval time, checksum, verification state, and extraction provenance.
- Distinguish source absent, source inaccessible, conflicting evidence, and not yet reported.
- Provide an audit trail of source revisions and reassessment triggers.
- Test duplicates, corrections, missing data, untrusted sources, and backfills.
- Verify no change to production endpoints or Level 1–6 outputs.

## Subsequent levels
8. Trial identity and normalized data
9. Phase and indication hierarchy
10. Efficacy
11. Safety
12. Statistical validity
13. Subgroups and unmet need
14. FDA regulatory intelligence
15. CMC and manufacturing
16. Advisory committee and exceptions
17. Sponsor/commercial intelligence
18. Versioned predictions, confidence, explanations
19. Blind historical backtesting and calibration
20. Integrated validation and dashboard release readiness

## Definition of done for each level
- Implementation committed to development branch
- Unit/integration tests run and passing
- Source and missing-data audit verified
- Prediction versions retained
- FOCUS, PAST, POOL, ASSESSMENTS regression checked where applicable
- Reviewed without merging or deploying

## Verified development milestone

Implementation commit `bc7128575dd16379ec27e3878e70cdd42797b76f`.
Verified acceptance is **73.2%** (1,025 of 1,400 checklist points).
Applying the baseline weights, all 14 levels passed their automated tests,
local runtime integration, and exact 32-trial reconciliation. Levels 7–13
earned the method gate. Level 7 earned the remaining evidence gate by
capturing and verifying each original registry response and serving the
resulting coverage report in a local browser. The other levels have open
evidence gates or incomplete scientific methods.

| Level | Verified % | Demonstrated functionality and remaining gate |
|---|---:|---|
| 7 | 100 | Official registry capture, provenance, raw digest readback and coverage display for all 32. |
| 8 | 90 | Exact identity and readiness checks. All 32 lack corroborating publisher receipts in the development store. |
| 9 | 90 | Phase, indication and population documented for all 32. Confirmatory role needs original supporting evidence. |
| 10 | 90 | Twelve posted primary readouts matched registered endpoint labels and windows. Resolve missing and incomplete comparisons before scoring. |
| 11 | 90 | Twelve posted safety readouts supported participant-count checks. Exposure, follow-up and comparator gaps remain. |
| 12 | 90 | Eight trials had reported primary analyses with consistent intervals. Eleven original SAPs supplied methods passages. One combined protocol and SAP exceeds the 16 MB retrieval limit. Confirm prespecification and execution from original records. |
| 13 | 90 | Registered populations checked for all 32. One original protocol supplied standard-of-care and unmet-need passages. Subgroup effects and broader indication-specific evidence remain unresolved. |
| 14 | 55 | Exact application, cycle and indication receipt validation. Verified FDA receipts for the cohort and automated sourcing remain pending. |
| 15 | 55 | CMC source checks distinguish gaps from documented findings. Required exact-cycle manufacturing and inspection evidence remains unavailable. |
| 16 | 55 | Advisory committee and exception source checks retain conflicts. Exact-cycle corroboration remains pending. |
| 17 | 55 | Registry lead-sponsor attribution retained. Program-specific rights and execution evidence remain pending. |
| 18 | 55 | Independent immutable predictions and abstention explanations. A validated FDA model and calibrated uncertainty are required for any numerical forecast. |
| 19 | 55 | Cutoff isolation and separate comparison of locked forecasts and adjudicated outcomes tested. No eligible real blind scored cohort has been established. |
| 20 | 55 | Local dashboard, history, sorting and reassessment replay verified. Full evidence readiness and out-of-sample predictive validation remain open. |

### Reproduce in development

Use an explicit local SQLite destination outside the repository. The
capture command saves original public registry response bytes. The validation
command reads those bytes and uses a separate SQLite ledger for assessment jobs
and immutable results.

```sh
PYTHONPATH=. python scripts/collect_level7_focus_registry.py --development-db /path/to/dev/level7.sqlite3
python scripts/level7_focus_report.py --db /path/to/dev/level7.sqlite3 --output /path/to/dev/focus-level7-report.json
python scripts/validate_extended_focus.py --evidence-db /path/to/dev/level7.sqlite3 --results-db /path/to/dev/assessments.sqlite3
```

The authenticated workbench exposes these levels when the frontend is built with
`NEXT_PUBLIC_PDUFA_EXTENDED_ASSESSMENTS=1`. The backend gate requires
`PDUFA_EXTENDED_ASSESSMENTS=1` and an isolated development
`PDUFA_ASSESSMENT_SCHEMA` whose name begins with `dev_`. Point the existing
authenticated assessment relay at that development backend. The Level 7 FOCUS
coverage panel reads the separate file configured with
`FOCUS_LEVEL7_COVERAGE_REPORT_PATH`. Hosted runtime configuration and production
activation were outside this verification.

An archived nightly monitor report includes an extended queue only for new or
changed verified registry evidence. Pass it to the validation command with
`--queue-report` to process matching locally retained evidence. The queue is
keyed by exact NCT, level and source digest. A second replay of the same
32-item queue left 448 saved results and 448 jobs with zero predictions
scored. The scheduled scan has no automatic prediction publishing path.

The 32-trial registry-only run persisted 448 assessments, all
`ABSTAIN` / `NOT_SCORED`. Chromium verified all 32 Level 7 coverage rows,
unavailable/corrupt report handling, FOCUS exact-NCT sorting and authenticated
Levels 7 and 20 execution through the frontend relay. The workbench reloaded
saved versions and sorted them by level. Historical tests verify pre-cutoff
selection and rejection of outcome leakage. The real registry capture was
current evidence and supplied zero eligible blind forecasts.

### Verification

- Backend: 1,444 passed, 2 skipped, plus 36 passing subtests.
- Repository regressions: 2,320 passed, 195 skipped, plus 1,095 passing subtests.
- Frontend: 172 test files passed. TypeScript checking and the production build passed locally.
- FOCUS alignment and read-only evidence preflight passed. The retirement audit found zero active retired dependencies.
- GitHub Actions: 13 of 13 reported PR-triggered workflows passed at the implementation commit.
- The canonical November 18 FOCUS snapshot resolved the PR conflict. All 32 trial identities and evidence fields were preserved. The differing record fields were market capitalizations.
