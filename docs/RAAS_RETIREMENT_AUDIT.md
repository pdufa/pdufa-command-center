# PDUFA retired scoring architecture — permanent audit

**Effective:** November 7, 2026 (Pacific). **Reinstatement:** prohibited unless the project owner explicitly reverses the directive.

## Authoritative rule

The independent medical path is **POOL → FOCUS → 12-level Deep Medical Intelligence → separate approval/CRL/delay outcomes → independent certainty reliability**. The former RAAS scoring architecture is **not** an active analysis, prediction, monitoring, qualification, scan, certainty or installation dependency. Retired research data may exist only as read-only evidence archives; its past scores are never imported into new medical assessments or represented as live forecasts.

The root `AGENTS.md` and `.github/copilot-instructions.md` apply to future Codex/Copilot sessions. These documents are installed on **the default `main` branch and the isolated installation branch**.

## Audit and implementation verified

| Surface | Retirement action | Scope |
| --- | --- | --- |
| Default GitHub workflow directory | 20 named legacy YAML workflows deleted from active tree, including two formerly scheduled daily jobs | **Applied to main**, source preserved in Git history |
| Default workflow CI | `scripts/check_retired_workflows.py` and `.github/workflows/retired-workflow-default-guard.yml` reject scheduled/manual scoring workflow reintroduction; successful GitHub Action observed | **Applied and QA-passed on main** |
| Preview workflow CI | `scripts/check_retired_raas_policy.py` and `retired-architecture-guard.yml` scan live sources, UI pages, transitive imports and all workflows | **Preview branch** |
| Analyze Now backend | Removed optional read-only score-map input, numeric score fields, archived scoring fingerprints and score-dependent missing requirements; existing 12-stage worker/historical NCT record retained | **Preview branch; dedicated QA green** |
| Active prediction page | Historical score-based dashboard replaced with independent evidence-gated approval, CRL and review-delay **ABSTAIN** with null certainty | **Preview branch** |
| FOCUS & TOOLS | Removed retired score/history columns, old score components and score CSV export dependency; retained exact trial identities, clinical and regulatory source links | **Preview branch** |
| Phase-first research census | Removed old score-engine imports, numeric score composites and prediction confidence from live source-model APIs and tables, retaining the original per-NCT phase evidence and unanswered source checks | **Preview branch** |
| FOCUS research compatibility API | Converted to original-source-only evidence; old numerical export formats return HTTP 410 | **Preview branch** |
| Retired route/API namespace | Next.js `proxy.ts` blocks `/raas*` and `/api/raas*` with HTTP 410, keeping historical source and files in Git | **Preview branch** |
| Independent installation monitor | Does not include retired scoring among acceptance checks or active progress | **Preview branch** |
| Remaining nightly PDUFA handoff | Preserves source scanning, error diagnosis and safe repair; removed old scoring file triggers/labels | **Preview branch** |

**Evidence checks:** The feature-branch guard inspected 53 explicit active roots, 344 reachable modules and 129 GitHub workflows before the final follow-up patch. After cleaning those reported import chains, the guard and the dedicated Deep Medical Intelligence and MAIN QA suites passed on commit `f876c263`. The separate default-branch workflow retirement guard passed on `992a97d`. Verify current exact-head CI whenever this document is read; historical successes do not certify later commits.

## Preserved historical files — not active inputs

Hundreds of legacy-named files remain in historical data, archived research modules, tests and Git history. The feature CI checkout recorded **413** legacy-named archival source/data files at its last inventory. Preservation is intentional. Examples:

- `new-platform/frontend/data/raas-trial-score-history.json`
- `new-platform/frontend/data/bottomOnlyScoreHistory20261107.json`
- `new-platform/backend/app/data/focus_legacy_score_snapshot.json`
- Legacy `new-platform/frontend/lib/raas-*.ts` archival implementations and older tests
- Historical source records and removed GitHub Actions YAML definitions in Git history

Neither presence of historical data nor old UI source alone proves a live dependency: the preview import graph and HTTP 410 guard are the current enforcement mechanisms. Historical score claims must not appear in an independent Analyze Now report, scientific rating, FDA prediction or certainty field.

## Important release boundary / unresolved work

**The default `main` branch still hosts older frontend application code.** The 20 named workflows and agent policies were retired on main immediately, but the full active UI and API cleanup remains on draft PR #928. Until that verified preview is selectively promoted, it would be inaccurate to claim that *every* remaining default-branch UI reference is archival-only. Do **not** merge the entire unfinished medical installation merely to remove UI labels; release the retirement-specific frontend changes after full integrated verification and preserving completed POOL/FOCUS behavior.

The isolated Render backend still requires its existing separate PostgreSQL database `DATABASE_URL`; no real Analyze Now canary, automatic source rerun, validated FDA probability or certainty is proven. The draft remains unmerged. Production data and historical evidence must never be deleted.

## Continuous guard

- Default `main`: `python scripts/check_retired_workflows.py`.
- Preview/medical installation: `python scripts/check_retired_raas_policy.py`.
- Both must pass on each relevant current commit before promotion.
- Reject any PR/agent action that restores retired score inputs, forecast logic, navigation, scheduler or installation tasks without explicit new authorization from the project owner.
