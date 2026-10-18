# PDUFA Command Center — isolated next-generation starter

**Safety boundary:** Existing Streamlit production lives on the unchanged `main` branch. This bootstrap is on `new-platform-bootstrap` and under `new-platform/`. Do not merge or change production deployment until validated.

## Pipeline trial filters

Open **PIPELINE → PIPELINE FILTERS & COUNTS**. Stage Counts, Date Trial Counts,
and Trial Filters combine when **DISPLAY TRIALS** is pressed. An unchecked
group includes all records. The four qualification checkboxes cover registered
Phase 3, publicly released results, verified primary-endpoint success, and a
second separate post-readout financing close. Registered phase remains
independent of the current regulatory stage; Phase 2/3 stays separate.

**More trial filters** contains identity, recruitment status, results dates,
safety, financing dates, regulatory milestones, runway, dilution, evidence
quality, and list membership. Missing evidence does not pass a checked
qualification. Closing filters use saved reviewed historical evidence; current
source freshness is independently selectable. Filtering does not change GEM
eligibility, list membership, or entry/exit rules.

## Architecture

- Next.js 16 App Router frontend (port 3000), single-operator password session (HttpOnly cookie)
- FastAPI backend (internal port 8000), server-only API key
- PostgreSQL database for per-ticker checklist selections and notes; SQLite only as a backend-local development default
- **Autosave:** edits write to database and restore on screen return (optimistic version checks).
- Production surveys, Gmail alerts, Streamlit deployment, and other live jobs **are not migrated or started** by this bootstrap.

## Automated local setup

On a machine with Docker Compose and Python 3 installed, check out this branch and run `bash new-platform/install-local.sh`. The installer generates isolated, private random credentials, builds only the new-platform containers and starts them on localhost:3000. Keep the generated dashboard password safe. It does not edit the Streamlit branch, deploy Streamlit, or touch its files and data.

## Local container installation (no Streamlit impact)

1. Copy `.env.example` to `.env` **within this directory**.
2. Set **unique strong values** for `POSTGRES_PASSWORD`, `PDUFA_INTERNAL_API_KEY`, `DASHBOARD_PASSWORD` and `SESSION_SIGNING_KEY` (at least 32 random characters for signing key). Do not commit `.env`.
3. From `new-platform/`, run `docker compose up --build -d`.
4. Open `http://localhost:3000`, enter dashboard password, and try a demo ticker, checklist, and note.
5. Run `docker compose down` to stop. Do **not** run `down -v` unless intentionally destroying **new-platform** test data.

## To install/deploy separately

Provide/authorize new hosting for Next.js, FastAPI, and PostgreSQL. Configure HTTPS, rate limiting, robust login, backups, secret rotation, health checks, migrations, and restrictive network policies before publicly exposing any dashboard. The single-password auth is a setup/demo starting point, **not production-grade multiuser auth**. Do not enable production orders or trading from this starter.

## Next migration steps

1. Reconcile existing Streamlit data formats and source-of-truth rules.
2. Expand PIPELINE → GEM JR → GEM checklists, indicator goals and score versioning.
3. Import existing ticker history into the new database (copy first; never move/delete source).
4. Validate new scan logic against existing read-only results. Run only one production nightly scheduler.
5. Cut over with explicit approval and rollback plan. Streamlit remains available.

### Development

Backend: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload`

Frontend: `cd frontend && npm install && npm run dev` (set environment variables from `.env.example` manually).
