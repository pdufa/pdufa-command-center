# Transfer installation audit — October 30, 2026 UTC

**Installation incomplete; production readiness is not established.**

## Audited baseline and boundaries

Local branch `work` started clean at `d327093520a3996d727c0811b4d171a381ab8afe`,
the owner's supplied production baseline. Remote main's current SHA could not
be independently reconciled: shell Git access failed connecting to the managed
proxy. Connected GitHub search confirms the repository and existing draft work.
No source code, scanner settings, FS/FA associations, credentials, database rows,
network allowlists, deployment settings or schedules were changed in this audit.
This report is the only intentional repository change.

## Verified infrastructure observations

- Vercel project metadata identifies the existing `pdufa-new-dashboard` project
  `prj_7VRIuXH3FzUseTmXkzLDYQbEAd5l`. Its latest deployment is reported READY
  (`dpl_uRoSo5khw9zwBFcRjmjjEv6C2Qhk`) with target null. That is **not** proof
  of a production promotion, production SHA, or functioning application.
- Explicit team-scoped production deployment listing returned **403 forbidden**.
  Alias and alias-as-deployment lookups returned 404. No Vercel CLI is installed.
  Do not infer a production outage or repair aliases from these access failures.
- Render `My Workspace` (`tea-db967i3l550s73cadem0`) lists the existing storage,
  scientific, enrichment and HOP services and three available PostgreSQL databases.
- HOP service `srv-dbf3vm8473hc73bp16fg` has live deployment
  `dep-dbh2097f3r2c73atkkh0` at
  `2032458f98ac1469742f6e652f9ef40dd3e537f8`, with automatic deployment off.
  Its code differs from the supplied frontend baseline. This alone does not prove
  API incompatibility, but requires exact-contract checks before a release.
- The storage PostgreSQL database `dpg-db972eei0phs73fpm3u0-a` is reported
  available. A read-only SQL probe was refused because its external IP allowlist
  is empty. Provider availability does not establish SQL or application connectivity.
- Managed runtime observations are current and networking is enforced/restricted.
  No application secrets, runtime variables or outbound identities are configured
  in this managed environment. Application API authentication cannot be tested
  using a configured runtime binding here. No secret file was inspected.
- `main.py` still uses bootstrap `Base.metadata.create_all`. Reviewed reversible
  schema migrations and backup/restore verification must precede production
  schema changes; none were attempted.

## Existing work that must be preserved and reconciled

The main SCIENCE catalog has eight layers, 40 questions and maximum depth 20.
The PEAK report documents 0/40 certified assessments, 0/20 reviewed depth levels,
missing original evidence and unavailable validated probabilities. Those are
dated research observations, not newly completed scientific assessments.

