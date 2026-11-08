# Permanent RAAS retirement — 2026-11-08

The owner's permanent policy is implemented in root `AGENTS.md` and enforced by `scripts/audit_raas_retirement.py --check`, the existing CI on all main pushes/pull requests, backend write guards, archive integrity pins and regression tests.

- Active dependency violations: **0** across 220 active entry points and 503 reachable source files.
- Historical score/review data: **104 files hash-pinned and byte-preserved**; read-only archive at `/archive/raas`, GET-only exact-NCT export at `/api/archive/raas`. Archived code is not an active calculation path.
- Legacy APIs: **18 return HTTP410** without importing calculators. Active FOCUS, source views, predictions and certainty no longer use the retired numerical outputs.
- Former writer CLI entry points: **71 fail closed before imports/network/data writes**. Original source bytes remain in `archives/raas/cli`.
- GitHub workflow state: **21 RAAS workflows disabled and read-back verified**. Original definitions remain under `archives/raas/workflows`; FOCUS nightly retains raw source/roster synchronization, with scoring and history writes removed.
- Installation: completed task IDs, dated task-evidence registry and original task catalog preserved. Active requirements project out retired work; no installation reset or restart.
- Test migration: 98 obsolete RAAS/survey UI acceptance specifications are preserved in the historical archive instead of requiring retired features. Supported source, filtering and data tests remain active with source-only expectations. Nothing is silently skipped as a substitute for validation.

Validation: 687 supported frontend tests passed; backend1133 passed/2skipped; root retirement23 passed; production build passed; desktop/mobile browser verified18 retired APIs, original historical records, source-only FOCUS membership and independent preview. See `verification.json` and browser receipts. Production deployment is recorded only after verification.

## Continue the independent installation

The additive independent preview `/preview/deep-medical-intelligence` now works from raw ClinicalTrials.gov sources, with 12 explicit installation levels and separate application-outcome/timing fields. The collector gives every discovered trial a processing state, without a trial-count cap. It preserves 11,644 POOL NCTs, adds the29FOCUS identities to the union (11,647 total), keeps terminated/withdrawn records and distinguishes6unlinked aliases from true NCTs. All29FOCUS raw registry packets were refreshed;47total raw registry packets were reused/captured.

**Scientific interpretation remains incomplete.** Program groupings are provisional application targets, application numbers/current goals require verification, and zero candidate decisions are certified complete. No efficacy result, CRL, manufacturing problem or numerical approval probability is invented. Existing POOL/FOCUS data and spreadsheet membership are unchanged. Full original-source adjudication, application crosswalks, independent challenges and outcome validation remain the next installation work; existing completed work is retained.

Deployment verification: Render staging commit `d11c3d74b` is live with HTTP200 and PostgreSQL ready. The existing medical preview commit `5608059b0` is live with HTTP200 but reports `POSTGRES_NOT_CONFIGURED`; this remains an explicit installation data-access limitation. No database was configured or reset. Final local production-build smoke verifies all15installation sections, anonymous access protection and the unchanged741-trial public CSV.
