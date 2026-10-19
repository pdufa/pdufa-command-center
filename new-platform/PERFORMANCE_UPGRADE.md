# PDUFA dashboard loading repair

The hybrid loading implementation serves a small first page before transferring
the full dataset required by the existing qualification screens.

## Behavior

- The authenticated pipeline page API returns 50 records, a content version,
  authoritative matching total, offset and next offset. Search runs across the
  complete published universe. Version changes return 409 and require a reset.
- The quick view retains one page at a time. Previous/Next reaches records past
  the first 100 without growing the DOM or accumulating the entire pipeline.
  Changing a query cancels the previous request; a late result cannot replace it.
- Initial page loading has priority over the complete transfer. Full-snapshot
  qualification, saved identities, history, WT preferences, charts and verified
  delta refresh continue to use the complete dataset, never a partial page.
- Backend full loads, pages and startup verification reuse the same numbered
  snapshot. JSON and gzip bytes are prepared once per source object, bypassing
  FastAPI's recursive per-request serialization of approximately 10 MB of data.
  Private cache headers and explicit stale-source behavior are preserved.
- Cached source readers do not wait behind an external-source refresh. Stale
  copies are explicitly marked and cannot receive a verified delta/page version.
- Top GEM/JR cards show published saved memberships until a current screen is
  available, with a label identifying the count's meaning. Standalone trial
  sheets request the small summary instead of downloading the full universe.

## Validation

- All 101 Render-release backend tests passed, including concurrent-reader,
  replacement-source, stale-version and compression-negotiation regressions.
- All 88 main-branch backend tests passed, including parity and pagination.
- Frontend typecheck, UI tests and a Next.js production build pass.
- Component regression covers third-page navigation, bounded rendering,
  whole-universe search and summary-based standalone counts.
- After the backend release, the production full workspace returned all
  11,775 programs, 11 saved GEM JR members and 6 saved GEM members in one
  observed browser request of approximately 5.2 seconds. This is a single
  measurement, not a cold-start guarantee or a p50/p95 benchmark.

## Release and source status

Verify the preview against the deployed backend before merging the frontend,
then verify the production pages and inspect runtime errors and memory.
The backend release is `070bee66dbacec850314a57c81073bb505f96e29`.
The published scan can legitimately remain `PARTIAL`; successful site loading
does not assert that every external evidence source has completed a live scan.
