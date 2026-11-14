# Isolated Scientific Levels 1–6 staging harness

> **ARCHIVED EXTERNAL-REVIEW DESIGN — NOT AN ACTIVE REQUIREMENT (owner decision, November 13, 2026).**
> All outside clinical, statistical, source-attestation, challenger, regulatory,
> qualification and multi-person adjudication gates described below were
> **withdrawn for owner assessments at Levels 1–20**. The owner alone checks
> and accepts results. The former five-person/A01–A14 reviewer scheme and
> its old synthetic tests are historical/disabled engineering, not owner
> work blockers. Use `AGENTS.md` (top directive),
> `infra/assessment/sole-owner-levels1-20.json` and
> `docs/level16-sole-owner-operation.md` for active policy.
> Existing security, evidence honesty, cutoff and deployment controls remain.
> No external review has been falsely recorded as completed.


## Actual delivery and approval state

Continues `68c49f13c99a7ff1b78d1d00a8934a7a6be78be3` and PR #1181.
The 87-test baseline and its Windows/Linux/PostgreSQL CI were inspected before
changes. `AGENTS.md`, shared dashboard auth, internal/medical keys, existing
review policy/events, migration, source dossiers/submissions/byte receipts,
phase-first engine, preview and prior CI were retained.

**No individual identity provider or source-attestation authority is explicitly
approved in the repository. No live reviewer login, isolated deployment, real
original evidence or genuine independent scientific assessment is activated.**
The only enabled factory mode supplied here is `SYNTHETIC_TEST_ONLY`, restricted
to newly created `level16_test_*` PostgreSQL databases and `.example.test` issuers.
It uses ephemeral synthetic keys/identities/documents in tests. Default factory
configuration returns BLOCKED/503. An arbitrary approval object/reference cannot
activate a live mode. There is no production import, route mount, env activation
flag, startup migration or deployment command.

## Identity adapter

`app/level16_staging_identity.py` supplies a narrow pinned-key RS256 access-token
adapter, not a new identity provider or sign-in service. It verifies the approved
issuer, exact single audience, public-key signature/kid, token type, exp/iat/nbf,
maximum lifetime, stable sub, session ID and token ID. It rejects unsigned or
foreign signatures, unknown keys, token-controlled key URLs and reviewer-role
claims. It does not discover keys from a token or fetch arbitrary URLs.

PostgreSQL separately provisioned accounts map issuer/sub to a stable person UUID.
Different accounts for one person return the same canonical reviewer identity;
the existing self-review/challenge/adjudication gates therefore apply across
aliases. This mapping requires actual identity proofing before any live use.
Server-side `reviewer_grants` remain the only source of the four authorized roles.
Shared dashboard cookies and service keys are never scientific reviewer identities.

Every authenticated request checks its provisioned session, expiry, valid-after
invalidation, session revocation and individual token revocation. The same checks
and row locks run again inside the review transaction. Revocation writes serialize
with active session locks. Local transaction context is set only by the trusted
adapter; callers cannot supply it through review JSON. The additional database
trigger requires that context and the canonical individual identity for events.
Backend database credentials remain a trusted server boundary, never end-user
credentials. This is not protection against a compromised privileged application
process or DBA.

Authentication, transaction authorization and denial audit records are durable,
append-only, server-timestamped and contain no bearer tokens/private keys/document
bytes. Existing review events independently record each actual authorized role.
Signature verification proves the configured signing key issued a token; it does
not establish identity proofing or external approval by itself.

## Transactional original evidence

`app/level16_staging_evidence.py` reuses the review service transaction. Current
NCT/level version pointers, evidence access, manifests, original bytes and source
verifier grants are locked/read on that same connection. Concurrent pointer
publication cannot change the binding mid-review. Pointer changes advance both
generation and immutable evidence version; ordinary DML cannot delete/reset the
pointer to bypass that check.

Each immutable bundle binds company/ticker, exact NCT, indication/population,
current phase/status, independently verified application cycle or null, assessment
level, document ID/SHA-256, document/protocol version, original source URL,
publication/retrieval dates and evidence cutoff. The canonical FOCUS roster and
provisional crosswalk restrict identity; they never independently verify an
application. The three unmapped NCTs cannot gain invented mappings.

Original bytes are stored in a separate immutable PostgreSQL table, reusing the
approved persistence stack. Each document and amendment is bounded at 64 MiB.
Missing/empty bytes, digest mismatches, incomplete links/versions, date/cutoff
violations, future cutoffs, cross-trial/application amendments and stale versions
are rejected. Amendment originals are checked separately. There is no HTTP upload
or automatic source retrieval. Only lawfully obtained public originals may be
provisioned by a separately authorized process; confidential records do not belong
in GitHub or these tests.

