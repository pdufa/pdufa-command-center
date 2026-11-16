# Scientific Levels 4–6: isolated staging and evidence gate

**Scope:** Development-only worktree `feature/levels-456-isolated`; draft PR #1227.
**No production merges, deployments, trades, automatic batch scans or clinical predictions are authorized.**

## Confirmed technical boundary

- The new interactive 456 panel is in FOCUS, PAST, POOL and ASSESSMENTS on the isolated branch.
- SCIENTIFIC_1_3 accepts only Levels 1–3. SCIENTIFIC_1_6 accepts only Levels 4–6.
- SCIENTIFIC_1_6 is **a source-bound research assessment**, not a validated safety, efficacy, clinical benefit or FDA approval score. Scientific scores are null; the FDA prediction always ABSTAINS.
- Only original exact-NCT registry observations and eligible source documents can be used. The historical mode requires an actual pre-decision cutoff, verified trial-to-application linkage and source snapshots captured before the cutoff. No current-data fallback.
- Save/load uses the existing `assessment_v2_` PostgreSQL tables and verifies immutable report digests on read.
- The UI chooses the 456 destination only when the explicit contract is SCIENTIFIC_1_6. It refuses to reuse the configured legacy/123 base URL or secret.

## Dedicated 456-only staging application (recommended)

A minimal, independently bootable API is available as
`new-platform/backend/app/scientific_456_staging.py`.
Its routes are restricted to scientific 456 version metadata,
exact-NCT run creation, run status and saved history; it **does not import**
`app.main` and does **not** register any FOCUS batch, PAST summary, live scan,
scheduler or trading routes.

To launch from `new-platform/backend` **only after a distinct staging database
and backend environment are provisioned and authorized**:

```bash
uvicorn app.scientific_456_staging:app --host 0.0.0.0 --port 8000
```

A separate non-root image is in `new-platform/backend/Dockerfile.scientific456`.
Select it explicitly when configuring the new staging service; the default
backend Dockerfile still launches `app.main`. Provisioning and deployment
remain **pending and require separate authorization**.

This dedicated application fails closed unless the enable flag is set, its
secret is configured, `PDUFA_REQUIRE_POSTGRES=1`, and
`PDUFA_LEVEL456_DATABASE_NAME` names the PostgreSQL database in `DATABASE_URL`
(the name must include `456`, e.g. `scientific456`). The database must
be independent of production; a schema inside production does not satisfy
this condition. It does not create, select or migrate the database for you.

## Isolated service — planning, not provisioned by this PR

**Require a dedicated backend environment and dedicated PostgreSQL database or Neon project**, not the production database and not a production database branch casually reused by an autonomous worker. Obtain authorization for resource creation and possible costs before provisioning.

Configure on the **new isolated backend service**:

| Variable | Value / requirement |
| --- | --- |
| `DATABASE_URL` | Unique isolated PostgreSQL database connection, not the production URL |
| `PDUFA_REQUIRE_POSTGRES` | `1` |
| `PDUFA_LEVEL456_DATABASE_NAME` | Name of a separate PostgreSQL database (must include `456`); must match `DATABASE_URL` |
| `PDUFA_LEVEL456_BACKEND_ENABLED` | `1` only on the isolated staging service; default disabled everywhere else |
| `PDUFA_INTERNAL_API_KEY` | New unique secret, stored as a secret environment variable |
| `PDUFA_ASSESSMENT_SCHEMA` | Not used by the dedicated 456-only application; separate database is required |
| `PDUFA_MIGRATION_COPY_ON_BOOT` | `0` |
| `PDUFA_MEDICAL_BATCH_AUTORUN` | `0` |
| `PDUFA_INSTALL_MONITOR_ENABLED` | `0` |

Do not attach production broker API credentials, production Telegram alerts, cron schedules, or production scan worker triggers to this service. Verify other startup/automation flags independently before any staging deployment.

Configure in the **development/preview frontend environment only**:

| Variable | Value / requirement |
| --- | --- |
| `PDUFA_LEVEL456_API_BASE_URL` | Dedicated **HTTPS** staging backend origin |
| `PDUFA_LEVEL456_INTERNAL_API_KEY` | Same unique secret as staging backend `PDUFA_INTERNAL_API_KEY` |

Keep existing `PDUFA_LEVEL123_*` and `PDUFA_API_*` variables separate. Do not add or change secrets in GitHub source files. Do not point the new frontend variables at a live 123 backend.

## Verify local code without provisioning

From `C:\Users\asiri\Desktop\pdufa-levels-456`:

```powershell
git pull --ff-only
$env:PYTHONPATH = "new-platform/backend"
.\.venv\Scripts\python.exe -m pytest new-platform/backend/tests -q
.\.venv\Scripts\python.exe scripts/audit_raas_retirement.py --check

cd new-platform/frontend
node --test tests/scientific-456-workspace.test.cjs
npm.cmd test
npm.cmd run typecheck
npm.cmd run build
```

These tests must be rerun after every code revision. Past passes are not evidence for untested later changes.

## Read-only staging check — only after a separate service exists

The verifier accepts the dedicated API's `stagingMode=SCIENTIFIC_456_ISOLATED_ONLY` response (original Levels 123 live elsewhere), or the earlier combined compatibility metadata. For the dedicated application, an empty history lookup requires `contract=SCIENTIFIC_1_6`.

A successful preflight also requires that the backend explicitly advertises `scientific456Enabled=true` after `PDUFA_LEVEL456_BACKEND_ENABLED=1` is set on staging. Keep this unset on production.

The staging backend has a safe read-only metadata route:
`GET /api/assessment-runtime/version`, advertising both scientific contracts and ABSTAIN status. The preflight also makes an authenticated GET for the fictitious NCT00000000 history. It does **not** submit a clinical trial or write a report.

With the two `PDUFA_LEVEL456_*` values supplied as secure environment variables, run:

```powershell
.\.venv\Scripts\python.exe scripts/verify_scientific_456_staging.py
```

Expected: `verified=true`, `safeToRunResearch=false`. **Read-only success is not end-to-end persistence verification.** A separate, explicitly selected exact-NCT exercise must verify queuing, persistence, immutable history, isolation and blind chronology before considering activation.

## Release gate

1. New targeted 456 tests and full backend suite pass.
2. Full frontend tests, TypeScript typecheck and Next production build pass.
3. Retirement audit remains at zero live violations.
4. Isolated service and credentials pass read-only preflight; production service unchanged.
5. Run one explicitly approved non-production exact-NCT assessment and verify saved immutable result. No invented scores, no approval probability.
6. Owner reviews the result and separately authorizes any eventual deployment. **Do not merge/deploy automatically.**
