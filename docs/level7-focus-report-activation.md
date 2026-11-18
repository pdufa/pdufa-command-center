# Level 7 FOCUS report activation (development only)

Level 7 is an **evidence inventory**, not a clinical score or FDA approval prediction.

## Read-only activation preflight

Before generating or serving a report, inspect the actual evidence store:

```bash
python scripts/level7_activation_preflight.py --db /secure/path/level7-evidence.sqlite3
python scripts/level7_activation_preflight.py --db /secure/path/level7-evidence.sqlite3 --report /secure/path/focus-level7-report.json
```

The preflight never creates or changes the database or report. It distinguishes a missing database, invalid schema, unavailable evidence report, and a report that matches the current 32-member roster and stored evidence. An initialized but empty store can be ready to generate a **coverage-only** report with zero evidence; this is **not** an operational scientific assessment. A matching local file also does not prove the hosted frontend can read it.

## Requirements
- A real SQLite evidence store initialized using `level7_store.EvidenceStore`.
- Records must be sourced and persisted through the verified Level 7 ingestion pipeline; the packaged FOCUS roster is **not evidence**.
- The report must reconcile against the exact 32 unique NCTs in `new-platform/frontend/data/p3PostDataActive.json`.
- The report path must be readable by the running Next.js server. Do not expose the SQLite database or report artifact as a public static asset.

## Optional nightly monitor export (development only)
When the nightly monitor is explicitly invoked with a persistent, writable Level 7 SQLite path, it can also produce the coverage report in the same run:

```bash
python scripts/focus_nightly_source_monitor.py \
  --archive /secure/path/archive/monitor-YYYYMMDD.json \
  --current /secure/path/focus-monitor-current.json \
  --level7-db /secure/path/level7-evidence.sqlite3 \
  --level7-coverage-output /secure/path/focus-level7-report.json
```

The export requires `--level7-db`, does not run by default, and is not a primary-source verification or FDA prediction. The archive path must be new for each run. Do not put the SQLite file or report under a public/static directory. The monitor-derived records are unverified until separately corroborated.

## Generate and serve
From repository root:

```bash
python scripts/level7_focus_report.py --db /secure/path/level7-evidence.sqlite3 --output /secure/path/focus-level7-report.json
```

Configure the **server-only** environment variable for the Next.js frontend:

```text
FOCUS_LEVEL7_COVERAGE_REPORT_PATH=/secure/path/focus-level7-report.json
```

The FOCUS page displays the Level 7 coverage panel. Its API endpoint `/api/focus-level7-coverage` reads this file and validates roster membership and totals. It fails closed with HTTP 503 if the variable is missing or the report is invalid. An empty initialized evidence database yields 32 `NO_LEVEL7_EVIDENCE` rows, not completed assessments.

## Acceptance criteria
1. Run `python -m unittest discover -s tests -p 'test_level7_*.py' -v` and `python scripts/check_focus_snapshot_alignment.py`.
2. Generate a report from the **actual** evidence database, not a blank fixture.
3. Verify exactly 32 distinct NCT rows, their status counts, and `fdaPrediction: null` for each.
4. Confirm that `/api/focus-level7-coverage` serves the validated report and the FOCUS panel renders it.
5. Confirm missing/corrupt report returns 503 and does not display fabricated coverage.
6. Keep the development PR unmerged and production deployment disabled until explicitly authorized.

The code and passing CI alone do not satisfy steps 2–4. Do not mark Level 7 operational until the real database and deployed development environment are verified.
