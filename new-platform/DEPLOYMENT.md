# Deployment handoff — isolated NEW PDUFA platform only

**Streamlit has been retired from the repository's active deployment setup.** The legacy source was preserved in `archive/streamlit-legacy-20261018`. An independently hosted Streamlit Cloud app, if still configured, must be decommissioned in its hosting account.
This setup uses `new-platform-bootstrap` branch and `new-platform/` path exclusively.
No PDUFA production jobs or orders are enabled by this code.

## Deployment sequence

1. Ensure Render and Vercel are authorized to access only `pdufa/pdufa-command-center`.
2. **Render staging:** Dashboard → New → Blueprint → GitHub repo `pdufa/pdufa-command-center` → **branch `new-platform-bootstrap`** → Blueprint path `new-platform/render.yaml`. Review the two **free** staging resources: `pdufa-new-api-staging` and `pdufa-new-staging-db`; check prices and conditions before approval. Set `PDUFA_INTERNAL_API_KEY` to a newly generated random string at least 32 bytes long and store it securely. Do not paste it in a chat. The Blueprint describes separate services, does not reference any existing Streamlit service.
3. **Wait for Render healthy backend:** new Render backend service URL ends in `.onrender.com`; `https://<new-backend-host>/health` should return JSON with `production_scans_enabled: false`. This is a health endpoint, not an authenticated trading endpoint.
4. **Vercel staging:** Add a **NEW** project named `pdufa-new-dashboard`; import the same GitHub repo. Set Root Directory to `new-platform/frontend` and Framework Preset to Next.js. Under Project Settings → Environments → Production → Branch Tracking set Production branch to **`new-platform-bootstrap`**, NOT `main`. Vercel otherwise defaults to `main` for Git repos, and no new frontend exists there. Ensure other existing projects are not modified.
5. **Vercel environment variables** (for Production and any preview test environments):
   - `PDUFA_API_BASE_URL` = exact public HTTPS URL of **new** Render FastAPI service, e.g. `https://<new-backend-host>.onrender.com`. No trailing slash necessary.
   - `PDUFA_INTERNAL_API_KEY` = same strong random string configured in Render, server-side only.
   - `DASHBOARD_PASSWORD` = a separate, unique strong password (minimum 12 characters).
   - `SESSION_SIGNING_KEY` = a separate random string of at least 32 characters.
   All these secrets remain SERVER-SIDE, never in any `NEXT_PUBLIC_` variable. Keep them in the hosting secret managers. Do not commit values to GitHub.
6. Build and deploy **new** Vercel project; test login, ticker- and stage-specific checklist persistence, tab switching, notes, and reloading. Verify Render environment stays healthy. Check GitHub Actions nightly scans remain unchanged; no Streamlit UI is required.
7. Do not activate scanners in the new app. Later migration will copy (never move) ticker data, add real GEM scoring, and verify functionality before any operator-approved cutover.

## Manual scan controls on the new SCANS page

The staging dashboard now reads **published** PIPELINE, GEM JR, GEM, FDA/SEC/FINANCIAL/MARKET/ISSUER status from original `main` reports and can dispatch the existing GitHub Actions workflow. **It never creates a second automated schedule.** The only 10 PM Pacific scanner remains `.github/workflows/pdufa-nightly-pacific-start.yml` on production `main`.

To activate the **START SELECTED SCAN** button, add the server-only secret `PDUFA_GITHUB_TOKEN` to the **new** Vercel project's environment variables. Use a fine-grained GitHub token restricted to repository `pdufa/pdufa-command-center` with **Actions: Read and write** permissions. Do not use a public `NEXT_PUBLIC_` variable and never put the token in GitHub files, browser code, or a chat. Redeploy the staging frontend after changing its secrets. Do not configure Streamlit; use Next.js/Vercel settings only.

The authenticated SCANS panel offers `VERIFY_ALL` (archived source validation), `REVERIFY_PARTIAL` (incremental recheck), and `RESCAN_ALL` (full recollection), targeting `ALL`, `PIPELINE`, `GEM_JR`, or `GEM`. Every manual request is sent to the **original** `pdufa-scan-control.yml` on `main`. The API checks current manual and overnight jobs and refuses to dispatch while either has an active/queued run. It does not promise the GitHub Actions job has finished: inspect the linked run and separately published evidence report. If GitHub status cannot be verified, it refuses to initiate another run.

The read-only report view and existing scheduled jobs work without this token; manual dispatch does not. Staging has **no** new production scheduler, order routing, or permission to rewrite original source snapshots directly. Do not cut over scheduling until reconciliation and an explicit separate deployment decision.

## PostgreSQL guard and activation

The Render backend has `PDUFA_REQUIRE_POSTGRES=1` configured, and the app refuses checklist reads/writes with an HTTP 503 until a persistent PostgreSQL URL is present. Check `https://pdufa-new-api-staging.onrender.com/health` and confirm both `storage_ready: true` and `storage_kind: postgresql` after connecting the database.

To activate without exposing secrets:

1. Open [the Render staging database](https://dashboard.render.com/d/dpg-db972eei0phs73fpm3u0-a) → **Connect** and copy the **Internal Database URL** (not the public external URL).
2. Open [the Render staging backend](https://dashboard.render.com/web/srv-db976hfbtjjs73bb98fg) → **Environment** → add `DATABASE_URL` with the copied URL. Do not share the URL in chat, GitHub, or a `NEXT_PUBLIC_` variable.
3. Save/deploy Render. Check `/health` and ensure PostgreSQL readiness is true.
4. On [Vercel staging](https://vercel.com/pdufa/pdufa-new-dashboard), set the `DASHBOARD_PASSWORD` secret to a privately chosen strong password and redeploy.
5. Sign in, check a box and enter a note, reload, switch stages/tickers, and confirm exact selections restore. These tests are prerequisites before moving real ticker records.

**The connected Render service must never rely on SQLite as permanent storage.** The free Postgres database is a **temporary test resource**, with a stated expiration of 2026-11-15. Production trading data must be backed up and moved to durable storage before that date.

## Important staging limitations

- The current login is a **single-password prototype**, not final production authentication: no account-level separation, rate limiting, audit history, or password reset. Do not expose clinical/financial secrets or trading capabilities until production-grade authentication, audit logging, and network protections are added.
- Render free PostgreSQL databases **expire 30 days after creation** and have **no backups**. Never use a free Render database as the only permanent store for checklist selections or migrated source data. Use a durable managed database/backups before production.
- Render free web services can suspend/spin down and are not suitable for critical continuous scans.
- No Vercel/Render resources are created by merely committing these instructions or YAML. An authorized account must create/import the resources and supply secrets.

## Safety validation

Compare `main...new-platform-bootstrap` before doing anything. All files in this branch must be newly added under `new-platform/` plus the isolated `.github/workflows/pdufa-new-platform-bootstrap-ci.yml`. The existing `app.py`, `requirements.txt`, data, Streamlit settings, schedules, and other production workflows must remain unmodified.

## Rollback

Switch off the new Vercel project / Render staging service only. Do not delete source data or modify Streamlit. The Streamlit app remains the standalone existing production system throughout staging.
