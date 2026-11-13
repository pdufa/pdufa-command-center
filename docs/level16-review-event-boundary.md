# Scientific Levels 1–6 review-event boundary

## Status and existing architecture audit

This stage continues commit `148cdc753af2192199b1ecb8c9efaa015d68bd11`.
It adds tested policy, PostgreSQL persistence and server-only readback interfaces.
**It does not establish working individual reviewer authentication, authenticate
any original clinical document, or complete any real scientific assessment.**

Repository policy (`AGENTS.md`) remains authoritative. The existing backend uses
SQLAlchemy 2 with PostgreSQL/psycopg and a development SQLite fallback. It bootstraps
some tables with `create_all` and module-local SQL; there is no deployed Alembic
framework to reuse. This stage reuses SQLAlchemy/PostgreSQL, adds one explicit
review-only migration, and does not invoke existing initializers or create a
parallel database service. Existing exact-NCT source/prediction histories remain
untouched. Their application-level append conventions are not sufficient to
claim database-enforced immutability for independent medical decisions.

Existing frontend auth (`lib/auth.ts`) issues a shared password session without
an individual subject. Backend `require_internal_key` and
`require_medical_internal_key` verify shared service keys, not individual reviewer
identities. Neither provides reviewer role grants or independent identities.
They cannot authorize this new workflow. No auth provider is invented here.

## Trusted dependencies and fail-closed interface

`app/level16_review_policy.py` defines the lifecycle and unavailable adapters.
`app/level16_review_events.py` defines a PostgreSQL repository and an **unmounted**
FastAPI router factory. There is no main.py, worker, schedule or production-config
change, and no env flag that silently activates reviewer access.

`ReviewEventService()` defaults to unavailable identity and evidence providers.
Its HTTP interface returns 503 for shared keys, arbitrary names and unverified
tokens. Server code may inject an approved adapter only after it validates the
provider's signature, issuer, audience, expiry/revocation and stable individual
subject. It must return `Identity(issuer, subject)`, never deserialize a caller's
identity/role JSON. The role comes exclusively from server-managed PostgreSQL
`reviewer_grants`, rechecked and locked in every write transaction. Test adapters
exist only in tests and are explicitly synthetic.

Four responsibilities are distinct: SOURCE_VERIFIER, CLINICAL_REVIEWER,
INDEPENDENT_CHALLENGER, REVIEW_ADMIN. Multi-role grants do not bypass independence:
source submitters cannot authenticate their own submission, source participants
cannot perform their own clinical review, source/clinical participants cannot
challenge their own work, and prior non-administrator participants cannot give
final adjudication. String differences in old proposal metadata never establish
these identities. A correction retains author, stage and role and creates a new
event; it cannot use a correction to skip a review stage. Corrected findings become
CORRECTION_REQUIRES_REVIEW in the current projection and require a renewed full
review cycle; a correction to a final event cannot silently retain adjudication.

The evidence adapter must resolve the current immutable evidence bundle/stream,
including company, exact NCT, indication, current phase/status, independently
verified application identity or null, level, original document ID/hash, document
and protocol versions, source URL, publication/retrieval dates, cutoff and evidence
version. Missing phase/version data blocks these review events; existing metadata
intake still accepts and displays incomplete unreviewed leads. A provisional
crosswalk never becomes verified simply by appearing there. The three unmapped
trials cannot receive invented application IDs.

The adapter receives the **same SQLAlchemy transaction connection** for current
stream selection, current binding and independent source checks. A production
implementation must lock its approved current-source/version index in that
transaction and bind original-source attestations to the authenticated verifier,
source locators, version and cutoff. An external mutable lookup or an arbitrary
dictionary of PASS flags is not an acceptable production adapter. No such
production adapter or source-attestation registry is connected yet. Source checks
include ownership, identity, phase/status/population, original bytes, versions,
dates/cutoff and conflicts; a matching checksum cannot satisfy them alone.

## Durable history and migration safety

`new-platform/backend/migrations/20261113_level16_review_events.sql` is an additive,
transactional PostgreSQL migration. **Do not execute it against production.**
It is not called by application startup. It creates the isolated schema and a
NOLOGIN writer group; it requires separate authorized migration-owner privileges
and fails if those objects already exist, rather than rewriting existing data.
Before staging execution, review role/schema names, backups, ownership and grants.

- Separately provisioned evidence streams are immutable. The web writer cannot
  register streams, change bindings, provision reviewers or revoke/enable grants.
- Events record ID, exact evidence context, reviewer issuer/subject/role,
  findings/reasons/contradictions/limitations/blockers, action/status, source-check
  attestation, server timestamp, prior event, ordinal and immutable event version.
