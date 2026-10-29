# Authenticated Pipeline retrieval verification

Prediction status: **NOT READY / ABSTAIN**.

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
offsets cannot alias integers. Source timestamps must be aware and, for actual
HTTP screening, within the explicit 24-hour research freshness window.

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
code; the exact staging deployment/source equivalence is not established here.

The Render monitoring plugin confirmed `pdufa-new-api-staging` exists in the
user-specified **My Workspace**, service `srv-db976hfbtjjs73bb98fg`, with origin
`https://pdufa-new-api-staging.onrender.com` and automatic deployment off.
This is control-plane metadata, not an authenticated workload or SQL probe.

The current execution environment has **no bound `PDUFA_INTERNAL_API_KEY`** and
its enforced host policy excludes the staging origin. The actual operator
command below exited **2 before any HTTP request**, reporting the missing key.
No repeated blocked-host probes, credential extraction, auth weakening, database
allowlist changes or deployment were attempted. The previously reported 11,812
assessment records and 11,636 registry entries were not independently retrieved
or reconciled here; they describe different populations from a Pipeline page.

## Authorized operator command

Use a supported environment with the internal key securely bound and the staging
origin explicitly permitted. Never pass the key as a command-line argument or
paste it into chat. Account for the existing backend identity-allocation behavior
described above before invoking the endpoints.

```sh
python -m research.preliminary_workspace_http \
  --backend-origin https://pdufa-new-api-staging.onrender.com \
  --output /authorized/pipeline-aggregate-diagnostics.json
```

The runner refuses overwrites and only writes diagnostics after complete
reconciliation. For authorized in-process per-record investigation,
`screen_backend_workspace` returns the full blocked research report; keep it in
the authorized research environment rather than committing private snapshots.

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
