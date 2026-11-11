# PDUFA Master Automation Controller — staged v1

## Implemented scope

A fail-closed, authenticated, checkpointed controller for the already existing POOL → FOCUS workflows. This is not a second nightly scheduler. The established 8 PM Pacific sequence stays in place.

- Unique run key and pinned initial GitHub revision.
- Persistent, versioned checkpoint state in the existing Render/Neon PostgreSQL database. Table: master_automation_runs.
- Exact GitHub Actions dispatch correlation, with FOCUS artifact verification.
- A failure blocks downstream managed work. Resume resets only the failed stage and its managed descendants. Previously successful steps retain their evidence digests.
- Four-hour worker leases, optimistic version checks, rejection of duplicate active workflow dispatches, and explicit recovery of expired leases.
- Authenticated status API, read-only Vercel proxy and /automation dashboard.

MANAGED stages in v1: POOL and FOCUS only.
NOT_WIRED stages: Assessments, predictions, calendar/company/news, alerts.
OBSERVE_ONLY stages: ATSMS market monitoring and independent backups.

Do not label those other modules completed just because a GitHub workflow exists.

## Deployment gates

This PR is NOT merged or deployed and installs no live controller in production. Once reviewed and explicitly approved:

1. The existing Render backend must use its persistent Neon DATABASE_URL. Controller tables use the same guarded create-only startup pattern as existing records.
2. On Render, set PDUFA_MASTER_WRITES_ENABLED=1 only after a recovery/rollback review. Absent means controller writes return HTTP 503.
3. Configure GitHub Actions repository secrets PDUFA_MASTER_API_BASE_URL (HTTPS backend address) and PDUFA_MASTER_INTERNAL_API_KEY (matching the backend internal API key). Never paste keys into chat or commit them.
4. Set the GitHub repository variable PDUFA_MASTER_ALLOW_EXECUTION=1 only after validating the backend authentication, exact-run correlation and cost/concurrency limits. It is disabled by default.
5. Use GitHub Actions workflow Master Automation Controller — Manual Checkpoint / Resume. Start with mode plan (no writes). Mode run requires a unique run key; mode resume requires an existing Run ID and exact failed stage.
6. Do not run a master dispatch while any underlying overnight or FOCUS workflow is actively running; the executor rejects overlap.

## Example: resume without redoing completed work

- POOL: SUCCEEDED. Its source workflow run ID, verified output hash and attempt are retained.
- FOCUS: FAILED. The exact run and error are stored.
- Downstream managed stages: BLOCKED. Unwired modules are not claimed to have run.
- Operator selects resume, the same Run ID, and stage FOCUS in the manual controller workflow.
- The API confirms FOCUS really failed, refuses a stale revision, and leaves POOL unchanged. Only FOCUS and its managed descendants return to PENDING.
- The executor dispatches FOCUS once using a unique correlation token, waits for its actual workflow result, then verifies full-POOL COMPLETE coverage and a coherent promotion audit before writing SUCCEEDED.

If the worker disappeared while RUNNING, an operator must first call the authenticated POST endpoint /api/master-automation/runs/{id}/recover-expired with the latest version and stage, AFTER its lease expires. That records FAILED; then an explicit resume may proceed. There is no automatic orphan replay.

## Evidence and limits

MANAGED_STAGES_COMPLETE means that the managed source-collection and FOCUS adapters completed; it does NOT establish that all market-cap-eligible trials have finished FDA-path review, that predictions are validated, or that Alpaca markets are working. FullEndToEndCertified remains false.

FOCUS cannot succeed without correlated GitHub artifact ZIPs containing the current complete registry audit and promotion audit. Source-code drift mid-run blocks execution, while reviewed generated data can advance.

No trading, stock orders, GitHub merges, source edits, Git pushes, automatic production deployments or new cron schedules occur in controller execution.

No additional subscription is intrinsically necessary. Explicit GitHub Actions and Neon usage is still subject to plan quotas.

## Files

- Backend state machine: new-platform/backend/app/master_automation.py
- Backend API: new-platform/backend/app/master_automation_api.py
- Executor: scripts/master_automation_runner.py
- Manual GitHub workflow: .github/workflows/master-automation-manual.yml
- Browser dashboard: new-platform/frontend/app/automation/page.tsx
- Browser authenticated proxy: new-platform/frontend/app/api/master-automation/route.ts
- Checkpoint tests: new-platform/backend/tests/test_master_automation.py
- Safety CI: .github/workflows/master-automation-controller-validation.yml

## Remaining integration work

Wire and independently validate evidence contracts for assessments, predictions, CAL/company/news, alerts, ATSMS market results and backups before promoting them from NOT_WIRED / OBSERVE_ONLY into MANAGED status. ATSMS still needs its rejected Alpaca HTTP 401 authentication repaired and a durable WT results view. All currently independent schedules remain unchanged.
