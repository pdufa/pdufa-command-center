# Authenticated Pipeline retrieval verification

Prediction status: **NOT READY / ABSTAIN**.

For iPhone-only operation, use the [Safari/GitHub Actions handoff](IPHONE_STAGING_RECONCILIATION.md).
It reuses the existing registered manual workflow and client with a distinct
staging secret. One reconciliation run was explicitly approved and attempted;
the current result is documented below. Previous GO instructions alone do not
authorize staging identity allocation.

## Latest verified state: authentication works, new dispatch pending

Fetched research HEAD `59fb6d8aa4afb08702c7451eec79f942834a6cdf`; all 14 PR
workflows passed. Its completed source-calendar-date repair is preserved. The
relevant local suite passed **141 tests**, zero failures.

[Run 40955794298](https://github.com/pdufa/pdufa-command-center/actions/runs/40955794298)
at `45b0abb1` authenticated and received the initial summary and first page,
then failed the original aware-timestamp check. No full reconciliation artifact
was produced. The backend intentionally reports `asOf` as a Los Angeles date.
The completed adapter repair validates that date against the current Los Angeles
day and preserves the raw value; it does not manufacture a time or offset. The
legacy offset-timestamp path still enforces its exact bounded age. Calendar-day
agreement must not be represented as an exact elapsed-hour freshness result or
independent publication-time verification.

The two newest manual runs, `40965784414` and `40965773373`, selected `main` and
were skipped. No manual run at `59fb6d8` was found. The connected GitHub tool can
inspect and retry jobs but cannot dispatch a new workflow; retrying an older job
retains the older commit. The operator's continuation authorizes the existing
staging scope, but a new manual research-branch dispatch is still required. The
current Cloud shell has neither the staging credential nor an allowed staging
origin; no attempt to bypass those restrictions was made. No production or
authentication configuration was changed.

All complete-inventory reconciliation metrics remain unmeasured until a new
report is available. A source-presence count is not independently verified
listing, restriction eligibility, FDA evidence or predictive accuracy.

## Downstream cap counts and exported audit metadata

The existing `59fb6d8` source-date check is preserved. Calendar snapshots now use
the actual aware retrieval observation clock for cap-claim freshness, avoiding
the field mapper's previous all-zero count when given a date-only cutoff. Without
that observation, cap claims remain unverified. Offset snapshots retain the
original source timestamp cutoff, including rejection of later cap claims.

The safe aggregate exports source precision, explicit freshness basis, actual
observation timestamp and the separately identified cap-reference clock. It
also exports declared total, unique permanent/source ID counts, missing source
IDs, duplicate counts and missing records after complete pagination/validation.
These fields do not expose raw IDs, rows or credentials. Zero duplicates in a
successful report follows global checks; a failed run yields no partial success
artifact. Listing, restriction and scientific readiness remain unverified.

Validation: **148 relevant tests passed**, zero failures; broader research
selection **903 passed plus 43 subtests**, one genuine external TSA fixture
skipped, zero failures. Independent review found no blocking issues and reran
148 relevant tests successfully. No production/backend configuration or source
calendar validation was changed.

## Earlier execution result: first response timed out

Research-branch [run 40942416784](https://github.com/pdufa/pdufa-command-center/actions/runs/40942416784)
ran at `f71a7baba4d89388e63f065dc08363b64b236a46`. Attempt 1 failed local key
validation before contacting staging. After the operator reported saving the
existing staging secret, attempt 2 passed local key validation, then its first
summary request timed out waiting for a response after 20 seconds. No pages or
complete records were received, and no aggregate artifact was created.
Authentication and any continued server-side work remain unconfirmed; a timeout
does not cancel backend processing. Staging log/event queries returned no
matching entries and do not identify the cause. No production change or deploy
was performed.

The repair adds a bounded `--request-timeout` option (default 20 seconds, maximum
120), uses 120 seconds in the existing manual workflow, and catches request/body
timeouts without leaking exception text or issuing another request. The job
still has a ten-minute overall limit and the client writes a report only after
complete reconciliation. A new research-branch manual dispatch is required to
use the new commit; rerunning the old job cannot pick up this repair. These
software changes do not establish successful staging authentication, Pipeline
counts or independently verified eligibility.

Timeout repair: **137 relevant regression tests passed**; broader research
selection **887 passed plus 43 subtests, six skipped, zero failures**.
Independent HTTP/workflow review passed **75 tests**, finding no blocking issues.
No new backend code, database schema or production configuration was changed.

## Authorization guard follow-up

The HTTP factories, screening API, diagnostics API and CLI now require explicit
operator authorization for possible staging identity allocation. The Python
keyword is `allow_identity_allocation=True`; the CLI flag is
`--allow-staging-identity-allocation`. Omission, false, null, strings and integer
aliases fail before constructing a client or making any request. This records
an operator's approval; it does not authenticate the operator or replace the
backend's existing key authentication.

One reconciliation run permitting the existing insert-only allocation of missing
program IDs was explicitly authorized and attempted through GitHub Actions.
The current result above supersedes the earlier direct-Cloud access observations
below. This Cloud shell still has no staging key binding or host permission;
the GitHub runner uses its separate authorized repository secret.

Follow-up verification: **99 preliminary tests passed**; the combined
preliminary/official/scientific/evidence/FDA suites passed **945 tests plus 298
subtests**, with one external fixture skipped. The full backend suite passed
**1,007 tests**, with one external fixture skipped and zero failures. Three new
isolated registry regressions verify no DML for existing IDs, insert-only missing
IDs with unrelated tables unchanged, and actual database uniqueness constraints.
These use an isolated SQLite database, not staging PostgreSQL. Independent code
review found and closed a factory-level authorization bypass; all four supported
HTTP entrypoints are now guarded. Remote CI is checked after publication.

Fetched research branch HEAD `f6f2f148b69befd8141ace54a90fc44bb3012a38`.
All 14 associated pull-request workflows completed successfully. Both existing
10,001-record duplicate-ID regressions were rerun locally and passed. Inspection
found that the preliminary safety job selected only five older test modules;
the adapter/HTTP/field-map tests were not executed by that job despite matching
its path filters. The job now runs all `test_preliminary_*.py` modules plus the
existing workspace bridge tests.

## Implemented retrieval safeguards

The existing authenticated HTTP client now reads `/api/workspace/summary` before
and after version-pinned `/api/workspace/page` pagination. It requires consistent
Pipeline counts, source timestamp and source state. Every page must preserve
version, timestamp and total, contain exactly the requested row count except
for the final remainder, and expose correct integer bounds/next offset. Boolean
offsets cannot alias integers. Offset source timestamps must be aware and, for
actual HTTP screening, within the explicit 24-hour research freshness window.
The backend's canonical date-only `asOf` follows its distinct current Los Angeles
calendar-day contract; its precision remains explicit rather than being converted
to an invented midnight timestamp.

Duplicate permanent program IDs remain blocked across all pages and across
10,000-record screening batches. Different permanent IDs sharing one supplied
exact source-program key are also rejected. Missing listing and restriction
verification still prevent eligibility. The field mapper safely rejects malformed
URLs and target dates. Date-only or aware cap-observation clocks are supported;
future or more-than-seven-day-old cap claims are withheld from source-presence
counts when the workspace timestamp is available. This is a conservative research
triage window, not a change to production restrictions or a scientifically
validated predictive rule.

The client refuses redirects so internal-key headers cannot be forwarded to a
different destination. Repeated JSON keys, nonfinite JSON and non-object payloads
fail closed without printing response bodies or credentials. Retrieved page and
row SHA-256 identifiers support local replay; they do not authenticate original
scientific sources, production restrictions or backend content-version derivation.
Aggregate diagnostics omit individual program records.

## Backend behavior and actual access status

Source inspection at the fetched commit shows:

- Both endpoints enforce `require_internal_key` and `require_storage`.
- Both call `source_workspace.workspace()`, which may gather/refresh external
  published sources and update process-local cache state.
- Page preparation calls `workspace_response.prepared()` and
  `program_registry.number_workspace()`. Missing permanent identities may be
  inserted into the existing database registry and committed. It also updates
  process-local content-version history. An HTTP GET is therefore **not an
  entirely side-effect-free backend operation**.

No backend behavior, scanner, authentication, database setting, membership,
FS/FA association or restriction was modified. Inspection describes repository
code. The subsequent Render control-plane check reports live deployment
`dep-dbf47d4s728c73e26mng` at `abad93df976b852ec48359469765280feada9fbd`.
That exact commit's `main.py` and `program_registry.py` were retrieved read-only
from GitHub. Both required routes, internal-key authentication and the same
insert-only registry implementation are present. This establishes source at
the reported deployment commit, not a fresh authenticated application response.
The research client changes require no backend deployment.

The Render monitoring plugin confirmed `pdufa-new-api-staging` exists in the
user-specified **My Workspace**, service `srv-db976hfbtjjs73bb98fg`, with origin
`https://pdufa-new-api-staging.onrender.com` and automatic deployment off.
This is control-plane metadata, not an authenticated workload or SQL probe.

The current execution environment has **no bound `PDUFA_INTERNAL_API_KEY`** and
its enforced host policy excludes the staging origin. The actual operator
command at `19c9817b` exited **2 before any HTTP request**, reporting the missing key.
No repeated blocked-host probes, credential extraction, auth weakening, database
allowlist changes or deployment were attempted. The previously reported 11,812
assessment records and 11,636 registry entries were not independently retrieved
or reconciled here; they describe different populations from a Pipeline page.

Alternative access paths were inspected. The Render connector can inspect
service/deploy metadata and update environment variables, but exposes no secure
read/bind operation for staging environment secrets or authenticated application
request transport. No local Render API credential or outbound identity binding
is available. The existing GitHub secret reference belongs to
`isolated-alpaca-review` and a different service; it was not reused. No secret
values, environment dumps or credential files were read, displayed or committed.

Existing IDs are selected by exact source key and are not updated. New keys use
`ON CONFLICT(source_key) DO NOTHING`, then re-read the winning mapping. The
unique source-key constraint and primary-key constraint prevent duplicate stored
identities. Concurrency may consume sequence numbers and leave gaps; this does
not mean an existing ID changes. Actual staging PostgreSQL constraints/data have
not been probed from this environment. Source inspection and isolated tests do
not replace that live verification.

## Authorized operator command

Use a supported environment with the internal key securely bound and the staging
origin explicitly permitted. Never pass the key as a command-line argument or
paste it into chat. Account for the existing backend identity-allocation behavior
described above before invoking the endpoints.

```sh
python -m research.preliminary_workspace_http \
  --backend-origin https://pdufa-new-api-staging.onrender.com \
  --allow-staging-identity-allocation \
  --request-timeout 120 \
  --output /authorized/pipeline-aggregate-diagnostics.json
```

The runner refuses overwrites and only writes diagnostics after complete
reconciliation. For authorized in-process per-record investigation,
`screen_backend_workspace` returns the full blocked research report; keep it in
the authorized research environment rather than committing private snapshots.
That API also requires `allow_identity_allocation=True`, only after approval.

The runtime supports reporting secret bindings, but the available Cloud
Environment tools expose only status/diagnostics. No secret-injection control or
verified UI menu path is exposed to this agent. The exact configuration backing
this session is
`7b12e40c-e824-4db2-9b7f-6c642ecda6f3~cecfg_6ae019e98ccc819a86be89c295a30a95`,
revision 1. Its supported environment-configuration workflow must attach the
existing staging key as `PDUFA_INTERNAL_API_KEY` and grant the staging hostname;
changing the Render service environment does not inject a secret into this
runner. No UI click path is claimed here.

## Concrete operator alternative: hidden terminal input

An operator can run the existing authorized retrieval from this research branch
in an approved terminal environment with staging network access, without binding
or exporting an environment variable:

```sh
python -m research.preliminary_workspace_http \
  --backend-origin https://pdufa-new-api-staging.onrender.com \
  --allow-staging-identity-allocation --prompt-key \
  --output /authorized/pipeline-aggregate-diagnostics.json
```

Enter the existing staging key only at the terminal's hidden prompt, never in
chat or a shell command. `--prompt-key` is restricted to the exact staging origin
and requires the allocation-authorization flag before requesting the key. Both
stdin and stderr must be terminals. If no-echo input is unavailable, the runner
stops rather than falling back to echoed or piped input. The key is passed to the
client in process memory only; it is not exported to the environment, put in
command arguments, logged, written to a file or included in the aggregate report.
Releasing the reference does not guarantee erasure of immutable string memory.

This alternative does not bypass the current execution environment's blocked
network policy or supply this agent with a secret. It makes the operator handoff
executable without inventing a settings menu. No new credentials or deployment
are required. Do not reuse the separate review-service secret.

Hidden-prompt increment verification: **106 preliminary tests passed**, including
seven new prompt/privacy regressions; combined research suites **952 passed plus
298 subtests**, one external fixture skipped; full backend **1,007 passed**, one
external fixture skipped; zero failures. Independent review reran all 44 HTTP
tests and found no material issues. These remain software checks, not live
authentication or Pipeline reconciliation results.

## Verification and next executable milestone

- Preliminary suite: **78 passed**, including a clean environment with only
  pytest installed, matching the dedicated job's dependency setup.
- Combined preliminary/official/scientific/registry/evidence/security/FDA suites:
  **924 passed, 298 subtests passed, one unavailable external RFC3161 fixture
  skipped; zero failures**.
- Full backend preservation suite: **1,004 passed, one external receipt fixture
  skipped; zero failures**.
- Existing eight-field and separate 650-field/50-level structural validators,
  saved GEM source-ledger structure and whitespace checks passed. Structural
  checks are not independent scientific or live source verification.

Next: securely bind the internal key and permit the staging origin through
supported environment configuration; execute this reconciled retrieval and
review listing, market-cap, restriction, exact FDA application/target and
scientific evidence for each program. No supported program qualifies for a
preliminary outcome merely from a successful API response. Independent historical
FDA evidence/adjudication and out-of-sample validation remain incomplete.

PIPELINE → GEM JR → GEM → WT and original GEM JR/GEM FS/FA associations remain
unchanged. No trading, merge or deployment was performed.
