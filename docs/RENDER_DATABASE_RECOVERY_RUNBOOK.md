# Render PostgreSQL recovery runbook

**Status: preparation only. No live database export or restoration has been performed.**

## Scope

The confirmed Render **My Workspace** (`tea-db967i3l550s73cadem0`) contains three independent PostgreSQL 16 databases:
- `pdufa-new-staging-db` (ID `dpg-db972eei0phs73fpm3u0-a`)
- `pdufa-alpaca-review-db` (ID `dpg-dbdnnd59fdbs73bp0c00-a`)
- `pdufa-scientific-assessment-review-db` (ID `dpg-dbehv1avcj2c73d0uk4g-a`), used by the isolated Scientific Assessment review service (`srv-dbehn9fb9u1s739ok5vg`).

Export each separately. Do not infer that either database is production solely from its name. Verify each service's `DATABASE_URL` target privately inside its authorized runtime. Never print or share the URL.

## Prerequisites

1. Confirm which Render service is connected to each database. Do not change connection strings, networking allowlists, or running services.
2. Arrange an authorized environment with PostgreSQL `pg_dump` client compatible with PostgreSQL 16 and repository code containing `scripts/export_render_postgres.py`.
3. Ensure adequate **private persistent** space for dumps and an approved secure transfer destination. Render's ephemeral service filesystem is not a durable backup location.
4. Verify that a backup is allowed for the database's plan and that credentials are available as `DATABASE_URL` in the execution environment.
5. Keep all dump files out of Git, public Vercel assets, logs, and public links.

## Manual export (one database at a time)

From an authorized environment connected to the intended database, run:

```sh
python scripts/export_render_postgres.py --output /private/backup/pdufa-staging-YYYYMMDD.dump
sha256sum /private/backup/pdufa-staging-YYYYMMDD.dump
pg_restore --list /private/backup/pdufa-staging-YYYYMMDD.dump > /private/backup/pdufa-staging-YYYYMMDD.contents
```

Repeat for the separately confirmed Alpaca and Scientific Assessment review databases using distinct filenames and their own environments. Never overwrite. Save SHA-256 checksums in a private recovery manifest. The exporter fails closed if `pg_dump` is missing or output exists. Both the repository script and the container copy decode URL-encoded credentials, create dumps with owner-only permissions (`0600`), and preserve an output created by another process during preflight.

## Isolated restoration rehearsal

Create an **empty, disposable database**, entirely separate from all existing Render databases. Restore a copy with a credential scoped to that isolated target:

```sh
pg_restore --no-owner --no-acl --dbname "$RESTORE_TEST_DATABASE_URL" /private/backup/pdufa-staging-YYYYMMDD.dump
```

Before running, confirm `RESTORE_TEST_DATABASE_URL` is **not** any existing live or staging database. Never use `--clean` or `--create` against a live database. Compare table counts and representative application records between source and isolated restore, including independent GEM JR / GEM FS and FA preset memberships. Do not change those associations.

## Completion criteria

- All three independent database dumps exist in approved private durable storage.
- Each dump has SHA-256 recorded and passes `pg_restore --list`.
- All three are successfully restored into isolated databases with matching counts and key application invariants. For the Scientific Assessment database, additionally verify archived gzip/SHA-256/NCT identity, batch history, ledger revisions, PDF bytes/manifests and reviewer findings.
- Current source archive, Sheets exports, non-secret deployment configuration and recovery instructions are preserved.
- Secrets are documented as **re-provision required**, not copied into an archive.
- A full-system ZIP is labeled complete only after all criteria are met and the restore is tested.

**Important:** No automated job or public HTTP export endpoint is enabled by this runbook.

## Source rebuild versus database recovery

The isolated-source recovery workflow at deployed commit `6d20d91295adada8accf4253a3d5d824451dedee` successfully rebuilt the frontend from a fresh source archive and ran the recovered backend regression suite: [verified workflow run](https://github.com/pdufa/pdufa-command-center/actions/runs/40194148115).

That verifies source reconstruction, not a live PostgreSQL dump, durable backup, point-in-time recovery, or database restoration. Those criteria remain pending until their own artifacts and isolated restore results exist. The hosted Render query connector cannot reach the databases while their external IP allowlists are empty; keep that network isolation in place and use an authorized internal runtime for exports. Dashboard-only backup controls require an authenticated Render browser session.

## Scientific platform installation verification — 2026-10-25

The isolated review deployment `dep-dbevhlbrjlhs7391sk9g` became live at `2026-10-25T12:41:31Z`, running commit `6d20d91295adada8accf4253a3d5d824451dedee` (including installation fixes in `65756bf8bd8020b02f3824e0676da081d28ecdd5`). The public `/health` check returned HTTP 200 with PostgreSQL storage `READY`. No runtime errors were returned in the post-deploy error-log check.

At `2026-10-25T12:41:39Z`, `SCIENTIFIC_API_READ_PROBE status=PASS checks=7 stored_trials=2 batch_jobs=2 domains=8 read_only=True scores_assigned=False` confirmed real loopback HTTP responses using the existing environment-held key. It checked missing/wrong credential rejection, persistent archive status, batch history, the exact archived assessment, the eight-domain pilot and the checksum-verified review packet. The probe performs GETs only and never exports credentials or response bodies.

All workflow runs for that deployed revision completed successfully, including scientific integration, backup export safety, browser acceptance, source reconstruction and the main CI checks. The backup-export fix is installed, but it has not yet produced a live database backup or verified restoration. The remaining recovery step requires an authenticated Render dashboard/internal execution path; the browser is currently at Render's sign-in screen. Do not label the full platform installation or database recovery complete on the strength of these checks alone.
