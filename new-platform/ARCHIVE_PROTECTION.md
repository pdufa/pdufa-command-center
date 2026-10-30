# Archive protection v2

This adds metadata and read-only archive evidence. It does not change archive
payloads, list membership, restrictions, FS/FA associations, scans, scientific
scores, predictions, or trading controls.

## Baseline and storage

`archive_manifests` stores the versioned archive identifier
`pdufa-ctgov-saved-scope-11622-v1`, the creation timestamp, canonical document and
SHA-256. The canonical document contains sorted NCT/checksum pairs, the original
saved download scope, counts, completion status/timestamps, database identity,
verification timestamp and audit version. Canonical encoding is UTF-8 JSON with
sorted keys, compact separators, ASCII escapes and no NaN. The manifest checksum
is the SHA-256 of the document alone, excluding the API envelope containing that
checksum. A later audit compares against this baseline; it never refreshes it.
A changed archive needs an explicitly reviewed new archive version.

Creation requires every archive check to pass, exactly 11,622 expected/physical
records, matching completed IDs, and COMPLETE download status. The source of
completeness is `full_trial_download.scope_ids`, not a current ClinicalTrials.gov
query or all registered trials.

Both metadata tables have primary keys. Run schedule keys and manifest checksums
are unique. PostgreSQL triggers reject UPDATE, DELETE and TRUNCATE, including
statement-level no-row operations. PUBLIC has no table privileges. The existing
application database owner retains INSERT/SELECT and migration privileges; no
production credentials or archive-table grants are changed. A database owner can
deliberately disable triggers or change DDL. This is application append-only
protection, not administrator-proof external WORM storage. An independently
controlled off-database copy remains a recommended future hardening step.

## Verification and scheduling

Payloads are read 100 at a time in a PostgreSQL REPEATABLE READ, READ ONLY
transaction, with a 30-second timeout per statement. Only audit metadata is
written, through a separate connection after verification. The database-wide
session advisory lock prevents overlapping runs across processes/deployments.
A unique `daily:YYYY-MM-DD` key prevents repeating a finished Pacific daily slot.
Failed results are retained and never replace a manifest. Progress logs occur at
each 1,000 records; errors log their type without credentials.

The due time is 20:00 America/Los_Angeles, including DST. The process checks every
30 seconds while running and catches up the latest due slot after a restart.
The dedicated GitHub Actions workflow on default branch main wakes the existing
free Render service at the UTC03/04 candidate time, selects the Pacific20:00
target, and polls the persisted result. Existing schedules remain unchanged.
GitHub scheduling delays and free-service wake-up mean execution is best effort,
not a guaranteed wall-clock SLA. The dashboard reports the target, last actual
verification time, overdue state and scheduler mode. It never shows a prior PASS
as current when the latest daily slot is overdue.

## Evidence inventory and consumers

`archive_readiness.py` contains explicit definitions for every present/missing
counter. Evidence flags are screened from the full JSON payloads. Missing,
malformed, absent or insufficient fields are counted separately. Scientific-ready
means a conservative evidence-screen candidate, not validated SCIENCE.
Registry FDA regulation is not FDA approval. Regulatory identifier candidates are
separate from externally verified identifiers. Archive-only verification establishes
zero externally verified outcomes; that is not a claim that regulatory evidence
does not exist. External FDA source review is still required.

Authenticated GET `/api/archive-health` supplies saved results and definitions;
GET `/api/archive-manifest` supplies the complete canonical baseline and checksum.
These APIs are read-only integrations for PIPELINE, GEM JR, GEM, WT, SCIENCE,
OUTCOME and MAIN; they do not qualify or move records automatically. The frontend
section fetches only when expanded, uses the existing session proxy, and renders
unavailable results as unverified rather than zero.

## Operations

Logs: `PDUFA_ARCHIVE_SCHEDULER`, `PDUFA_ARCHIVE_INTEGRITY_PROGRESS`,
`PDUFA_ARCHIVE_MANIFEST`, `PDUFA_ARCHIVE_PROTECTION_RESULT`,
`PDUFA_ARCHIVE_READ_ONLY_SELFTEST`, `PDUFA_ARCHIVE_APPEND_ONLY_SELFTEST`,
`PDUFA_ARCHIVE_HEALTH_HTTP`. Runtime selftests verify PostgreSQL rejects a no-row
archive delete in the read-only transaction and a no-row metadata update through
the append-only trigger. They never change an archived record or historical row.
Loopback HTTP checks re-read the saved report and manifest through authenticated
routes, recalculate the canonical checksum, and reconcile sorted IDs.

If an audit fails, preserve the manifest and all records, inspect the structured
result/error category, and reconcile the saved scope before any repair. Do not
redownload, replace records, disable protection, or change network access as an
automatic recovery action.