A separately approved, pinned source authority must sign the exact manifest,
including provenance, amendments, current binding and checks. The attesting
stable person must have a provisioned SOURCE_VERIFIER grant. The actual source
authentication event must come from that same verifier, distinct from the source
submitter. A checksum, a caller's issuer claim, a signature alone or a dictionary
of PASS flags cannot substitute for the combined original-byte, provenance,
identity, grant, current-version and attestation gates.

**An authority signature does not perform medical/source review.** A real
attestation must follow an actual independent review of the original source,
ownership, exact trial identity, population, phase/status, versions, dates,
conflicts and authorized access. No such real attestation is supplied here.
The resolver rejects outcome-exposed/archive-purpose manifests; semantic source
accuracy and hidden outcome exposure still require human source governance.
Nothing here establishes a blind prediction, calibration or FDA probability.

## Persistence and access

`20261113_level16_staging_evidence.sql` is an additive migration after the existing
review-event migration. It creates account/session/revocation, immutable audit,
original-document/bundle, evidence-access and current-version tables. It does not
modify application/worker/scan tables and is never run against production by this
stage. Only disposable tests apply it automatically.

Runtime credentials cannot provision people, roles, sessions, evidence or access;
they cannot rewrite originals, audit or review history. PostgreSQL row-level
security restricts streams, events, bundles and original bytes to the authorized
person's evidence grants. No transaction identity yields no evidence rows.
DBA credentials are rejected by the review runtime. Deliberate DBA/schema changes
remain possible and require normal administrative separation/backups/retention.

New source versions invalidate current readiness without deleting old events or
original bytes. Historic authorized event history remains readable through the
existing history API. Corrections still create new events and require renewed
review. Source authentication does not complete clinical review; separately
identified clinical, challenge and final-administrator stages remain mandatory.

## Protected interface and phase-first reporting

`create_staging_app()` is a standalone **test harness factory**, not a production
entrypoint. It reuses the existing event router, phase-first engine and escaped
preview. Signed individual credentials protect HTML, events/history and original
byte downloads. No-store/CSP/nosniff headers apply to all responses. Original-byte
downloads are attachments; document text is not executed or embedded as HTML.

The interface covers all 32 FOCUS trials, 29 provisional trial mappings, 23 cycles
and the three visible exceptions. It displays company/ticker/NCT/indication,
source-authenticated phase when available, six separate level states, source
provenance/versions/digest/dates, reviewer identity/role, challenge, findings,
reasons, contradictions, limitations, event history and blockers. Missing and
rejected/inaccessible evidence remains blocked. Existing source queues retain
unreviewed, missing, conflicting, nonpublic and not-yet-expected dispositions.

Per-level fields separate implementation, report-time test execution (the report
does not run tests), evidence verification, scientific adjudication and blockers.
Authenticated phase drives phase-specific applicability; Phase 1/2 evidence never
requires future pivotal Phase 3 results/SAP. Synthetic positive paths can complete
a test level; default and actual FOCUS scientific completions remain zero. Scores,
FDA probabilities and outcome/timing judgments remain null.

A fresh trusted database projection is required before authorized findings or
history can be rendered; saved JSON cannot certify them. The harness explicitly
labels all positive test displays SYNTHETIC, not real clinical assessments. It
supplies no real provider login UI or approved staging deployment.

## Test execution and external dependencies

Optional dependencies: `requirements-level16-staging.txt`. CI adds synthetic JWT
and blocked-interface tests on both Windows and Ubuntu, plus staging integration
on a disposable PostgreSQL 16 service. Original byte-preserving Windows checkout,
all 87 prior tests and the mandatory retirement audit remain enabled. The database
test fixture restores autocommit after explicit migration DDL so lock tests use
real transactions; no guard is bypassed to reset test evidence versions.

Tests generate ephemeral private keys, tokens, source attestations, people and
original bytes marked SYNTHETIC_TEST_ONLY entirely in memory/disposable databases.
No real private keys, credentials, clinical documents or attestations are saved.

**Next exact development action:** obtain explicit approval for the real individual
issuer/audience/public-key rotation and invalidation mechanism, identity-proofed
reviewer/person mappings, independent original-source attestation authority and
isolated staging database/access policy. Review those concrete configuration
choices before implementing a live activation path or provisioning real evidence.
Then validate an actual original-source bundle and distinct authorized reviewers
in staging. No production migration, activation, merge or deployment is authorized
or performed by this work.