- Runtime credentials must be a separate non-owner, non-superuser login with
  membership in the writer group. The service rejects owner credentials,
  privilege escalation rights, unsafe mutation grants and missing/disabled guards.
- Database triggers reject UPDATE/DELETE/TRUNCATE of event history and immutable
  stream bindings. Reviewer identity/role grant keys cannot be rewritten. Runtime
  cannot disable triggers. No hash chain is represented as storage immutability.
- A transaction locks the stream before examining its history. Unique event IDs,
  unique stream ordinals, predecessor checks, FKs and database lifecycle/role
  checks reject replays, stale predecessors, skipped stages and competing writes.
- Role revocations serialize with review transactions via grant-row locks.
  Corrections append new events referencing the previous immutable event.
- Database owners/superusers can deliberately change schema/disable guards.
  Administrative separation, backups and external retention remain necessary;
  this is not tamper-proof against the DBA. The application cannot give itself
  those privileges.

The normal nine-stage lifecycle is enforced in both policy and database:
SOURCE_SUBMITTED → SOURCE_AUTHENTICATION_PENDING → SOURCE_AUTHENTICATED →
SCIENTIFIC_REVIEW_PENDING → SCIENTIFIC_REVIEW_COMPLETED →
INDEPENDENT_CHALLENGE_PENDING → INDEPENDENT_CHALLENGE_COMPLETED →
FINAL_ADJUDICATION_PENDING → FINAL_ADJUDICATED.

REJECTED, CONFLICT_UNRESOLVED, ADDITIONAL_EVIDENCE_REQUIRED,
SUPERSEDED_BY_NEW_EVIDENCE and NOT_APPLICABLE_AT_CURRENT_PHASE are separate
administrator dispositions. Conflict/additional-evidence resolution restarts
source authentication and the subsequent required reviews; it cannot jump back
to completion. Rejected/final/not-applicable streams permit an explicit
supersession or append-only same-stage correction, not an invisible rewrite.
New evidence requires separately registered new stream/version and old-stream
supersession; trusted current-stream selection prevents using stale findings.
Unresolved contradictions/blockers prevent completion. Phase non-applicability
is narrowly limited to early-phase Levels 3/5 and never waives source identity.

## Engine and offline display

The phase-first engine accepts an optional **server dependency**
`trusted_review_reader(nct, level)` backed by `service.projection(...)`. There is
no CLI/JSON trust option. Default reports expose disconnected auth/storage/evidence
blockers for every level, zero actual reviews and no authorized event history.
A configured service verifies current evidence context and authorized history
before returning a projection. Source authentication, clinical review, challenge
and final adjudication are separate statuses. Only final adjudication marks that
specific level complete, never all six levels or an FDA prediction.

The renderer requires a fresh identical trusted database projection before showing
any authorized findings/history. A saved JSON flag, forged event list, source
authentication claim or completion count is rejected. Offline CLI use cannot
establish this trust and remains an unreviewed readiness preview. The preview
shows source collection, authentication, reviewer authorization, clinical and
challenge status, findings/reasons/contradictions/limitations, history and blockers.
Proposal text remains explicitly UNREVIEWED. Historic events remain readable even
when superseded, but are not current scientific findings. No signed offline export
format is claimed.

All 32 FOCUS records, 29 provisional mappings, 23 cycles and three exceptions are
preserved. FDA probabilities/outcome/timing judgments remain null, and review
events never certify a prospective blind prediction or import outcome-aware
historical archives into active assessments.

## Validation and next action

The dedicated CI retains byte-preserving checkout and runs policy/HTTP plus all
existing Levels 1–6 tests on Windows and Ubuntu. A separate PostgreSQL 16 service
job applies the migration **only to a newly created disposable test database**
and tests real permissions, triggers, rollback, concurrency and engine/preview
readback. Local tests require explicit `LEVEL16_TEST_ALLOW_DISPOSABLE=1` and
`LEVEL16_TEST_DATABASE_URL`; they never read the application's `DATABASE_URL`.
The PostgreSQL test fixture refuses to reuse an existing review-writer role.
Mandatory retirement audit remains unchanged.

Next exact action: connect an approved individual identity provider and a
transactional original-evidence/current-stream resolver in an isolated staging
test harness; provision source verifier, clinician, challenger and administrator
as genuinely separate subjects. Validate real issuer/audience/expiry/revocation,
source attestations and reviewer grants before mounting any review router.
Obtain real source and scientific reviews only afterward. No staging/production
migration or provider connection has been performed by this stage.

## Subsequent staging harness slice

The isolated adapter/resolver/interface implementation and its explicit live
activation blockers are documented in [isolated staging](level16-isolated-staging.md).
Default access remains blocked; only disposable synthetic integration is enabled.
