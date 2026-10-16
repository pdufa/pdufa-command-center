# Deployment handoff — isolated NEW PDUFA platform only

**Do not delete, alter, redeploy or migrate the existing Streamlit deployment.**
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
6. Build and deploy **new** Vercel project; test login, ticker- and stage-specific checklist persistence, tab switching, notes, and reloading. Verify Render environment stays healthy. Check that Streamlit's deployed URL and nightly jobs are unchanged.
7. Do not activate scanners in the new app. Later migration will copy (never move) ticker data, add real GEM scoring, and verify functionality before any operator-approved cutover.

## Important staging limitations

- The current login is a **single-password prototype**, not final production authentication: no account-level separation, rate limiting, audit history, or password reset. Do not expose clinical/financial secrets or trading capabilities until production-grade authentication, audit logging, and network protections are added.
- Render free PostgreSQL databases **expire 30 days after creation** and have **no backups**. Never use a free Render database as the only permanent store for checklist selections or migrated source data. Use a durable managed database/backups before production.
- Render free web services can suspend/spin down and are not suitable for critical continuous scans.
- No Vercel/Render resources are created by merely committing these instructions or YAML. An authorized account must create/import the resources and supply secrets.

## Safety validation

Compare `main...new-platform-bootstrap` before doing anything. All files in this branch must be newly added under `new-platform/` plus the isolated `.github/workflows/pdufa-new-platform-bootstrap-ci.yml`. The existing `app.py`, `requirements.txt`, data, Streamlit settings, schedules, and other production workflows must remain unmodified.

## Rollback

Switch off the new Vercel project / Render staging service only. Do not delete source data or modify Streamlit. The Streamlit app remains the standalone existing production system throughout staging.
