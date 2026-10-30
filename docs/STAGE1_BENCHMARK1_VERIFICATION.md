# Stage 1 / Benchmark 1 verification

Final completion status: **INCOMPLETE**.

The authenticated backend live-streaming path is verified. The mandatory deployed
frontend/browser population and reload checks remain unverified because the actual
live-browser workflow stopped at credential preflight. Deployment success alone
is not treated as completion.

## Commits and deployments

| Item | Identifier / result |
|---|---|
| Main application implementation | `e9b1cfa2b97110b20c4dea4924c98793ad89253a` |
| Main tested revision, including regression compatibility fixes | `08033fdbd13da662aca0a387cec0959f96e823a8` |
| Render deployment mirror | `92bb782a24aa8a57aa581da711541e4538ed1a84` |
| Render service | `srv-db976hfbtjjs73bb98fg` |
| Render deployment | `dep-dbie5duk1f9s73ej4uhg` — LIVE |
| Production Vercel deployment inspected | `dpl_Gx1rAo4ChWrfnrJNUMd5oXVa2LMC` — READY, exact main revision `08033fdb` |
| Production Vercel build URL | https://pdufa-new-dashboard-a05v2puzx-pdufa.vercel.app |
| Production alias | https://pdufa-new-dashboard.vercel.app |
| Authorized browser-check workflow commit | `144f8c854b05918a2459500c67084037e6c6a07b` |

The implementation is on main. The existing Render service remains configured for
new-platform-bootstrap; only matching Stage 1 files were mirrored, with additive
integration into that branch's own main.py/page.tsx. There was no branch-wide merge
or rollback of unrelated features. The same nct_live_stream.py and frontend stream
implementation are used on both branches. Existing branch-specific functionality
and an automated morning-report data commit were preserved.

## Existing implementation inspected

The previous /api/prediction-events/NCT... endpoint streamed saved evidence only.
It did not retrieve live data or persist incremental processing. That existing
replay and its ABSTAIN safeguards remain unchanged.

Stage 1 adds authenticated POST /api/nct-stream/NCT.../runs, run snapshot GET, and
SSE events GET. The frontend uses the existing HttpOnly session, with same-origin
POST validation; the backend uses the existing internal credential/storage guard.
A run requires an existing saved dossier with matching NCT and canonical checksum.
No authentication bypass, new production credential, IP-access change or public
source-data endpoint was introduced.

## Selected real trial and saved dossier

- Selected NCT ID: **NCT00116805**.
- Saved dossier identifier: `scientific-candidate-review-v1:44136fa355b3678a/NCT00116805`.
- Original dossier SHA-256: `c7c1d08244597084152238853c3d8357b892218aee1c48db97e83f63216c54de`.
- Actual persistent database: `pdufa_new`; saved dossier table:
  `scientific_candidate_dossiers`, from the persisted scientific-review ledger.
- New live processing run: `5f1d75ec-305e-4e9e-9fe3-46b7d2f55296`.
- Authoritative live source: https://clinicaltrials.gov/api/v2/studies/NCT00116805 .
- Received source-body SHA-256: `ef81d9753637f67ca5c1ec94ae5af91f14aedd06888d9b04168025de5b299e1b`.
- Existing dossier identity/hash were validated before processing. The source's
  internal NCT matched, and the live sponsor/product/indication/phase facts were
  checked against that saved dossier. The original dossier hash remained unchanged.

The runtime verification retrieved genuine ClinicalTrials.gov JSON. Synthetic
fixtures were used only in automated tests, never as live verification evidence.

## Actual deployed backend execution

Verification timestamp: `2026-10-30T18:33:16.990593+00:00` (**October 30, 2026, 11:33:16 a.m. PDT**).
Runtime marker: `PDUFA_STAGE1_BACKEND_VERIFICATION`; actual result: **PASS**.

| Mandatory backend check | Observed result |
|---|---|
| Request without internal credential rejected | `true` |
| Accepted authenticated request / exact saved NCT | PASS |
| Live authoritative retrieval and normalization | PASS |
| Evidence URL, raw source hash and timestamp preserved | PASS |
| SSE events received over actual HTTP | **70** |
| Events persisted before delivery | **70** persisted; ordered snapshots match received events |
| First events arrived while work still active | `true` |
| First event received | `2026-10-30T18:33:07.374811+00:00` |
| Terminal event received | `2026-10-30T18:33:16.757145+00:00` |
| Deliberate disconnect and Last-Event-ID resume | **2** HTTP connections; PASS |
| Cursor resume without duplicate event sequences | `true` |
| Snapshot re-read/reload identical to persisted events | `true` |
| Original saved dossier unchanged | `true` |
| Deployed authenticated frontend browser flow | **NOT VERIFIED** |

