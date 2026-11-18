# Test report

| Check | Passed | Failed | Skipped | Result |
| --- | ---: | ---: | ---: | --- |
| CI-scoped root Python suite | 2,293 | 0 | 195 | Completed, with 1,166 passing subtests |
| FastAPI backend suite | 1,387 | 0 | 2 | Completed, with 28 passing subtests |
| Full Next.js frontend regression suite | 981 | 0 | 0 | Passed on the current branch |
| Focused audit and interface contracts | 20 | 0 | 0 | Passed on the final export |
| Snapshot validation | 2 snapshots | 0 | 0 | Pinned and reconciled exports passed |
| Frontend typecheck | 1 command | 0 | 0 | Passed |
| Standalone repository smoke | 1 command | 0 | 0 | Passed |

The root test `AssessmentExportTests::test_committed_package_reproduces_retained_research_inputs` compared the entire committed evidence package against regeneration. The exporter had been selecting the moving November 17 roster for the dated November 14 research. It now reads the archived November 14 roster and verifies that its date matches the research cutoff. The committed evidence package remains byte-identical.

The backend test `test_packaged_focus_roster_matches_frontend_snapshot` compared the roster date and full record list. The canonical refresh had been updating only the frontend copy. The November 17 canonical roster changed its date and five market-cap values from November 14. The development branch now packages the same current roster on both sides, and the existing refresh stages both copies together. All 32 trial identities remain the same. Neither test assertion changed.

The full suites ran after the code fix. The final focused suite and snapshot validators ran after the last two clinical evidence updates.

The sandbox without local socket support caused the AnyIO test client to stall even on a trivial FastAPI app. The finished runs used local socket support and loopback proxy settings. The Python rerun used FastAPI 0.128.0, Starlette 0.50.0 and AnyIO 4.12.1 in the test environment. The repository dependency declarations were unchanged.

```sh
python -m pytest tests -q --disposition-report=/tmp/l1-final3-dispositions.json --junitxml=/tmp/l1-final3-root.xml
PYTHONPATH=new-platform/backend python -m pytest -q new-platform/backend/tests --junitxml=/tmp/l1-final3-backend.xml
(cd new-platform/frontend && npm test)
(cd new-platform/frontend && npm run typecheck)
python -m unittest discover -s tests -p test_2026_unrestricted_level1_audit.py -q
python scripts/audit_2026_unrestricted_level1.py --snapshot reports/2026-unrestricted-level1/2026-11-18
python scripts/audit_2026_unrestricted_level1.py --snapshot reports/2026-unrestricted-level1/2026-11-18/reconciled
python smoke_test.py
```

The audit suite validates CSV and JSON parity, duplicate keys, source receipts, date history, prospective cutoffs, retrospective exclusions, immutable inherited freezes and exact row-level blocker coverage.

The evidence recheck reproduced the full-suite totals on November 18. Root pytest reported 2,293 passed and 195 skipped, backend pytest reported 1,387 passed and two skipped, and npm test reported 981 passed. There were zero failures. The final revised exports also passed the 20 focused tests, both snapshot validators, the standalone smoke check, CSV/JSON parity, and direct checks for row-level recheck coverage, trial applicability and calibration status. Frontend typecheck passed.

The four-cycle discovery update and clinical evidence refresh changed report data only. The final 20 focused export and interface checks, both snapshot validators and CSV/JSON reconciliation checks passed. The prior full-suite baseline remains 4,661 passed, zero failed, and 197 skipped.
