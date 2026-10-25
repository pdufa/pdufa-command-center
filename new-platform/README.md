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
source freshness is independently selectable. The optional financing checkbox
narrows displayed Pipeline matches but is NOT a GEM/GEM JR eligibility gate.
GEM research requires successful exact-program Phase 3 evidence. Manual entry
signals also require fresh sourced cash runway, dilution clearance, PDUFA timing,
and technical confirmation. No orders are placed.

## Architecture

- Next.js 16 App Router frontend (port 3000), single-operator password session (HttpOnly cookie)
- FastAPI backend (internal port 8000), server-only API key
- PostgreSQL database for per-ticker checklist selections and notes; SQLite only as a backend-local development default
- **Autosave:** edits write to database and restore on screen return (optimistic version checks).
- Production surveys, Gmail alerts, Streamlit deployment, and other live jobs **are not migrated or started** by this bootstrap.

### Production research-only API integration

Production Next.js remains bound to `PDUFA_API_BASE_URL` for ordinary workspace
pages, saved assessment history, trial storage, and program management. Its
read-only market-enrichment and program-decision-readiness proxies may instead
use `PDUFA_RESEARCH_API_BASE_URL`. Only these two authenticated GET handlers
consult the research override. It is not a replacement for the storage API,
and no trading, alternate scheduler, or filesystem migration is initiated.

The research backend must verify each requested permanent Program ID and the
matching exact trial source key. A mismatch is withheld, not silently joined
by ticker, even if the same company appears in both databases. Research
responses remain for human review, never orders or approvals.

Configure the override as a server-only HTTPS URL under Vercel Production and
Preview environments, and retain `PDUFA_INTERNAL_API_KEY` server-side.
Changing the override requires a new deployment for the setting to take
effect. Disabling it falls back to `PDUFA_API_BASE_URL`; it does not
automatically copy any Program ID or clinical evidence between services.

### Historical outcome audit source

The session-protected, read-only `/api/hop/readiness` proxy uses the separately
installed `https://pdufa-hop-readonly-review.onrender.com` service. The ordinary
storage backend does not have this endpoint. HOP never changes the storage or
market-enrichment backend selection, and does not fall back to either service
on an error. `PDUFA_HOP_API_BASE_URL` can explicitly override this source with a
root HTTPS origin; an invalid override fails closed. The existing
`PDUFA_INTERNAL_API_KEY` remains server-only and redirects are rejected.

Its single 45-second request deadline includes the existing bounded warm-up
retry. A successful response reports research-source coverage; it cannot certify
review-cycle outcomes, enable predictions, or publish an approval probability.

### Isolated research evidence review

The isolated Program ID readiness endpoint reads the existing selected GEM JR or
GEM assessment. It reports source links, review dates, missing evidence, and risk
flags for catalyst timing, SEC cash runway, and financing/dilution review. It
does not assign or change any of the 21 assessment scores or FS/FA presets.

An observed `catalystTiming` review must retain `eventType` (`PDUFA`,
`PUBLIC_READOUT`, or `FDA_ADCOM`), `eventDate`, and `dateConfirmed: true` in its
existing `measurements`. A registry primary-completion date or reported PDUFA
date alone is insufficient. Past events and conflicting PDUFA dates remain
unverified. Existing seven-day catalyst/dilution and 120-day runway review
windows apply. A reviewed risk can be adverse: its grade, measurements, and
risk flags are retained. Readiness only means ready for human research review;
orders and trade recommendations remain disabled in this isolated endpoint.

The isolated primary-source catalog covers the 17 saved GEM JR/GEM programs
reviewed on October 23, 2026. Fourteen application target dates have issuer/SEC
source support; three trial readouts have already been reported and do not
establish a future public event date. Confirmed date facts can satisfy the
separate catalyst-readiness input without assigning numeric assessment grades.
The catalog is available at the authenticated `/api/review/catalyst-evidence`
route and each exact-program response retains its primary source. It expires
after seven days and requires re-review if the published date changes. Issuer
financing observations remain distinct from dilution clearance and exact-program
financing qualification. The startup smoke checks all 17 immutable identities
and the source-to-readiness link for a real application in both GEM stages.

The expanded GEM JR/GEM trial's stock-price section displays the selected stage's
existing research-readiness review, including the three catalyst/runway/dilution
checks, review dates, primary-source links, retained risks, and missing requirements.
Its authenticated frontend proxy uses the configured backend and never falls back
to another deployment. A disabled isolated endpoint is shown as unavailable.
Market and risk evidence load independently, so an Alpaca credential rejection
does not hide the clinical or financing evidence gaps. A mismatched immutable
Program ID, exact source key, stage, or unsupported readiness claim is withheld.

The same panel includes collapsed **Clinical & financing source facts** for the
17 saved review programs. It retains three complete native ClinicalTrials.gov
records with exact NCT IDs and SHA-256 receipts, and financial observations for
15 unique issuers from saved SEC snapshots or issuer-published statements. Trial
design/enrollment, registry results availability, cash, matched-period operating
cash flow, and a cash-only runway calculation retain their source dates. Liquid
securities stay separate from cash; positive cash flow and mismatched periods
do not produce a runway estimate. Filing metadata, unused ATM capacity, and
issuer-level financing proceeds do not establish an exact-program financing
close or dilution clearance. Source receipt freshness is reevaluated on every
read. These source observations do not assign grades, change the 21 scores,
update the clinical database, or remove its write freeze.

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
