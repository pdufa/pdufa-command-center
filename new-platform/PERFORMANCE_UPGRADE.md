# PDUFA dashboard performance upgrade

Status: development plan; not deployed. Production must remain unchanged until verified.

## Current verified architecture
- Frontend: Next.js Workspace.tsx, cached verified snapshots and guarded workspace delta updates.
- Backend: workspace snapshot, summary, delta, and chart APIs.
- Pipeline has ~11,775 candidates. Pipeline display already pages 25 records; GEM/GEM JR detail table shows at most 10 records.
- Do not equate smaller rendered tables with smaller API payloads.

## Delivery sequence and acceptance tests
1. **Baseline**: measure initial response bytes, API TTFB, JSON parse time, first usable screen, tab switch, chart open, and iPhone memory. Record p50/p95 on warm and cold loads. Instrument without recording user-sensitive information.
2. **Authoritative server-side queries**: add paginated candidate endpoint with cursor, stable sorting, server-side filtering and authoritative total counts. A page response must carry snapshot version, query fingerprint, next cursor and total. Cursor invalidation must force safe reset, not silently combine versions.
3. **Progressive UI**: show initial 50 records then load more on scroll/explicit action. Keep search, qualification, and GEM/JR selection semantics server-authoritative; never compute counts or eligibility from a partial page.
4. **Caching**: retain last verified snapshot as fallback; cache page responses by version + filter fingerprint. Background fetches must cancel on filter changes. Limit cache memory and support schema migrations.
5. **Delta updates**: apply version-checked changes atomically; on missing/invalid delta fetch a full verified snapshot. Never present partially applied updates as complete.
6. **WT charts**: lazy-mount only the selected chart; cancel old requests; preserve ENTRY/STAY/EXIT indicator selection and FA independent toggle.
7. **Heavy computation**: profile first; move proven CPU hotspots to memoized selectors or worker, keeping UI responsive.
8. **Failure and rollout**: compare server counts and candidate identities with existing dashboard; test mobile/wide screen, offline recovery, filter changes, empty results, back/forward navigation, and rapid tab switching. Roll out behind a feature flag; automatically revert on elevated errors or material regressions.

## Release gates
- Frontend typecheck/build and backend tests pass.
- Pipeline, GEM JR, GEM and WT totals match the authoritative existing API for identical filters.
- Saved memberships, date-added/removed history, WT signals and charts remain unchanged.
- Compare measured p50/p95 load time and payload size against baseline; do not claim speed improvements without measurement.
- Review staging before merging to main and deploying production.
