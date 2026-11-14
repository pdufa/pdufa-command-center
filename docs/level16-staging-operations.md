# Isolated staging operations — review only, no deployment authorization

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


## Scope and templates

`infra/level16-staging/render.yaml.example` is a separate private service/database
proposal. The existing `new-platform/render.yaml`, production app, worker and scan
schedules remain unchanged. The example uses the whole repository as build context
because the existing preview reads scripts and canonical frontend FOCUS snapshots;
a backend-only root would omit those dependencies.

The service runs `app.level16_staging_preparation:app`, never `app.main:app`.
It does not open a database, authenticate a reviewer, launch a worker, fetch
clinical sources or execute DDL. `/livez` is a liveness check only. `/readyz`
returns 503 with explicit configuration/approval blockers, even if all decision
references are filled. Other routes return 503. It has no live activation flag.
Private services have no Blueprint `healthCheckPath`; probe HTTP readiness on the
private network after authorized creation. No public gateway or callback origin
is supplied. Proposed region/resource names must be checked/approved before use.

## Database and roles (only after approval)

1. Prove the target is the new isolated staging database/resource/workspace.
   A matching database name alone does not prove isolation or owner approval.
   Verify actual host/resource ID and billing/admin ownership independently.
2. Check the migration operator can create the NOLOGIN writer role and schema,
   grant restricted privileges, own/enable triggers and RLS, and perform exports.
   If the managed provider cannot grant required capabilities, stop; do not
   remove checks or substitute owner credentials in the runtime.
3. Review and manually apply `20261113_level16_review_events.sql`, followed by
   `20261113_level16_staging_evidence.sql`. Neither is a startup migration.
   Templates contain no commands to migrate an existing production database.
4. Review `restricted-roles.sql.example`; supply the exact authorized staging
   database explicitly. It provisions a new non-owner runtime login with no
   password value. Provision its credential interactively or through approved
   secret tooling; new login cannot authenticate by password until then.
5. Runtime receives `PDUFA_LEVEL16_DATABASE_URL` referencing that restricted login,
   not `fromDatabase.connectionString`/owner. The preparation service intentionally
   does not consume that DSN. Future approved live wiring must reuse the existing
   service permission checks, not bypass them.
6. Run `preflight.sql` read-only and existing service guard checks. Expect four RLS
   tables, six original guards and eighteen staging guards; runtime must have no
   superuser/CREATEROLE/BYPASSRLS/owner membership or history mutation privileges.
   Verify missing guards or unauthorized access fail closed.

## Evidence and reviewer acceptance

- Verify issuer/audience/signature/type, expiry, sid/nbf/jti contract, real logout,
  invalidation/denylist behavior and key rotation on actual private test tokens.
- Proof five distinct individuals; grant/source-scope changes through a separate
  administrator; validate aliases cannot self-review/challenge/adjudicate.
- Curator supplies only lawfully accessible original public documents. Do not
  import registry URLs or local hash receipts as source authentication. Private
  originals, person proofs, keys and credentials never go into GitHub.
- Verify all document/amendment bytes, versions, cutoff and immutable manifest,
  independent human source attestation, current pointer locks and per-person
  access. Confirm a new version removes current completion while preserving all
  old originals and event history.
- Execute each level's actual clinical/statistical/specialist requirements, reasons,
  contradictions and limitations. Keep missing/nonpublic/not-yet-expected/conflicting
  evidence distinct. An administrator cannot certify science with a role flag.
- No real assessment is considered ready based on synthetic test success or on
  process liveness. FDA forecasts/probabilities remain null.

## Backups, recovery and secure rollback

Proposed acceptance targets (owner must approve): paid DB PITR with seven-day
window on Pro; daily encrypted logical export, 30-day backup retention; original
source/review history retained indefinitely; RPO <=24 hours for exports; target
RTO <=4 hours, measured in an isolated restore drill before live enablement.
No new backup cron or existing scan schedule is installed by this package.

Before real use, export the whole isolated database in PostgreSQL custom format
using the approved secret mechanism. Never put DSNs/passwords in command history,
logs or Git. Store encrypted exports in owner-approved restricted backup storage;
include schema, triggers, functions, RLS, grants, byte originals and complete event
history. Instance/cluster role provisioning is separate from a database dump.

Restore into a **new empty isolated database**, never on top of production or
review history. Ensure expected NOLOGIN/runtime roles exist, restore owner/ACL
policy deliberately, and compare inventories: all event IDs/ordinals/predecessors,
server timestamps, source hashes/bytes, immutable manifests, person mappings,
revocations, current generations and audit rows. Then prove runtime cannot update,
delete or truncate history or read unauthorized evidence and that all guards/RLS
remain active. A readable dump or matching checksum alone does not prove recovery.
The disposable automated restore drill exercises actual pg_dump/pg_restore plus
these integrity/mutation controls; it is not a production recovery guarantee.

Rollback is **access suspension and forward recovery**, not data deletion:

1. Stop private ingress/live release and revoke affected reviewer sessions/grants
   through the authorized administrator. Retain events, originals and audit.
2. Return service code to the disabled preparation entrypoint; readiness stays 503.
   Do not run down migrations, reset sequences or restore an old production snapshot.
3. For database recovery, restore/PITR into a new isolated instance, verify complete
   inventories and role/RLS controls, then obtain owner approval for staging-only
   DSN cutover. Keep the prior instance read-only for audit, rather than overwrite it.
4. For source errors, append corrections/superseding versions and renewed independent
   reviews; never edit an existing event or original document. For key compromise,
   revoke sessions/authority approvals and block affected evidence until verified.
5. Re-run acceptance, backup/restore and retirement checks before any approved
   staging re-enable. Production, scans, memberships and Levels 7–20 stay untouched.
