# Deep Medical Intelligence — isolated preview installation

Status checked: 2026-11-07 (Pacific); deployment log timestamps may be UTC 2026-11-08.

## Scope / boundaries

- Draft PR #928 and branch `feature/deep-medical-intelligence-preview-20261107` only.
- Read-only source research from the dated **29-NCT FOCUS snapshot**.
- The 12-stage continuous worker records source checks and evidence gaps; it is **not** a completed medical/FDA decision or an approval probability.
- No RAAS, surveys, production scanner mutation, POOL/FOCUS Sheet writes, or trading automation.
- The backend is authenticated with an independent preview key, configured in Render and in the corresponding Vercel **branch-only** preview environment. Never copy that key into source, logs, or documentation.

## Existing preview resources

| Role | Resource |
| --- | --- |
| Render preview backend | [pdufa-medical-intelligence-preview](https://dashboard.render.com/web/srv-dbntrkpsrm7s73aec3lg) |
| Backend URL | https://pdufa-medical-intelligence-preview.onrender.com |
| Isolated preview database | [pdufa-medical-intelligence-preview-db](https://dashboard.render.com/d/dpg-dbnts20u01pc73do32qg-a) |
| Vercel frontend | Project `pdufa-new-dashboard`, preview branch `feature/deep-medical-intelligence-preview-20261107` |
| Code | [Draft PR #928](https://github.com/pdufa/pdufa-command-center/pull/928) |

**Free PostgreSQL expires 2026-12-08. Do not use this instance as a permanent research archive.**

## Remaining required configuration (in Render Dashboard)

The connected Render management API reports the database and service, but does **not** return a database connection URL. Do not guess the hostname or password.

1. Open the [preview PostgreSQL database](https://dashboard.render.com/d/dpg-dbnts20u01pc73do32qg-a) and select **Connect**. Copy its **Internal Database URL** (for a Render service in the same Oregon region).
2. Open the [preview backend service](https://dashboard.render.com/web/srv-dbntrkpsrm7s73aec3lg), then **Environment**. Add `DATABASE_URL` with the internal URL. Choose **Save and deploy**.
3. Keep `PDUFA_REQUIRE_POSTGRES=true`. The isolated `PDUFA_INTERNAL_API_KEY` is already configured; do **not** change the production API key.
4. After redeployment, open `https://pdufa-medical-intelligence-preview.onrender.com/health`. Expect `storage_ready: true`, `storage_kind: "postgresql"`, and `status: "ok"`. A `200` alone is **not** sufficient: `/health` returns `200` when waiting for the database too.
5. Confirm the newest **READY** Vercel preview deployment is using its branch-scoped `PDUFA_API_BASE_URL` and `PDUFA_INTERNAL_API_KEY`. Sign in to the preview and open `/medical-intelligence-preview`.
6. Start one non-production test run using the explicit **Run All 12 Stages** button. Verify exactly one immutable NCT, 12 saved stage records, separate `SOURCE_RECORDED` / `LEADS_ONLY` / `EVIDENCE_GAP` / `SOURCE_UNAVAILABLE` states, a final `ABSTAIN` decision, and the run survives page reload. Then test stop, resume and backend restart.
7. Only after those tests consider scaling across all 29 FOCUS NCTs. The roster snapshot is dated 2026-11-07 and is **not a live Google Sheets sync**.

## Code / tests

The backend Docker build context is `new-platform/backend`, so the roster is copied to `app/data/focus_snapshot.json`. Its exact-record parity with `new-platform/frontend/data/p3PostDataActive.json` is tested.

From the repository root:

```bash
PYTHONPATH=new-platform/backend python -m pytest -q new-platform/backend/tests/test_medical_continuous.py
cd new-platform/frontend
npm run typecheck
node --test tests/medical-intelligence-*.test.cjs
```

The medical-specific regression suite is the appropriate release gate for this isolated preview. The **full legacy frontend suite** still contains unrelated RAAS/TOOLS assertions against retired or missing components, and a failure there must not be mislabeled as medical-specific success.

## Data retention and rollout

The first release gate is **persistence and source provenance**, not a clinical prediction. All 12 stages report source research attempted, never an FDA approval forecast. After preview verification, choose a durable PostgreSQL plan/instance and reviewed migrations before making long-running saved research a production feature.
