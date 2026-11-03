# PDUFA Command Center — active platform

**Operational stack (November 3, 2026):** Next.js frontend on Vercel, FastAPI backend on Render, and GitHub Actions for the research scans and published source reports.

- Live dashboard: https://pdufa-new-dashboard.vercel.app
- Frontend: `new-platform/frontend/` (Next.js / React)
- Backend: `new-platform/backend/` (FastAPI; configured Render service)
- Main research area: **POOL → PIPELINE**, with evidence, FDA outcomes, scientific evaluation, and supporting commercial analysis
- Eligibility focus: publicly traded issuers with a $300 million–$10 billion market cap and source-verified post–Phase 3 programs. Keep unverified claims clearly labeled; do not remove historical POOL records.

## Current dashboard

The deployed Next.js site contains the Pipeline, Tools, Compare Trials, Scans, Predictions, Patient Population and System Status navigation. Its authenticated landing page also links to the complete POOL and dated RESULTS. Dashboard visibility does not guarantee that a scan, a score, or its evidence is complete; use the source status and dated run results to confirm.

**Streamlit is retired from the active platform.** Do not deploy an `app.py` entrypoint or configure a Streamlit Community Cloud application for current operations. GEM JR and GEM are retired research selections, not active nightly scan stages. Historical data can remain accessible for provenance without being treated as current eligibility or prediction input.

## Nightly research process

The active GitHub Actions orchestration is:

1. `.github/workflows/pdufa-nightly-pacific-start.yml` — guarded **8:00 PM Pacific** scheduled start, including duplicate protection and recovery slots.
2. `.github/workflows/pdufa-overnight-sequential.yml` — one awaited sequence of clinical collection, scan reporting, source checks, shared enrichment, scoring/repair and dated archival.
3. `.github/workflows/pdufa-nightly-clinical.yml` — Pipeline inventory/enrichment plus posted Phase 3 results, using source snapshots.
4. `.github/workflows/pdufa-nightly-missing-sources.yml` — FDA, SEC, financial, market and issuer evidence checks.
5. `.github/workflows/pdufa-nightly-scoring-then-repair.yml` — scoring-input audit, error checks, and guarded repair.
6. `.github/workflows/pdufa-scan-control.yml` — operator-requested verification and targeted rechecks.

A scheduled dispatch is **not** proof that a scan completed. Check GitHub Actions and the site's dated RESULTS / source-verification records for actual success, failure, partial evidence, or missing inputs. Required repository secrets must be configured separately and never committed.

The separately proposed **Prediction Accuracy & Calibration Scan** is **not yet an installed nightly stage**. Do not represent calibration, outcome learning or validated probability improvement as active without its own code, measured benchmarks and completed runs.

## Local frontend development

```bash
cd new-platform/frontend
npm install
npm run build
npm run test
```

For local development, run `npm run dev` in that directory. Backend code and tests are under `new-platform/backend/`; do not infer production service health from a successful local build.

## Historical records and retirement boundary

Historical Streamlit implementation and its documentation are intentionally preserved, **not deployed**:

- Archived implementation branch: [`archive/streamlit-legacy-20261018`](https://github.com/pdufa/pdufa-command-center/tree/archive/streamlit-legacy-20261018)
- [Superseded README / legacy operating instructions](docs/archive/legacy-readme-pre-streamlit-retirement-2026-11-03.md)

The legacy README contains outdated Streamlit, GEM and 10 PM scheduling instructions. **Do not follow those instructions for the current system.** The active site's code, Vercel project settings, and the current GitHub workflow files above take precedence.

Do not delete source archives or deactivate Pipeline/Phase 3 GitHub Actions as part of retiring Streamlit. Removing any separately provisioned external Streamlit Cloud or Render resource requires verifying its precise identity and that it is not used by the current FastAPI/Next.js stack. No external account resource is assumed deleted by this documentation change.

## Security and accuracy boundaries

- Never place API keys, email passwords, cloud secrets, or credentials in the repository.
- Keep historical trial identities, NCT source citations, timestamps and archived decisions intact.
- Failed or incomplete source retrieval must remain visibly **partial / unverified**; missing evidence is not a zero score or an automatic FDA prediction.
- Predictions are research estimates, not regulatory decisions or authorization to trade.
