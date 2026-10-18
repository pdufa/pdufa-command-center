# Moving the new PDUFA PostgreSQL database from Render to Neon

This guide is for the **separate new platform only**. Never delete or change the
existing Streamlit deployment, source records, nightly scans or existing database.

## Why

The free Render PostgreSQL staging database `pdufa-new-staging-db` currently
expires on **2026-11-15**. Render's free web service
`pdufa-new-api-staging` can remain on Render; only its PostgreSQL storage
connection needs to move. The Vercel dashboard remains at Vercel.

Neon currently has a $0 free PostgreSQL plan with a 1 GB/project storage limit,
compute/transfer caps, and a short point-in-time restore window. Free does not
mean unlimited, and separate external backups are needed for durable recovery.
Review the current Neon limits/terms before putting critical trading records there.

## Non-destructive migration sequence

1. **Connect Neon in ChatGPT** or create a free Neon account at https://console.neon.tech
   and make a project named `pdufa-new-persistent-db` in a US region near Render Oregon.
   Use a compatible Postgres version; don't upgrade to a paid plan.
2. Verify Neon has a new **empty** database. Never paste database credentials in
   ChatGPT messages, images or GitHub.
3. Confirm the new Render API is reading from Postgres in
   `https://pdufa-new-api-staging.onrender.com/health`: expect
   `storage_kind=postgresql` and `storage_ready=true`. The existing
   `DATABASE_URL` still points at Render at this stage.
4. Freeze checklist writes on the **new Render API only** by setting
   `PDUFA_MIGRATION_READ_ONLY=1` in its Environment settings. Redeploy and
   verify PUT calls receive HTTP 503. Read operations remain available.
   **Do not change any Streamlit scanner or job.**
5. Run the migration in a trusted environment able to reach both Postgres
   databases. Render DB's internal URL works only on Render's network;
   from outside use a separate authorized connection, never enable public
   access carelessly. Run inside Render infrastructure or a secure network
   bridge with verified access. The dedicated `copy_checklists.py` migrates
   the current new-platform `checklists` table, NOT Streamlit's datasets.
   This needs an execution environment with Python 3.12+ and SQLAlchemy/psycopg.

   ```bash
   export MIGRATION_SOURCE_DATABASE_URL='<old Render DB, private>'
   export MIGRATION_TARGET_DATABASE_URL='<new Neon unpooled URL, private>'
   python new-platform/migration/copy_checklists.py --check
   export PDUFA_WRITE_FREEZE_CONFIRMED=yes
   python new-platform/migration/copy_checklists.py --copy
   python new-platform/migration/copy_checklists.py --check
   ```

   Read both results. Never switch unless row counts and checksums match.
   If source is empty, verify both databases are empty; do not infer actual
   migration from the mere presence of the destination schema.

6. Change `DATABASE_URL` on the **new** Render API to Neon's recommended
   application connection string (pooling if appropriate for production
   requests); keep the old Render database running. Remove
   `PDUFA_MIGRATION_READ_ONLY` only after checking target counts and schema.
   Redeploy, confirm `storage_ready=true`, then test autosave and reload
   of GEM JR and GEM ticker selections and notes against the new DB.
7. Schedule secure backups to a separate storage destination and document
   restore testing. Keep old Render data until all tests pass and a recoverable
   backup exists. Do not delete it automatically.
8. This migration is unrelated to the source CSV/GEM scanner migration.
   No scanners or broker orders are enabled by this procedure.

## Recovery / rollback

If Neon cannot connect or validation fails: set the new Render API back to the
original internal Render `DATABASE_URL`, redeploy and confirm its health.
Do not turn writes back on until the chosen active database is confirmed,
and reconcile any post-cutover writes before switching back. The old database
remains intact during the process.

## Important limitations

* `copy_checklists.py` only transfers the new platform's current
  `checklists` table. Other future tables need separately reviewed migrations.
* This is a staged **plan and script**, not proof of executed data transfer.
* PostgreSQL credentials and any dumps must never be committed to GitHub.
* The Neon free plan can be unsuitable as the sole permanent, backed-up
  system for high-value trading data; evaluate backup retention and workload.