The first-to-terminal delivery interval was approximately 9.4 seconds. Events were
received before processing completed, rather than buffered until the whole run ended.
The reconnect test deliberately closed the first connection after three events,
then resumed from its actual persisted cursor.

Only new stream metadata tables are written: nct_stream_runs, nct_stream_sources,
and nct_stream_events. Sources/events are append-only; request and event keys are
unique. Each normalized event commits before stream delivery. Database locks
prevent overlapping work, saved source integrity is rechecked on recovery, and
interrupted runs recover without demoting completed evidence. Errors end loading
states and retain the original saved dossier. No tokens, passwords or protected
trial values are printed to logs; diagnostic output contains only the requested
NCT/run/dossier IDs, hashes, timestamps, counts and verification booleans.

## Frontend behavior implemented and regression-tested

- Smallest leaves populate first; persisted dependency events update their parents.
- PENDING → LOADING → VERIFIED / FAILED / INSUFFICIENT_EVIDENCE.
- Only actual LOADING work shows the accessible rotating indicator.
- Verified leaves and citations remain visible while other work continues.
- Stream IDs, strict sequence checks and cross-NCT/run guards prevent duplicate or
  stale updates. Incomplete EOF reconnects with the saved cursor, up to three times.
- Reload stores only an NCT/run pointer, then reads persisted events from the server.
- MAIN remains ABSTAIN. These are evidence-collection states, not scientific scores.

These client behaviors passed automated React/parser/proxy tests. They have **not**
been represented as observed live browser behavior.

## Actual regression results and execution times

| Suite / revision | Actual result | UTC completion timestamp |
|---|---|---|
| Full main backend, 08033fdb | **1,024 passed, 1 skipped** | 2026-10-30T18:31:01Z |
| Full main frontend | **402 passed, 0 failed**, TypeScript and production build passed | 2026-10-30T18:30:49Z |
| Render mirror backend, 92bb782a | **309 passed** | 2026-10-30T18:30:56Z |
| Render mirror frontend | **39 passed, 0 failed**, TypeScript and production build passed | 2026-10-30T18:30:47Z |

Main CI: https://github.com/pdufa/pdufa-command-center/actions/runs/41107498655 .
Mirror CI: https://github.com/pdufa/pdufa-command-center/actions/runs/41107506125 .
The new actual HTTP auth/stream TestClient case executed in CI. One unrelated
existing main-backend test remains skipped; skipped tests are not reported as passed.
Focused local execution had29 backend passes and a local-only HTTP transport skip;
CI additionally executed the HTTP case and a new nested-route regression. Eleven
focused frontend tests passed, including real React reconnect/reload/cross-NCT
cancellation, parser byte splits, source proof validation, auth/origin rejection,
rendering and loading indicators.

Initial CI caught an older route-inspection test incompatible with FastAPI's
included-router wrapper, and a mirror page test assuming direct panel adjacency.
Both were corrected without weakening assertions or changing production layout:
recursive route inspection still checks every removed ZIP endpoint, and the page
test checks presence/order of all preserved panels. Full reruns above passed.

## Exact remaining blocker and live-browser attempt

Actual authorized browser workflow:
https://github.com/pdufa/pdufa-command-center/actions/runs/41108170021 .
It executed on October 30 at 18:35:08 UTC and failed its first credential preflight:

`INCOMPLETE: missing GitHub Actions secret DASHBOARD_PASSWORD`

No browser dependency was installed and no login was attempted after this failure.
There was no password guessing, session forging, credential retrieval or provider
protection bypass. The workflow/script remain ready to run a legitimate normal-form
login, live rendering/animation, source/snapshot equality, and reload persistence
check once an authorized credential binding is available.

Required next action: configure an authorized application test credential through
GitHub's secret manager as DASHBOARD_PASSWORD, or provide an already authorized
browser session, then rerun Stage1 authorized live browser verification. Do not copy
credentials into source, reports, logs, prompts or artifacts. If credentials are
provided, the existing workflow can be rerun from GitHub Actions without changing
application code. Only after every mandatory browser check passes may this report
be changed to VERIFIED COMPLETE.

## Runtime health and protection boundaries

Render reported LIVE for the exact mirror SHA. Production Vercel deployment metadata
reported READY for the exact tested main SHA. The actual backend runtime test passed;
no Stage1 worker/startup failure logs or server failure/restart events were observed
in the post-deployment check. Provider deployment status is supporting evidence only.

PIPELINE, GEMJR, GEM and WT restrictions, original FS/FA associations, scientific
scoring rules, OUTCOME methodology, MAIN aggregation, scheduled scans, scan history,
archive payloads/manifests and trading safeguards were not changed. Scientific
significance/clinical meaningfulness remain unadjudicated, regulatory fields are
not inferred from trial phase, and all prediction/trading decisions remain ABSTAIN.
This Stage1 benchmark executes no scientific-framework assessments and authorizes
no trading activity.
