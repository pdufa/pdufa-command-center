# Stage 1 / Benchmark 1 verification

Final completion status: **FINAL CHECKS PENDING** (authenticated live-browser workflow PASS; explicit tab navigation, active-browser reconnect and post-run dossier checksum not yet demonstrated).

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

## Final-verification follow-up — October 30, 2026

Completion remains **INCOMPLETE**. The remaining credential blocker was rechecked
through the existing authorized workflow, with no application changes.

| Evidence | Actual result |
|---|---|
| Browser workflow / attempt | [41108170021, attempt 2](https://github.com/pdufa/pdufa-command-center/actions/runs/41108170021/attempts/2) |
| Job | [124247427050](https://github.com/pdufa/pdufa-command-center/actions/runs/41108170021/job/124247427050) |
| Attempt start | 2026-10-30T18:43:35Z |
| Credential preflight failed | 2026-10-30T18:43:41.4973652Z (11:43:41 a.m. PDT) |
| Exact diagnostic | `INCOMPLETE: missing GitHub Actions secret DASHBOARD_PASSWORD` |
| Browser login / authenticated frontend test | Not attempted; blocked before checkout/browser installation |
| Sanitized browser-result artifacts | None; no authenticated browser run occurred |

The connector does not expose GitHub secret-list metadata. The rerun's value-free
preflight directly established that `secrets.DASHBOARD_PASSWORD` resolved to an
empty/unavailable binding for this job. This does not distinguish an absent
repository secret from an organization secret without repository access or an
environment-only secret. No secret value was requested, retrieved or generated.

### Minimum secure credential setup

1. The authorized application owner obtains the **existing normal production
   dashboard login password** from their approved credential store. It must match
   the deployed `pdufa-new-dashboard` production application's
   `DASHBOARD_PASSWORD`. Use the application login password, not the backend
   internal API key or session signing key.
2. Open [repository Actions secrets](https://github.com/pdufa/pdufa-command-center/settings/secrets/actions):
   **Settings → Secrets and variables → Actions → New repository secret**.
3. Enter the exact name **`DASHBOARD_PASSWORD`** and save that existing credential
   directly in GitHub's secret field. Do not paste it in chat, source, workflow
   inputs, logs or this report. An approved organization Actions secret with access
   granted to this repository is also sufficient. An environment-only secret is
   unavailable because this workflow has no environment binding.
4. Open [Stage 1 authorized live browser verification](https://github.com/pdufa/pdufa-command-center/actions/workflows/stage1-live-browser.yml),
   select **Run workflow**, choose **main**, and run. Alternatively, rerun the
   failed job after the secret is available.
5. Inspect the actual job outcome and sanitized verification artifact before
   changing this report's status. A successful credential preflight alone is
   insufficient.

### Deployment and evidence recheck

Render deployment `dep-dbie5duk1f9s73ej4uhg` still reports LIVE for exact mirror
`92bb782a24aa8a57aa581da711541e4538ed1a84`. At the 18:43 UTC check, the production Vercel alias
resolved to READY deployment `dpl_GN81oSc6WdbE4VJvE1G5azjYnV2g`, build URL
https://pdufa-new-dashboard-h0dt52hx5-pdufa.vercel.app, commit
`64f7dcb6b73c38f8c212f2898c588398d868cee8`.
Comparison with tested main `08033fdb` confirms no backend/frontend application
code changes; the intervening files are this report, the browser workflow/script,
and the existing automated morning-results data update. No new deployment was
requested in this follow-up.

The actual deployed backend marker was reread from Render logs. It retains the
documented PASS for real NCT00116805, saved dossier verification, 70 persisted and
received events, two HTTP connections, cursor resume without duplicates, matching
reload snapshots, and an unchanged original dossier. Its execution timestamp is
18:33:16 UTC; rereading it is not represented as a new execution.

The live browser script checks normal authentication, live SSE, visible bottom-up
population/loading, persisted ordering, displayed values against authenticated
snapshots, and reload without a duplicate run. Forced frontend reconnect/error
cases are exercised by regression tests; the deployed backend independently
exercised a two-connection cursor resume. Those are separate evidence sources,
not claims that blocked browser checks executed.

Only verification documentation is changed in this follow-up. All protected
restrictions, FS/FA associations, scoring, schedules and trading controls remain
unchanged.

### Fresh regression execution

All four suites actually reran against the unchanged tested application revisions.
The backend jobs executed in attempt 2; frontend jobs executed in attempt 3 after
GitHub finished the backend attempts. Inherited successful job entries are not
counted as new executions.

| Suite | Fresh result | Test/build completion UTC | Executed job |
|---|---|---|---|
| Main backend, 08033fdb | **1,024 passed, 1 skipped**, 7 warnings, 11.39s | 2026-10-30T18:50:40.9058028Z | [124250528572](https://github.com/pdufa/pdufa-command-center/actions/runs/41107498655/job/124250528572) |
| Main frontend, 08033fdb | **402 passed, 0 failed, 0 skipped**; TypeScript and production build passed | tests 18:51:34Z; build 18:51:47Z | [124250915531](https://github.com/pdufa/pdufa-command-center/actions/runs/41107498655/job/124250915531) |
| Render mirror backend, 92bb782a | **309 passed**, 6 warnings, 6.12s | 2026-10-30T18:50:32.9372122Z | [124250540225](https://github.com/pdufa/pdufa-command-center/actions/runs/41107506125/job/124250540225) |
| Render mirror frontend, 92bb782a | **39 passed, 0 failed, 0 skipped**; TypeScript and production build passed | tests 18:51:10Z; build 18:51:21Z | [124250868782](https://github.com/pdufa/pdufa-command-center/actions/runs/41107506125/job/124250868782) |

The main workflow's attempt 3 finished SUCCESS at
`2026-10-30T18:51:51Z`; mirror attempt 3 finished SUCCESS at
`2026-10-30T18:51:23Z`. The existing main-backend skip is still reported as a skip,
not a pass. No application code was rebuilt or rewritten to work around the
credential blocker.

**Final benchmark result: INCOMPLETE — authorization credential unavailable to
the live-browser job.** Backend live execution and automated regressions pass;
deployed authenticated browser authentication, population and reload remain
pending. Only after the authorized workflow succeeds and its evidence is checked
may Stage 1 be marked VERIFIED COMPLETE.

## Benchmark 1 final-completion credential check — 2026-10-30

Status remains **INCOMPLETE**. No application code changed and none of the
previously passing regression suites was rerun during this check.

- Starting report/application revision: `d6b5323bff49ca0d7ad60ad0b5b600797d9a0da9`.
- Authorized browser workflow: [41108170021, attempt 3](https://github.com/pdufa/pdufa-command-center/actions/runs/41108170021/attempts/3).
- Actual job: [124254771378](https://github.com/pdufa/pdufa-command-center/actions/runs/41108170021/job/124254771378).
- Credential preflight executed at **2026-10-30T19:00:23.5219863Z** and exited 1:
  `INCOMPLETE: missing GitHub Actions secret DASHBOARD_PASSWORD`.
- `secrets.DASHBOARD_PASSWORD` was empty/unavailable to that job. The existing
  workflow references the correct exact name. It declares no GitHub environment,
  so an environment-only secret cannot supply this binding. Repository secrets
  or organization secrets granting this repository access are supported.
- The managed execution environment also has no ready credential/session binding.
  Secret values were not requested, retrieved, generated or guessed.
- Vercel production alias was inspected: READY deployment
  `dpl_CFvzLkWuFjQzKzYqNYXdyDpkFiiF`, commit `d6b5323b`,
  https://pdufa-new-dashboard-ll9th5wqx-pdufa.vercel.app .
- Render deployment `dep-dbie5duk1f9s73ej4uhg` remains LIVE for `92bb782a`.

**Precise user action:** In repository Settings → Secrets and variables → Actions,
create repository secret **`DASHBOARD_PASSWORD`** using the **existing production
dashboard login password** supplied securely by the authorized owner from their
approved credential store. It must match the production dashboard's configured
login password. Do not use the session signing key or backend internal API key.
Do not paste the credential into chat. An approved organization secret with this
repository selected is also sufficient. Then rerun **Stage 1 authorized live
browser verification**, branch **main**, using the workflow link above.

No browser login, PREDICTION-tab interaction, live frontend population, refresh or
frontend reconnect check executed in this attempt. Source inspection shows
application login uses same-origin POST /api/auth, a successful JSON response and
an HttpOnly cookie followed by client rendering; an HTTP redirect is not required
by that application flow. Actual deployed authentication/redirect behavior remains
unverified because the job stopped before login.

The existing browser script also does not explicitly select the PREDICTION tab or
force a frontend reconnect. Those requested live checks must be added/executed and
their results reviewed after authorized access is available; existing backend
resume and regression results must not be relabeled as those browser observations.

All prior NCT00116805/backend persistence/dossier preservation and regression
evidence remains intact. All protected restrictions, associations, scientific
methodology, schedules and trading controls remain unchanged. Only this report was
updated. Stage 1 may be marked VERIFIED COMPLETE only after every mandatory
authenticated browser check actually passes.

## Final authorization recheck — 2026-10-30T19:08:10Z

**Completion gate: FAIL. Stage 1 status: INCOMPLETE (credential blocked).**

The browser-only [workflow run 41108170021, attempt 4](https://github.com/pdufa/pdufa-command-center/actions/runs/41108170021/attempts/4)
actually completed FAILURE at 2026-10-30T19:08:15Z. Its
[job 124258904087](https://github.com/pdufa/pdufa-command-center/actions/runs/41108170021/job/124258904087)
failed at 2026-10-30T19:08:10.8508948Z with
`INCOMPLETE: missing GitHub Actions secret DASHBOARD_PASSWORD`.
The job exited 1 before checkout, browser installation or login.

Starting repository revision was `df13425ac3c127880d591ceec8da096f918af067`.
The rerun uses the unchanged main-branch browser workflow/script revision
`144f8c854b05918a2459500c67084037e6c6a07b`. The selected NCT remains
`NCT00116805`; no new authenticated trial run was created.

The current workflow correctly references `secrets.DASHBOARD_PASSWORD`.
The GitHub connector explicitly excludes secrets APIs and offers no secret-name
listing tool. Therefore repository-level secret existence cannot be listed with
the available connection. The executed preflight establishes that the binding is
empty/unavailable to this job, not whether a secret exists elsewhere. The workflow
has no environment binding; an environment-only secret will not reach it.

**Required manual configuration:** The authorized owner must obtain the existing
production dashboard login password from their approved credential store, then
open [Settings → Secrets and variables → Actions](https://github.com/pdufa/pdufa-command-center/settings/secrets/actions),
choose **New repository secret**, and save it with exact name
**`DASHBOARD_PASSWORD`**. If that repository secret already exists, the owner
should correct its availability/configuration there using the existing password;
do not replace the application's password. An organization secret must grant this
repository access. Do not paste credentials into chat.

Then run [Stage 1 authorized live browser verification](https://github.com/pdufa/pdufa-command-center/actions/workflows/stage1-live-browser.yml)
on **main** and inspect its actual assertions and sanitized results. A dispatch or
successful preflight alone is insufficient.

Authentication, live frontend streaming/population, persistence after browser
refresh, browser reconnection/deduplication and saved-dossier browser verification
were **NOT EXECUTED** in this attempt. Previous successful backend/dossier and
regression evidence remains unchanged. No successful tests were repeated, no
application code or production data changed, and all protected functionality and
trading controls remain intact.


## Authenticated live-browser success — October 30, 2026, 19:37 UTC

**Observed GitHub Actions result: PASS (job 124272359051, workflow run 41108170021).**

- The repository-secret preflight succeeded; the existing authorized dashboard credential was supplied to the runner without exposing its value.
- Playwright installed and executed `node scripts/stage1_live_browser.cjs` against the deployed dashboard.
- The actual job log emitted `Stage 1 live browser: PASS` at 2026-10-30T19:37:41Z, and the job concluded success.
- The sanitized verification artifact was uploaded successfully: `stage1-live-browser-sanitized-result`, artifact ID `13006571443` (1103 bytes).
- Workflow: https://github.com/pdufa/pdufa-command-center/actions/runs/41108170021
- Artifact: https://github.com/pdufa/pdufa-command-center/actions/runs/41108170021/artifacts/13006571443

The checked-in browser script requires successful normal login, an authenticated live NCT00116805 processing run, actual SSE responses, loading/verified observations, ordered persisted events, source citation/hash equality, bottom-up parent dependencies, browser display-to-snapshot equality, and a browser reload restoring the same run without an extra POST. It asserts that MAIN stays ABSTAIN. These assertions are supported by the script's PASS exit and the successful job; the sanitized artifact can supply per-check detail.

**Completion gate: NOT YET FORMALLY CLOSED.** The currently checked-in browser script does not explicitly navigate to the PREDICTION tab or deliberately interrupt and resume an *active frontend browser SSE connection*. Its reload test restores an already completed run; the separate backend test previously verified Last-Event-ID reconnect. The live browser script also does not freshly re-read and compare the original saved dossier checksum *after* this run. These three explicit follow-up requirements must be implemented and observed before declaring the expanded Benchmark 1 acceptance criteria VERIFIED COMPLETE. Do not relabel the backend reconnect as a browser reconnect or an earlier dossier hash as a post-run hash.

Protected Pipeline/GEM JR/GEM/WT restrictions, FS/FA presets, scientific scoring, scans, and trading controls remain outside the verification scope. No trading authorization is implied.
