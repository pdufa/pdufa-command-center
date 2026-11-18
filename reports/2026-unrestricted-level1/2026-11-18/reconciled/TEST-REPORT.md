# Test report

| Check | Passed | Failed | Skipped | Result |
| --- | ---: | ---: | ---: | --- |
| CI-scoped root Python suite | 2,292 | 1 | 195 | Completed, with 1,164 passing subtests |
| FastAPI backend suite | 1,386 | 1 | 2 | Completed, with 28 passing subtests |
| Full Next.js frontend regression suite | 981 | 0 | 0 | Passed on the current branch |
| Focused audit and interface contracts | 20 | 0 | 0 | Passed on the final export |
| Snapshot validation | 2 snapshots | 0 | 0 | Pinned and reconciled exports passed |
| Frontend typecheck | 1 command | 0 | 0 | Passed |
| Standalone repository smoke | 1 command | 0 | 0 | Passed |

The root export reproducibility test observes a difference between the committed November 14 Level 1–6 evidence package and the November 17 current FOCUS roster. The backend roster parity regression also finds a November 14 versus November 17 as-of mismatch. Both snapshots contain the same 32 NCT IDs. These failures remain visible because resolving them would require republishing or changing the lifecycle of existing production inputs.

The broad root run began before the final export refresh. The focused 20-test run validated the revised 66-cycle dataset and both snapshot validators were rerun. Frontend code and tests were unchanged during this refresh.

The sandbox without local socket support caused the AnyIO test client to stall even on a trivial FastAPI app. The finished runs used local socket support and loopback proxy settings. The Python rerun used FastAPI 0.128.0, Starlette 0.50.0 and AnyIO 4.12.1 in the test environment. The repository dependency declarations were unchanged.

```sh
python -m pytest tests -q --disposition-report=/tmp/l1-next-dispositions.json --junitxml=/tmp/l1-next-root.xml
PYTHONPATH=new-platform/backend python -m pytest -q new-platform/backend/tests --junitxml=/tmp/l1-next-backend.xml
(cd new-platform/frontend && npm test)
(cd new-platform/frontend && npm run typecheck)
python -m unittest discover -s tests -p test_2026_unrestricted_level1_audit.py -q
python scripts/audit_2026_unrestricted_level1.py --snapshot reports/2026-unrestricted-level1/2026-11-18
python scripts/audit_2026_unrestricted_level1.py --snapshot reports/2026-unrestricted-level1/2026-11-18/reconciled
python smoke_test.py
```

The audit suite validates CSV and JSON parity, duplicate keys, source receipts, date history, prospective cutoffs, retrospective exclusions, immutable inherited freezes and exact row-level blocker coverage.
