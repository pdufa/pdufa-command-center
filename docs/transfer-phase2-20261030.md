# Transfer Phase 2 — October 30, 2026 UTC

Continuation of local checkpoint `38c8eb8e`; production main remains
`d327093520a3996d727c0811b4d171a381ab8afe`. No installation restart, schema
change, live database copy, credential change or scanner setting change occurred.

## Blocker disposition

| Blocker | Root cause / observed boundary | Fix attempted | Status | User action required |
| --- | --- | --- | --- | --- |
| Vercel 403 | Explicit team query is denied although the authenticated user's verified default team is PDUFA; the fetch helper separately fails reading deployment aliases at `/v2/deployments/{id}/aliases` | Used verified default-team context and exact project/deployment IDs; issued Vercel's team-consent link | PARTIALLY FIXED: production deployment/alias/SHA metadata verified; authenticated content helper blocked | Approve team grant for the existing connection; if still denied, authorize project and deployment-alias access in the Vercel connection |
| Credentials | Required variables exist in deployed scopes; managed runtime has no corresponding bindings. Presence does not prove matching values | Read metadata with `decrypt=false`; never retrieved secret values | REQUIRES USER ACTION for direct authenticated production tests | Securely bind the existing keys/password in the managed environment; do not rotate or paste values into chat |
| PostgreSQL | External allowlist is empty; hosted Render SQL connector cannot be allowlisted because it has no published stable egress IP. Runtime Render hosts also fail this environment's HTTP policy | Inspected internal service configuration, existing health workflow and bounded startup logs; left allowlist untouched | PARTIALLY FIXED: existing runner verified backend storage ready; direct SQL/identity/restore checks blocked | Prefer existing Render internal connection from an authorized execution environment, not public ingress; authorize the existing Render API hosts for managed HTTP probes |
| EPERM / stalled HTTP | Default command sandbox denies Node child-process/async HTTP operations; a minimal unrelated FastAPI app also stalled | Reproduced outside application logic; used supported per-command `network.enabled=true` sandbox permission, retaining proxy/TLS | FIXED for local tests and build | None |

The exact reason Vercel applies different grants to explicit and default scope
is not established. Do not describe API authorization failures as a website
Deployment Protection challenge. Project metadata reports password/SSO/IP
deployment protection disabled. No protection was changed.

## Concrete repairs

- `scripts/export_render_postgres.py`: create private `0600` dump files using
  exclusive creation; failed creation no longer deletes a competing backup.
- `tests/test_render_postgres_export.py`: exercise the competing-file race and
  verify restrictive permissions as well as existing credential/cleanup checks.
- `new-platform/migration/copy_checklists.py`: re-read the source in a fresh
  transaction before destination commit; concurrent source edits cause rollback
  instead of reporting source unchanged / cutover ready. Normalize aware
  timestamps to UTC and host case for safe comparisons.
- `new-platform/backend/tests/test_checklist_copy_safety.py`: real isolated local
  database transactions cover rollback, conflicting target preservation,
  idempotence, independent GEM JR/GEM settings, read-only comparison and canonical
  identity/time checks. These are not a live PostgreSQL migration rehearsal.
- `new-platform/backend/requirements.txt`: include the existing FDA PDF parser's
  `pypdf>=5.0,<7` runtime dependency, previously present only in root requirements.
  The real blank-PDF parser regression now requires that dependency instead of
  silently skipping it.

## Fresh verification

- Full backend after dependency repair: **1,000 passed, zero skips**, six existing
  dependency warnings. Before repair it was 999 passed with one missing-pypdf skip.
- Targeted scanner/clock/identity/archive/progress/export selection: **83 passed,
  59 subtests passed**. Separate migration/export selection: **13 passed**;
  these counts overlap and must not be added as unique tests.
- Existing complete frontend verification remains **391 passed**; no TSX changed.
- Production Next.js build: **passed**, including TypeScript and page generation,
  using the supported network-enabled command sandbox. Generated files restored.
- Real Chromium against the built local server, **1440×1000** desktop and
  **390×844** iPhone-sized viewport: tracker and prediction-pilot HTTP 200, no
  JavaScript page errors, four visible tracker bars contained in the viewport,
  six expandable pilot sections. This is local browser emulation, not physical
  iPhone or production browser certification; stock-price feeds were not tested.
- Local full backend exercises existing SCIENCE → OUTCOME → MAIN routes and the
  real PEAK source case with abstention. It does not validate FDA prediction
  performance. Main lacks a production three-class PASS/CRL/EXTENSION classifier;
  newer historical-label contracts remain in draft research work. Do not infer an
  extension from a missed deadline or turn unavailable evidence into a forecast.

