# MAIN PDUFA — Automated Installation Progress & System Health Monitor

This monitor is **additive** to the existing MAIN 7-gate Core Platform/Pipeline acceptance checklist and the archived 31-gate audit. It neither replaces those gates nor silently resets/accepts any trial. It is independent of RAAS and surveys.

## Installed modules

- `new-platform/frontend/app/main/InstallationProgressDashboard.tsx`: expandable per-stage progress and check-level evidence shown on MAIN `/main`, refreshed every 45 seconds while open.
- `new-platform/frontend/app/api/main/installation-progress/route.ts`: authenticated and non-cached, reads the isolated medical preview backend and optional exact-commit GitHub Actions metadata. Fails closed if unavailable.
- `new-platform/frontend/lib/main-install-progress.ts`: 20 groups, including all 12 advanced analysis levels and all requested stages. Percentages are computed from explicitly defined individual checkpoints.
- `new-platform/backend/app/installation_monitor.py`: authenticated read-only record inspection, scan/evidence/revision counters, optional 5-minute persisted polling, Telegram alert queue/dedupe.
- `new-platform/backend/app/main.py`: read-only `GET /api/internal/installation-monitor` protected by `X-Pdufa-Internal-Key`, optional background monitor worker during normal service startup, and lightweight `HEAD /` liveness for Render.
- `new-platform/frontend/tests/main-install-progress.test.cjs`, `new-platform/backend/tests/test_installation_monitor.py`, `.github/workflows/main-installation-monitor-qa.yml`: isolated testing and CI.

## Honest progress measurement

**Verified installation checkpoints / all defined checkpoints × 100, rounded down**.

- Every named checkpoint has equal weight and documents its exact acceptance condition and source type.
- `VERIFIED` only where matching current evidence is present. `UNKNOWN` never counts as complete.
- `PENDING` = known required work, `BLOCKED` = failed dependency, `FAILED` = observed failing check.
- A code-defined research level **does not** certify that medical/scientific analysis has been performed.
- A Vercel READY preview **does not** certify real patient data, FDA predictions, Postgres storage or production success.
- An FDA approval probability, CRL probability, delay estimate or certainty rating is **never generated** by this monitor.
- The existing archived acceptance percentages remain dated history and do not contribute to this new live checkpoint numerator.
- The dashboard is additive to /main, which already has the historical production CI/smoke evidence and exact final FOCUS audit.

## Actual source coverage

| Signal | Verified against |
| --- | --- |
| Main frontend preview | Hosting runtime metadata and exact deployed Git SHA |
| Current CI | GitHub Actions checks **for the currently deployed SHA**, if the repo Actions API is accessible |
| Backend liveness and storage | Authenticated Render FastAPI response, real PostgreSQL readiness |
| Ingestion / source scans | `phase3_ingestion_state`, `nct_stream_runs` persisted records |
| Research collection | `medical_continuous_runs`, `medical_continuous_stages` |
| Research/prediction changes | `medical_prediction_revisions` append-only source history (all forecast values remain ABSTAIN) |
| Registry evidence updates | `medical_registry_watch` (ClinicalTrials.gov only) |
| Telegram | `installation_monitor_alerts`: actual successful `sendMessage` response required before VERIFIED |
| Historical calibration | `HISTORICAL_CALIBRATION` from locked source records (currently empty) |

External scanner schedules, external deployment failures, FDA/SEC/company/PubMed changes, and the actual Google Sheets live sync are not silently inferred from these tables. They display unknown or pending until connected to authoritative run/record APIs. GitHub scheduled workflows are checked by `event=schedule` and do not prove an external scheduler ran.

## Configure the optional monitor and Telegram

The isolated Render preview service is `pdufa-medical-intelligence-preview`. The source-side health endpoint is available without reading the database, but **database-backed monitoring remains blocked until `DATABASE_URL` is configured** with the Render PostgreSQL **Internal Database URL** in Render's own dashboard. Do not paste the database URL or Telegram credentials into chat, GitHub, documentation or logs.

On the Render preview backend, set:
- `DATABASE_URL`: internal PostgreSQL connection URL for its separate Oregon database.
- `PDUFA_REQUIRE_POSTGRES=true`: already required; do not disable.
- `PDUFA_INSTALL_MONITOR_ENABLED=true`: enables one 5-minute monitor poll loop **after** PostgreSQL readiness; this is separately enabled for the preview, not production.
- `PDUFA_TELEGRAM_BOT_TOKEN` and `PDUFA_TELEGRAM_CHAT_ID`: optional, secure Render environment variables, **never** exposed to the frontend or source control.

The Telegram queue records observed first-completed medical source runs, first registry watch baselines, Phase 3 ingestion errors and new failed medical source-run counts. Each event has a deterministic unique key and is recorded once, delivered at most once successfully; failures can be retried after 10 minutes. The monitor does not claim delivery just because a bot token was configured.

On Vercel only if needed, add `PDUFA_GITHUB_READ_TOKEN` as an encrypted **preview-branch-only** read-only token for private GitHub Actions metadata. Without GitHub API access the current-build CI/scheduled workflow evidence correctly appears UNKNOWN. The existing independent preview API URL/key must stay branch-scoped; do not copy this setup to production.

## Current verification / production boundary

A passing isolated QA tests implementation logic and fail-closed safeguards. A compiled preview demonstrates the frontend build. It does **not** certify deployed backend database records, successful Telegram delivery, current nightly scans, independent clinical adjudication or historical calibration.

The free preview PostgreSQL is not permanent storage and expires **December 8, 2026**, unless replaced/upgraded. Do not silently promote, merge the draft PR, start predictions, or change POOL/FOCUS Google Sheets.

Next checks: (1) verify the current Vercel deployment and monitor QA workflow; (2) configure internal PostgreSQL only in the Render dashboard; (3) recheck authenticated monitor output, real stage histories and error alert deduplication; (4) configure optional Telegram safely and confirm one actual success response; (5) wire additional external scanner and FDA/SEC/publication evidence pipelines.
