# A01–A14 resolution — no authorization granted

All live integration stays disabled. TECHNICALLY_PREPARED means repository preparation only; it never means approved or operational. No private account identifiers are published.

## A01 — OWNER_DECISION_REQUIRED

Select NEW isolated Render workspace, account administrators and region; confirm no production private-network peer

Established: One team workspace is visible through the read-only Render connector. No workspace selected, administrators verified or production isolation approved.

Recommended: New isolated Render workspace/region; do not reuse a production private network.

Options/cost: Free: local Docker laboratory. Paid: separate Render Pro workspace.

Still needed: Owner account administrator, selected region, data residency and isolation evidence.

Minimum owner action: Name the authorized account administrator and approve a new isolated workspace/region.

## A02 — BLOCKED

Approve individual issuer/tenant/audience, MFA and a real-token contract test for RS256 at+jwt, exact audience, sid, nbf, jti, lifetime and invalidation

Established: RS256 signature, issuer, exact audience, expiry, session/token invalidation and alias/person gates have synthetic tests. No authentic individual provider approved or qualified.

Recommended: Separate Auth0 tenant, conditional on strict token contract qualification; no shared dashboard login.

Options/cost: Free: Auth0 developer tier for contract tests or self-hosted Keycloak (hosting/operations extra). Paid: Auth0 Essentials displayed $35/month estimate, confirm plan/MFA terms.

Still needed: Actual issuer/audience, public key fingerprints, MFA policy, real at+jwt token contract with sid/nbf/jti and revocation proof.

Minimum owner action: Select the provider/tenant and designate its administrator; authorize a real-token qualification session. No credentials in Git.

## A03 — EXTERNAL_EVIDENCE_REQUIRED

Identity-proof at least five distinct people: source submitter, separate source verifier, clinician, independent challenger, final administrator; approve immutable alias/person mappings and role grants

Established: Server-controlled four-role grants and stable person mapping reject self-challenge/alias bypass. Existing controls require five distinct people including submitter.

Recommended: Five individually identity-proofed people: submitter, verifier, clinician, challenger, adjudicator.

Options/cost: Free: qualified volunteers if available. Paid: professional verification and specialist review; no fee assumed.

Still needed: Real people, immutable person/account mappings, identity-proofing records and approved role grants.

Minimum owner action: Nominate five people and approve who verifies identities and administers role grants.

## A04 — OWNER_DECISION_REQUIRED

Designate an independent original-source attestation authority, signer custody, public key fingerprints and human verification checklist

Established: Signed attestation validation and exact evidence/cutoff binding implemented; zero genuine source attestations.

Recommended: Owner-designated independent human source verifier with separately controlled offline RS256 signer.

Options/cost: Free: locally generated approved key with accountable custody after authorization. Paid: managed KMS/HSM and professional verifier; quote required.

Still needed: Authority mandate, real verifier, custody/recovery policy, public fingerprints, attestation checklist.

Minimum owner action: Appoint the independent authority and approve custody/checklist; do not send private signing keys.

## A05 — EXTERNAL_EVIDENCE_REQUIRED

Approve separate PostgreSQL 16 instance, migration operator privileges, resource IDs, restricted runtime login and per-person evidence grants

Established: PostgreSQL append-only events, restricted writer roles, evidence RLS, transactional concurrency/replay controls and disposable database tests exist. No approved staging instance.

Recommended: New isolated PostgreSQL 16; migration operator separate from restricted runtime identity.

Options/cost: Free: disposable local PostgreSQL for synthetic tests. Paid: Render Basic $19/month plus storage; confirm regional pricing and recovery terms.

Still needed: New resource ID, owner/migration permissions, runtime secret reference, network isolation and grants.

Minimum owner action: Authorize the isolated instance and assign migration/runtime administrators; no production DSN.

## A06 — OWNER_DECISION_REQUIRED

Approve public-original acquisition/access policy, immutable storage limits, encryption, audit access and indefinite review/source history retention

Established: Original bytes are content-addressed outside Git; immutable PostgreSQL BYTEA/version/RLS controls exist. Public metadata reports contain no credentials or clinical records.

Recommended: Reuse existing immutable evidence tables with per-person access; public originals only for initial case.

Options/cost: Free: private local files for preparation. Paid: PostgreSQL storage (estimate $0.30/GB-month), encrypted backup storage extra.

Still needed: Access roster, encryption/retention policy, storage cap and permission to ingest selected public originals.

Minimum owner action: Approve public-source intake, named access, immutable retention and storage limit.

## A07 — TECHNICALLY_PREPARED

Approve pinned-key overlap/rotation, <=900-second access tokens, session/token revocation owners, emergency suspension and signer recovery

Established: Synthetic pinned-key/issuer/token/session rejection and revocation tests implemented. This does not prove actual provider revocation.

Recommended: Pinned key overlap, <=900-second tokens, accountable session invalidation and emergency suspension.

Options/cost: Free: documented manual rotation and local contract tests. Paid: provider/KMS administration and on-call operations.

Still needed: Named revocation/rotation owners, actual provider session invalidation evidence and recovery procedure approval.