## Live evidence and limits

Vercel default-context metadata confirms production deployment
`dpl_6h2uD9Hoofe5ojjzg9BM9cKtwJfy`, READY, target production, repository
`pdufa/pdufa-command-center`, main SHA `d3270935`, and the expected three aliases.
The newer latest project deployment is a research preview, not production.
Shell `git ls-remote` independently reconciled main to that same SHA. GitHub
repository metadata confirms pull/push permissions for this existing repository.

[Continuous health run 40988782709](https://github.com/pdufa/pdufa-command-center/actions/runs/40988782709)
completed successfully at 01:57:09 UTC. Inspected job logs record frontend HTTP
200 and backend HTTP 200. Its source workflow also requires backend service
identity, `status=ok` and `storage_ready=true` before success. This is observed
read-only service/storage readiness at that time, not independent SQL counts,
historical integrity, authenticated dashboard functionality or recovery proof.
The startup log's phrase "persistent database ready" alone is insufficient:
it is emitted before the connection check and tests URL configuration.

[Overnight run 40811143302](https://github.com/pdufa/pdufa-command-center/actions/runs/40811143302)
started October 29 at 03:15:46 UTC and completed successfully at 03:39:17 UTC.
Inspected jobs include sequential PIPELINE, GEM JR, GEM, financing/source checks,
scoring, result and archive stages. Saved clinical and source reports explicitly
remain **PARTIAL**; scoring is **REVIEW_REQUIRED**. Job success does not certify
full source coverage, WT automation, all Special Designations, or the next night's
execution. No new scanner was dispatched by this phase.

## Exact credential scopes observed (names only)

| Variable | Configured Vercel scope |
| --- | --- |
| `DASHBOARD_PASSWORD`, `SESSION_SIGNING_KEY`, `PDUFA_INTERNAL_API_KEY` | Production and general Preview |
| `PDUFA_API_BASE_URL`, `PDUFA_RESEARCH_API_BASE_URL` | Production and general Preview; one older branch has its own API URL override |
| `PDUFA_HOP_INTERNAL_API_KEY` | Production only |
| `CRON_SECRET`, `PDUFA_GITHUB_TOKEN` | Production only |
| `PDUFA_SCIENTIFIC_PREVIEW_READ_KEY`, `PDUFA_SCIENTIFIC_API_BASE_URL` | One existing scientific review branch only |

General previews fall back to `PDUFA_INTERNAL_API_KEY` for HOP; if the existing
HOP key differs, authenticated HOP preview testing requires the correct existing
HOP credential to be configured for that preview branch. This is a scope gap,
not evidence that production authentication is absent. No key was copied.

## Consolidated external actions

1. In the existing ChatGPT Vercel connection, approve PDUFA team access using the
   provider consent link supplied in the conversation (expires after ten minutes).
   Ensure the connection includes project `pdufa-new-dashboard` and permission
   to read its deployment aliases. If approval does not resolve the exact alias
   endpoint failure, inspect the connection grant rather than disabling protection.
2. In this task's managed environment configuration, authorize HTTPS access to
   `pdufa-new-dashboard.vercel.app`, `pdufa-new-api-staging.onrender.com` and
   `pdufa-hop-readonly-review.onrender.com`. Additional research-host access is
   needed only if verifying its separately configured research proxy. Keep proxy
   and TLS verification in place.
3. Bind existing `PDUFA_INTERNAL_API_KEY`, `PDUFA_HOP_INTERNAL_API_KEY` and
   `DASHBOARD_PASSWORD` through the secure managed secret UI, sourced from the
   existing authorized secret store. A real login generates its own session;
   production `SESSION_SIGNING_KEY` need not leave Vercel. Configure the existing
   HOP key for this preview branch if its fallback credential is different.
4. For database-level proof, use the existing Render service's internal database
   connection in an authorized Render shell: read-only identity/count checks,
   then separately authorized private dump and isolated restore. No external
   allowlist change is requested. If external SQL becomes necessary, first identify
   a trusted fixed egress IPv4 and request approval for only that `/32`; the hosted
   MCP connector currently cannot supply one.

The checklist-only copy script is not a complete migration of full-trial,
identity, assessment-history and other tables. Do not execute it as the full
system transfer. Existing backups must be restored and reconciled in isolation
before any live schema or cutover work. Transfer and validated prediction remain
incomplete; no completion percentages are assigned here.
