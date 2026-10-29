# iPhone operator workflow for staging reconciliation

Status: **NOT READY / ABSTAIN**. The approved inventory retrieval and aggregate
reconciliation are complete. Independent scientific and program eligibility
verification remain incomplete.

## Successful reconciliation (2026-10-29)

[Run 40969177461](https://github.com/pdufa/pdufa-command-center/actions/runs/40969177461)
at research commit `07968fec1182168f60de9ccf735710bca96a0b77` succeeded and
uploaded its artifact. Actual results: **11,812 records, 119 pages, 11,812 unique
permanent and source IDs, zero duplicates and zero missing records/IDs**.
There are **114 market-cap source claims, zero qualifying FDA target claims,
zero candidates passing research scope and 11,812 blocked records**. Source date
is `2026-10-29` with explicit Los Angeles calendar-day precision. The original
ZIP's hash matches GitHub's digest; its sole JSON member and audit manifest are
preserved locally in the repository before the one-day artifact expiry.

See the [complete report and limitations](PIPELINE_RECONCILIATION_20261029.md).
Actual eligibility remains unestablished; zero scientific predictions were
generated. The prior one-run staging authorization has been exercised. No
additional run is needed for this completed inventory reconciliation.

## Earlier verified state (2026-10-29 22:32 UTC)

Research HEAD `59fb6d8aa4afb08702c7451eec79f942834a6cdf` was fetched and all
14 associated PR workflows were independently confirmed successful. The
completed calendar-date compatibility repair was preserved and **141 relevant
regression tests passed locally**, with zero failures.

The newest manual runs, [40965784414](https://github.com/pdufa/pdufa-command-center/actions/runs/40965784414)
and [40965773373](https://github.com/pdufa/pdufa-command-center/actions/runs/40965773373),
selected `main` and were skipped. No manual retrieval run at `59fb6d8` was found.
The available GitHub connector exposes old-job retries and run inspection, but
no new workflow-dispatch operation. Retrying an old job retains its old commit;
it cannot execute this repair. A new Safari dispatch on the research branch is
the remaining operator action. Approval is already provided by the continuation
directive; no replacement credential or production deployment is needed.

[Run 40955794298](https://github.com/pdufa/pdufa-command-center/actions/runs/40955794298)
at the preceding `45b0abb1` authenticated successfully and returned the summary
and first page, then stopped with `aware workspace source timestamp required`.
No complete report was produced. The backend's `asOf` is a Los Angeles calendar
date, and the completed repair checks it as such without inventing midnight or
a timestamp offset. The original precise timestamp path still enforces bounded
age and rejects future timestamps. An accepted calendar date proves a matching
reported business day, not an exact elapsed-hour source age or original source
publication time.

Workspace version, source date value, complete row/page counts, duplicate counts,
source-evidence counts and verified eligibility remain **unmeasured** until a
successful report is inspected. Earlier registry (11,636) and candidate-assessment
(11,812) observations are different populations, not substitute Pipeline totals.

## Downstream report repair after the verified calendar-date baseline

The completed `59fb6d8` source-date validation is unchanged. Inspection found
that the separate cap field mapper still expected an offset timestamp, silently
counting every calendar-snapshot cap claim as unsupported. Calendar snapshots
now use the actual aware caller observation clock for cap-claim freshness. A
missing observation remains conservative, future claims are withheld, and legacy
offset snapshots retain their original source cutoff. No source publication
timestamp is invented and no listing/restriction gate is upgraded.

The aggregate artifact now retains `source_time_precision`, `freshness_basis`,
`observation_timestamp`, and the cap freshness reference timestamp/basis. A
current Los Angeles calendar date is explicitly distinct from bounded elapsed
timestamp age. These clocks do not independently verify publication or trial,
regulatory or market evidence.

After complete pagination and global identity checks, the report also records
`workspace_total`, `unique_program_ids`, `unique_source_program_ids`,
`source_program_ids_missing`, both duplicate-ID counts and `missing_records`.
Zero duplicate counts are emitted only after the checks succeed; failure still
produces no success artifact. Missing source IDs stay visible. Missing records
means missing relative to the API-declared Pipeline total, not relative to the
separate registry/assessment populations. Raw IDs and individual rows remain
excluded from the aggregate artifact.

Validation: **148 preliminary/workflow/bridge tests passed**, zero failures;
broader research selection **903 passed plus 43 subtests**, one genuine external
TSA fixture skipped, zero failures. Independent review reran all 148 relevant
tests and found no blocking issues. These synthetic checks do not supply actual
Pipeline counts or scientific validation.

## Observed execution results (2026-10-29)

[Manual run #10](https://github.com/pdufa/pdufa-command-center/actions/runs/40942416784)
used research commit `f71a7baba4d89388e63f065dc08363b64b236a46`.

- Attempt 1 stopped with `PDUFA_INTERNAL_API_KEY is required` before making any
  staging request. It caused no staging database writes.
- After the operator reported saving the existing key as the staging repository
  secret, attempt 2 passed local credential validation and issued the initial
  `/api/workspace/summary` request. Waiting for its response raised a
  `TimeoutError` at the original 20-second client deadline. No page was requested,
  and no reconciliation artifact was produced. Server authentication, response
  schema and server-side completion remain unconfirmed. A client timeout does
  not prove that server-side processing stopped.
- Render's service metadata identifies the intended staging service. Queries
  for matching summary logs and service events returned no entries for this
  attempt; they do not establish the cause of the timeout or verify authentication.

The existing workflow now gives each request a bounded 120-second timeout while
retaining its ten-minute overall job limit. The client reports timeouts without
tracebacks, response bodies or credentials, exits without producing a partial
success report, and does not automatically retry. This accommodates slower
responses without assuming a cold start caused the observed failure. Re-running
the old failed job still uses its old commit and 20-second deadline: a new manual
dispatch on the research branch is needed to use the repair.

Timeout-repair verification: **137 preliminary/workflow/bridge tests passed**,
zero failures. Broader research selection: **887 passed, 43 subtests passed,
six skipped**, zero failures. Independent review reran **75 HTTP/workflow
tests** and found no blocking issues. These checks use synthetic transport;
they do not establish a successful live response or independently verified
program eligibility.

## What is supported

The current ChatGPT execution tools provide no secure human terminal-input
control or secret-binding control. Do not enter a key in chat. The existing
Render staging Free service has no Dashboard Shell/SSH. Neither is proposed as
an iPhone terminal solution.

Use Safari and GitHub Actions instead. The workflow filename
`isolated-readiness-smoke.yml` already exists with `workflow_dispatch` on the
repository's default branch. Selecting the research branch runs that branch's
definition, including the added staging job. No main merge, backend deployment,
Codespace, paid Render upgrade or new credential is required.

The original isolated-review job and its credential remain unchanged. The new
job only runs on manual dispatch of
`research/fda-decision-label-gate-20261028`. It reuses the existing authenticated
Python client and the fixed staging origin. It never automatically runs on
push, PR or schedule.

## Phone steps

The existing secret already authenticated in run `40955794298`. Steps 1–2 are
initial setup instructions only; do not repeat them or replace a working key.

1. Open the [Render staging service](https://dashboard.render.com/web/srv-db976hfbtjjs73bb98fg)
   in Safari. Tap **Environment** and check **Environment Variables** (or a
   **Linked Environment Group**) for `PDUFA_INTERNAL_API_KEY`. This is the
   existing server credential's expected location. The agent's connector cannot
   confirm its presence or retrieve it securely. If absent, stop; do not rotate
   or create a replacement without separate authorization.
2. Open [GitHub Actions secrets](https://github.com/pdufa/pdufa-command-center/settings/secrets/actions)
   in Safari. Tap **New repository secret**. Enter the name
   `PDUFA_STAGING_INTERNAL_API_KEY`. Enter the **existing staging value only in
   GitHub's protected Secret field**, then tap **Add secret**. Do not put it in
   chat, workflow inputs, repository files, logs or screenshots. Do not reuse the
   `isolated-alpaca-review` key. This stores the existing key for the approved
   runner; it does not change or rotate Render's key.
3. Confirm explicit approval covers the intended staging reconciliation run;
   the current continuation directive provides it. A summary
   or page GET can refresh published-source caches. Page preparation can insert
   missing exact program identities into staging `program_identity`, including
   keys used by Pipeline and GEM history. Existing IDs are read unchanged;
   source-key uniqueness and conflict-safe inserts prevent duplicate stored
   identities. Sequence gaps can occur under concurrent insert attempts. The
   path does not update restrictions, FS/FA associations, scientific assessments
   or trading settings. Staging database state/constraints remain unprobed.
4. **Only after approval**, open [the manual workflow](https://github.com/pdufa/pdufa-command-center/actions/workflows/isolated-readiness-smoke.yml).
   Tap **Run workflow**, then the small gray **main ▼** button inside its popup.
   In the **Switch branches/tags** search field, type **fda-decision** and select
   **research/fda-decision-label-gate-20261028**. Confirm that the selected branch
   has replaced **main**, then tap the lower green **Run workflow** once.
   The page retains the registered name **Isolated PDUFA Readiness Smoke**;
   the research-branch job is **Authorized staging Pipeline reconciliation**.
   Do not choose main or the separate isolated-review branch.
5. Open the completed run. A successful **staging-pipeline-reconciliation**
   artifact contains only `pdufa-pipeline-reconciliation.json` and expires after
   one day. The agent can inspect that run/report through GitHub without
   receiving the secret. A missing key, denied authentication, source drift or
   incomplete pagination fails visibly without a successful report.

Repository administration/Actions permissions are needed for these GitHub
buttons. If unavailable, an authorized repository operator must perform the same
steps; granting database access publicly is not an alternative.

## What executes

The manually selected job checks out the research branch without retaining Git
credentials, injects only `secrets.PDUFA_STAGING_INTERNAL_API_KEY` into the
client's process environment, and calls the existing summary/pages/summary
runner with explicit identity-allocation authorization. No secret is printed or
written to an artifact. The job has read-only repository permissions, a bounded
timeout, serialized runs and no deployment command.

The report reconciles counts, page/version/timestamp consistency, duplicates,
source-presence counts and blocked screening records. Raw individual program
records and credentials are not uploaded. Report hashes establish local JSON
integrity, not independent FDA evidence. The previously observed registry and
assessment counts are separate populations; no equality is assumed. No verified
eligibility counts or preliminary outcomes are inferred before actual data and
evidence review.

Local verification: **112 preliminary/workflow tests passed**; combined
research suites **958 passed plus 298 subtests**, one external fixture skipped,
zero failures. Independent workflow/HTTP review passed 50 tests with no material
findings. These are software checks, not a live staging authentication result.
Repeated manual dispatches are serialized, not deduplicated: approve and start
exactly one run.

## Verified interface references

- [GitHub manual workflow and branch selection](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)
- [GitHub workflow_dispatch ref/default-branch requirements](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch)
- [GitHub Actions secret form](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)
- [Render Environment settings](https://render.com/docs/configure-environment-variables)
- [Render Free service limitations](https://render.com/docs/free)