Minimum owner action: Appoint security owners and approve rotation/revocation/recovery policy.

## A08 — BLOCKED

Approve internal-only ingress or separately protected TLS gateway, callback origins, and browser sign-in implementation; no shared dashboard identity

Established: Production interface remains unmounted. Protected synthetic API and disabled preparation health service exist; real browser sign-in/TLS ingress is not implemented or approved.

Recommended: Private service plus separately protected TLS gateway after origin/callback and login design approval.

Options/cost: Free: localhost synthetic harness. Paid: private Render service $7/month plus gateway if needed.

Still needed: Approved origins, callback URLs, ingress administrator, real browser login implementation and access test.

Minimum owner action: Choose internal ingress/gateway and approve exact origins before live sign-in development/configuration.

## A09 — TECHNICALLY_PREPARED

Approve backups: seven-day PITR, daily encrypted export/30-day backup retention, RPO <=24h, target RTO <=4h and restore drill before live enablement

Established: Disposable backup/restore inventory and mutation guards are tested; no provider backup policy or actual staging recovery accepted.

Recommended: Seven-day PITR, daily encrypted exports retained 30 days, RPO <=24h and target RTO <=4h; prove staging restore.

Options/cost: Free: local disposable pg_dump/restore drill. Paid: provider PITR/backup plan and export storage; quote required.

Still needed: Backup owner, encrypted export destination, provider retention/PITR entitlement and timed restore evidence.

Minimum owner action: Approve recovery targets, retention and backup administrator/destination.

## A10 — OWNER_DECISION_REQUIRED

Approve current-source cutoff and outcome-exposure quarantine; this collection is not a blind historical prediction input

Established: Every research artifact is current-source, unreviewed and excluded from blind historical predictions; exact cutoff and raw receipts retained.

Recommended: Use 2026-11-14 current-source cutoff for preliminary research; isolate all outcome-exposed material.

Options/cost: Free: existing cutoff/quarantine controls. Paid: independent blinded evaluator only if a future prospective study is separately authorized.

Still needed: Owner cutoff decision and actual reviewers exposure declarations.

Minimum owner action: Approve the current-source cutoff and require exposure declarations; do not call this a blind study.

## A11 — OWNER_DECISION_REQUIRED

Approve provider billing terms and monthly budget: estimated $86.30 before storage growth, backups, egress, taxes and professional reviewer fees

Established: Prior dated estimate $86.30/month before extras is recorded; no purchase or budget authorized. No fresh binding quote obtained.

Recommended: Authorize a capped staging budget only after checking provider plan, MFA, PITR and storage terms.

Options/cost: Free: local synthetic Docker + developer identity-contract tests. Paid: $25 workspace + $7 service + $19 database + $0.30 storage + $35 identity = $86.30/month estimate; tax/egress/backups/reviewers extra.

Still needed: Billing owner, current quotes, spending cap and professional reviewer budget.

Minimum owner action: Approve billing entity and maximum monthly spend after current quote confirmation.

## A12 — EXTERNAL_EVIDENCE_REQUIRED

Approve scientific qualifications, disease/statistical responsibilities and conflict-of-interest review for the actual reviewers

Established: Engineering role separation cannot establish medical/statistical qualifications or independence. No actual reviewer qualified.

Recommended: Disease specialist plus statistical reviewer/challenger with documented qualifications and COI checks.

Options/cost: Free: qualified volunteers if genuinely available. Paid: clinician/biostatistician review by quote.

Still needed: Credentials, scope, conflict disclosures, independence and availability of named reviewers.

Minimum owner action: Supply real qualified reviewers and authorize qualification/COI verification.

## A13 — EXTERNAL_EVIDENCE_REQUIRED

Assign exact-NCT application-cycle verification, retaining the three unmapped exceptions until evidence supports a mapping

Established: 29 trials/23 provisional cycles preserved. FDA product context retrieved for mitapivat and maralixibat; no exact application/review-cycle binding established for the three exceptions.

Recommended: Retain three unmapped exceptions; assign documentary verification to a human regulatory reviewer.

Options/cost: Free: public FDA/registry/sponsor evidence. Paid: qualified regulatory review if needed; no assumed data subscription.

Still needed: Exact application number plus submission/supplement/review cycle and source-backed trial linkage.

Minimum owner action: Assign the regulatory verifier; accept unmapped status until documentary evidence supports a cycle.

## A14 — BLOCKED

Authorize a specific isolated staging release only after configuration, token, evidence, backup and independent-review acceptance checks; this file itself cannot authorize activation

Established: Live access remains disabled. Filled templates are not authorization; no release, deployment or production migration performed.

Recommended: Separate explicit release authorization only after A01-A13 evidence and acceptance gates.

Options/cost: Free: retain disabled offline preparation. Paid: approved isolated release costs above.

Still needed: Signed/traceable owner authorization for a specific configuration/release after genuine identity, evidence, access and restore acceptance.

Minimum owner action: Review the completed acceptance package and authorize a specific isolated release only when prerequisites are met.
