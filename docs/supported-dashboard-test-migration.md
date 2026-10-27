# Supported dashboard test migration

The root `app.py` Streamlit application is deliberately retired. Its former widget names, Python import/reload helpers, nested SCANS placement and monolithic HTML grid are not the active product contract. The supported operator dashboard is `new-platform/frontend/app/Workspace.tsx` with authenticated Next.js routes and the FastAPI backend.

This migration does not restore that application, add `skip`/`xfail` markers, ignore test directories, or bypass evidence gates. Mixed Python files retain their independent engine, source-integrity, financial arithmetic, source chronology, exact-identity and authorization tests. Only retired application wiring assertions move to the runtime that now implements those behaviors.

`tests/supported_dashboard_checks.py` executes supported frontend suites in separate Node processes. It requires a successful exit, positive test discovery and zero reported failures. It caches successful suites once per pytest process; failures are not converted into skips. The backend bridge likewise requires real passing pytest cases in an isolated import environment. Tests use local fixtures and mocked requests; they do not collect FDA evidence, dispatch live scans or authorize trading.

## Retained contracts and current coverage

| Former Streamlit assumption | Supported contract now exercised |
| --- | --- |
| SCANS nested in five Streamlit subtabs | `scans-navigation-contract.test.cjs` and `scans-new-results.test.cjs`: one current top-level entry, published source-bound reports, stale/unmatched history not called new results, unknown counts preserved. Existing Python PIN and dispatch authorization tests remain. |
| Four Streamlit scoring tables and GEM cards | `candidate-assessments.test.cjs`, `gem-evidence-rendering.test.cjs`, `gem-live-rendering.test.cjs`, `gem-research-defaults.test.cjs`: exact-trial drill-down, complete versus partial scores, pagination, separate live research and saved memberships. |
| Old first-column ticker buttons and header overlays | `wt-chart-checkbox-map.test.cjs`, `gem-original-checkbox-groups.test.cjs`, `trial-filters.test.cjs`: existing controlled selection groups, exact-program scope, accessible filters, no invented overlays or membership promotion. Retained Python selection/financial/color calculations are unchanged. |
| Stage/date filters must appear above the old grid; clearing filters means zero | `pipeline-data.test.cjs`, `trial-filters.test.cjs`, `restrictions-central-placement.test.cjs`: the current central Restrictions placement, published availability totals, AND/OR rules, unknown evidence and current clear-to-full-universe behavior. |
| Market or SEC forms must not be inserted into a retired PRE PHASE 3 renderer | `research-only-backend.test.cjs`, `research-readiness.test.cjs`, `read-only-warm-retry.test.cjs`, `shared-enrichment.test.cjs`: authenticated read-only endpoints, exact program/stage boundaries, source mismatches withheld, no assessment/qualification/FS/FA writes, no orders. Standalone historical Step 4/5 form and engine tests remain. |
| A posted Phase 2 result or trial listing should appear in an old clinical pane | `candidate-assessments.test.cjs`, `numeric-forecast-metrics.test.cjs`, `main-phase3-research-panel.test.cjs`: original endpoint/group context, missing evidence stays missing, research progress does not become a validated probability or membership. All Python Phase 2 chronology and p-value joins remain. |
| Old TODAY or prediction/optimizer bookmarks should restore Streamlit panes | `retired-navigation-migration.test.cjs` renders the supported workspace: legacy requests recover to a supported page; GEM JR, GEM and WT remain distinct; SCANS uses published reports; switching views preserves selections; requests remain read-only. Archived source/history files are still checked. |
| Hot-reload evictions of a deleted Python UI module must be retried | Supported bounded read-only warm retry and candidate-provider recovery tests, including refusal to retry a POST or malformed identity, replace Python import-cache details. |

The old grid's exact CSS selectors, Streamlit tab tuple order and obsolete private Python renderer names were intentionally not reimplemented. Countdown color boundaries, original-value preservation, financing status calculations and source joins continue to be tested in their retained Python engine tests; current UI behavior is tested using actual TypeScript modules and rendered React components.

## Smoke entry point

`smoke_test.py` is now import-safe. `run_repository_smoke()` preserves all original dataset, historical-cohort, source provenance, designation, p-value and strict FDA evidence checks, while its retired application-string assertions are replaced with supported frontend contracts. CLI execution and `test_repository_snapshot_smoke` run the same checks. No part of this test migration establishes model accuracy or upgrades unverified source evidence.

## Retained filtering defect found during migration

The old `test_no_click_no_stages_or_dates_is_zero` also exposed a genuine error in the retained `pipeline_display.filter_pipeline` library. Its documented current contract makes cleared dimensions unrestricted, but both empty dimensions produced scalar `True`, which pandas interpreted as a row label. The implementation now starts with an index-aligned boolean mask and intersects selected dimensions. Regression cases verify no/one/both dimensions, unknown stages, a custom index, literal query matching and preservation of original records. No GEM restrictions or membership rules change.

Run the mixed Python contracts only after installing the frontend's locked npm dependencies and the Python development/test dependencies used by the retained modules. The bridge deliberately reports a failure if the supported runtime or its dependencies are absent; it never installs packages implicitly.

Use `npm ci --prefix new-platform/frontend` and `python -m pip install -r requirements-test.txt`, then `python -m pytest -q` for complete collection and execution. Test-only Streamlit dependencies support retained library regression checks; they do not restore or deploy the retired application. The read-only `supported-dashboard-contracts.yml` PR workflow installs both supported runtimes and executes the complete maintained Python suite. It separately reports saved-clock metadata drift as a warning, while runtime inconsistency remains a failing check.

## Verification snapshot

- The migrated mixed Python suites plus the retained repository smoke test: **136 passed, 51 subtests passed**.
- Full legacy/root-outcome suites plus `smoke_test.py`: **1,684 passed, 546 subtests passed**, with eight pre-existing pandas deprecation warnings and no failures.
- Default root pytest collection: **2,191 tests collected**, with no retired-application import error.
- The five added rendered navigation cases and the 22 migrated navigation/startup/scoring pytest entry points passed independently. These wrapper counts are not additional independent model-validation cases; referenced Node suites execute once per pytest process.
- `git diff --check` and Python compilation of the smoke entry point, filter library and bridge passed.

Logs from this verification are under the local `work/test-migration/` directory. Later application changes should rerun the affected supported suites before publishing a new verification result.