Existing draft PRs include [#522](https://github.com/pdufa/pdufa-command-center/pull/522)
(historical evidence and staging reconciliation),
[#498](https://github.com/pdufa/pdufa-command-center/pull/498)
(saved first-trial research), #497/#479 (SCIENCE contracts), and #496 (historical
validation gates). PR #522 describes a different 50-level/650-field research
scope. Resolve the authoritative version against its actual directive and files
before importing it; do not silently replace main's 20-depth catalog or merge
overlapping drafts wholesale. PR bodies and prior test totals are leads, not
fresh runtime evidence.

The existing overnight entrypoint uses 20:00 America/Los_Angeles admission,
DST-aware recovery slots and duplicate protection before dispatching one awaited
chain. Code review and offline clock tests do **not** verify tonight's execution,
notifications, source collection, successful publication or database ingestion.
The separate annual Render census cron is not the overnight scanner.

## Fresh verification

| Check | Observed result |
| --- | --- |
| Frontend `node --test --test-isolation=none tests/*.test.cjs` | **391 passed**, zero failures/skips |
| Direct restriction/preset/installation/scientific gate selection | **28 passed** (overlaps the full frontend suite) |
| Frontend `npm run typecheck` | Exit 0 |
| Scanner clock/sequence, identities, backup archive, dated artifact and progress regression selection | **76 passed; 59 subtests passed** |
| Offline SCIENCE dossier/investigation/source and historical cohort/metrics selection | **60 passed** |
| Frontend production build | Compiled, then failed: Next could not parse TypeScript `--showConfig`; separate child-process probe returned `spawnSync ... EPERM` |
| Complete backend test run | Incomplete: stalled after 23 progress markers; stopped, no pass claim |
| Backend HTTP-containing research selection | Incomplete: stalled after 50 progress markers; stopped, no pass claim |
| Authenticated production flow / PostgreSQL SQL / iPhone rendering | Not verified |

The first backend invocation from repository root lacked `PYTHONPATH` and failed
collection; it was corrected by running from `new-platform/backend`. These
collection errors are not evidence of an application regression. The default
frontend runner reported 57 test-file passes; the explicit in-process rerun above
established the actual 391 individual test results despite sandbox child-process
restrictions. Generated Next files were restored; build caches are not proposed.

Local logs are in `/tmp/pdufa-*.log`; they are ephemeral, not deployment receipts.
Software fixture tests do not certify real FDA evidence or prediction accuracy.

## Progress ledger

Percentages require a fixed acceptance denominator. Where this audit cannot
establish one, **N/V** means unverified, not zero or a subjective estimate.
The historical MAIN baseline below is explicitly dated and is not refreshed by
this report. Local software test percentages are not installation completion.

| Component | Status | Completion % | Remaining work |
| --- | --- | --- | --- |
| Platform | Local frontend verified; full runtime open | N/V | Complete backend HTTP/build checks; authenticated end-to-end checks |
| Transfer | Existing baseline and draft work identified | N/V | Reconcile remote main, staging identities, draft contracts and deployment versions |
| Database | Provider available; SQL access blocked | N/V | Application health, identity/count reconciliation, migration and restore proof |
| Scanners | 76 targeted tests pass; live execution unverified | N/V | Inspect latest scheduled run, per-stage errors, date-separated publication and DB arrival |
| SCIENCE | Main 40-question catalog preserved | 0/40 = 0%, dated PEAK evidence only | Acquire originals, investigate required depths and validate evidence; reconcile newer scope |
| OUTCOME | Research abstention preserved | N/V | Exact cycle labels, justified cohort, predecision chronology and calibrated validation |
| MAIN | Existing daily baseline preserved | 1/31 = 3.23%, October 26 baseline only | Establish fresh evidence for remaining 30 gates; prove complete data path |
| Dashboard | 391 frontend tests pass | N/V | Authenticated live display, prominent supported prediction, desktop/iPhone browser checks |
| Production | Project metadata accessible; release access blocked | N/V | Restore scoped access, pass critical checks, deploy reviewed change and verify live operation |

## Prioritized continuation

1. Restore access through supported configuration: authorize the Vercel connection
   for team `pdufa` and this project; securely bind existing application credentials
   and authorize required Render origins for runtime checks. Do not paste keys into
   chat, rotate credentials, disable protection or open the database allowlist.
2. Reconcile actual remote main and production alias SHA. Retrieve the existing
   scheduled scan's jobs/artifacts and verify start/end/status/errors/results,
   latest successful timestamp, all required categories and no duplicate night.
3. Use the existing authenticated backend health and storage/reconciliation paths
   from an allowed runtime to verify PostgreSQL and immutable program identities.
   Preserve original counts, saved settings and independent GEM JR/GEM FS/FA.
4. Complete baseline backend HTTP tests and production build on a runtime where
   required child-process/event-loop operations function. Diagnose actual failures
   before making application changes. Verify backup restore in isolation.
5. Review existing draft contracts against the latest actual directive; integrate
   only tested, compatible increments. Preserve distinct PASS, CRL and formal
   EXTENSION, plus abstention when evidence cannot support a classification.
6. Exercise SCANNERS → DATABASE → SCIENCE → OUTCOME → MAIN → RESULTS → DASHBOARD
   with an exact trial/program/application identity and traceable evidence/model
   versions. Reject stale sources and incorrect cross-trial joins.
7. Deploy only after critical checks pass; verify alias SHA, authenticated API/data
   path, scheduling, published results and desktop/iPhone rendering. Deployment
   success alone does not satisfy transfer acceptance.

No implementation stage, new production deployment, complete transfer or prediction
accuracy is claimed. Baseline commit is recorded above; a report-only commit can
be identified with `git log -1` after saving this checkpoint.
