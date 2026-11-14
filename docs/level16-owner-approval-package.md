# Levels 1–6 owner approval package — NOT authorization

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


Current decision-by-decision preparation: [2026-11-14 A01–A14 resolution](level16-owner-approval-resolution-20261114.md). This adds evidence and owner actions; it grants no approval or live access.

Prepared from commit `41611d5b6487e504ff68cfe95b71e04c10713a75` and current public
provider references retrieved November 13, 2026. No provider, reviewer, workspace,
new database, credentials or deployment is approved by this package.

## Recommendation

Use a **new isolated Render workspace**, one private preparation/reviewer service,
one separate paid PostgreSQL 16 instance, a **separate Auth0 development tenant
subject to strict token-profile qualification**, and an owner-designated independent
source verifier with a separately controlled offline RSA attestation key.
Keep original public documents in the existing immutable PostgreSQL BYTEA tables
with per-person row policies. Do not introduce object storage until measured
volume requires it. No current worker, production instance, FOCUS membership or
Levels 7–20 configuration is reused or changed.

The repository's Render Blueprint and SQLAlchemy/psycopg support this hosting/data
stack. Existing shared-password login and internal API keys do not establish
individual reviewer identity. No individual provider is approved in repository
policy. The connected Render tool has **no selected workspace**; live resource
IDs, account permissions, subscription costs and available credits are unverified.
No account workspace was selected and no cloud resource was created or queried.

The recommendation is conditional: Auth0's documented RFC9068 examples have an
array audience and do not guarantee `sid`/`nbf`. Our adapter requires **RS256,
`at+jwt`, exactly one configured audience, `iss/sub/exp/iat/nbf/jti/sid`, short
lifetime, provisioned individual sessions and server-side revocation**. The default
Auth0 profile is not compatible unchanged. A real-token qualification test and
reviewed configuration/adapter work must establish the full contract. Do not
invent claims, disable audience/signature/expiry checks, relabel an ID token as an
access token, or activate a tenant merely because it supports JWTs.

## Compatible options, permissions, security and cost

| Area / option | Existing compatibility and required permissions | Security and owner decision | Expected cost / free option |
|---|---|---|---|
| Auth0 separate tenant — recommended after qualification | RS256/RFC9068 `at+jwt` available; tenant/API/application administrator must configure API audience, PKCE login, issuer keys and session invalidation integration. Exact claim contract remains blocked. | A02: tenant, billing, MFA, allowed origins, signing-key fingerprints, claim qualification; no client roles. | Public page advertises Free $0/up to 25,000 MAU; Essentials $35/month at the displayed 500-MAU tier adds Pro MFA. Verify billing cadence, region and feature selection. Free is suitable for contract testing, not assumed to meet clinical reviewer MFA policy. |
| Existing organizational OIDC/Entra/Okta tenant — reuse if owner identifies an approved one | No approved individual tenant found; administrator must provide issuer, audience, access-token profile and proof of person/account ownership. Current strict token contract must be qualified. | A02/A03: owner confirms existing service and licenses; no shared account or service principal as a human. | Incremental cost may be $0 under existing licensing; actual license/feature quote unknown. Not assumed owned or approved. |
| Keycloak on an isolated host — free software alternative | Standard OIDC/RSA and configurable claims; default token header/claims still require qualification. Needs host/database administrator and maintenance ownership; do not build a competing provider inside this app. | A02: patching, TLS, backups, MFA, issuer/key rotation, monitored availability and token profile responsibility. | Software/license $0; host, database and operator time are not free. An existing secure host can make incremental compute $0 only if owner confirms capacity/isolation. |
| Identity-proofed reviewer/person registry | Reuse `identity_accounts`, `identity_sessions`, `reviewer_grants`; separate administrator provisions through approved DB operations. | A03/A12: minimum **five distinct people**: source submitter, separate verifier, clinician, independent challenger, final administrator. Four role types, five people under current source-separation rules. Verify aliases, qualifications and conflicts; retain private identity proof outside Git. | No new license; actual human proofing/reviewer fees require a scope/quote. No invented reviewers or professional fee estimate. |
| Source attestation authority — designated independent verifier, offline RSA | Existing pinned source verifier accepts exact manifest/bytes/version binding. Owner must approve authority URI/audience/public keys; actual source verifier performs checklist before any signature. | A04/A07: separate signer custody from web/IdP keys, encrypted key backup, two-person release of key changes, document applicability/cutoff/conflict review. Signature alone is not source or scientific verification. | OpenSSL/offline software $0; existing secure workstation may have no incremental compute cost. Qualified reviewer time and secure custody remain costs. |
| Managed signing/KMS alternative | PKCS#1 v1.5 SHA-256/RSA public-key verification can be compatible; cloud/IAM/KMS administrator required; no existing approved signing service identified. | A04: provider, key policy, authorized human attestations, audit, signing API format/rotation proof must be reviewed. | Provider key/request/audit fees variable; obtain a quote. No unverified price assumed. |
| Dedicated Render PostgreSQL 16 — recommended | Reuse both existing additive migrations and runtime role. DB operator must demonstrate CREATE ROLE, schema/trigger/RLS ownership and backup permissions before purchase/apply; managed privileges are not presumed available. | A01/A05/A09: new instance/workspace, private-only access, separately provisioned owner/runtime credentials, migration preflight and restore drill. Runtime must not receive owner URL. | Proposed 0.5c-1g $19/month plus $0.30/GB storage; 1 GB starts at $0.30. 0.1c-256mb $6/month is cheaper but leaves limited document/query memory. Free DB $0 is temporary with no managed recovery; not suitable for durable genuine review history. |
| Local PostgreSQL/Docker alternative | Existing disposable tests reuse PostgreSQL 16, triggers and roles; no cloud API required. | Synthetic development only until owner approves secure hosting, access, retention and recovery. | Software $0, existing hardware/electricity/operator costs remain. Disposable test databases must never substitute for real review retention. |
| Restricted original storage — existing BYTEA/RLS | No new storage provider; DB curator provisions lawfully public originals and signed manifests; per-person source grants. | A06: no private clinical records in Git, 64 MiB/document cap, immutable originals/history, private access and encrypted backups. No public bucket or local ephemeral live evidence. | Included within paid DB storage at $0.30/GB/month; backup copies/egress extra. Local synthetic bytes have no cloud storage bill. |
| Rotation/revocation and reviewer administration | Reuse pinned keys, person/session tables, token denylist, authorization audit and immutable events. Identity/DB administrators need tightly scoped separate credentials. | A07: propose <=900s access tokens, 90-day signing-key review, overlap until all accepted tokens expire, emergency session revocation and audited grants. Real IdP logout/admin hooks and MFA policy still require implementation/qualification. | Built-in code has no license cost; provider MFA/audit features and operator time depend on selected plan. |

### Proposed monthly budget, not an invoice

At the retrieved public prices: Render Pro workspace **$25** + private 0.5c-512mb
service **$7** + 0.5c-1g PostgreSQL **$19** + 1 GB DB storage **$0.30** + displayed
Auth0 Essentials **$35** = **$86.30/month** before tax, egress, storage growth,
backup export storage, extra services and professional reviewer fees. Confirm
billing terms and feature eligibility before approval. An already paid compatible
workspace/IdP may reduce incremental cost; none is assumed. A cheaper separate
Hobby workspace with paid compute has a shorter PITR window (three days rather
than Pro's seven) and fewer administrative features. Entirely local synthetic
testing is the $0 cloud-bill alternative. No purchase or free-trial creation was
performed.

## Exact configuration and authorization sequence

1. Owner completes A01–A14 in `infra/level16-staging/owner-approval.json` with
   actual external approval references and concrete resource/configuration IDs.
   The JSON remains a decision record, **never runtime authorization**; even
   filled references cannot activate the preparation app or current harness.
2. Select the NEW account/workspace and region explicitly. Reserve new resource
   names and a separate database; verify no shared production network peer or
   production DSN. Approve the budget and administrator membership first.
3. In the approved IdP tenant, create an individual-reviewer API/application,
   configure Authorization Code + PKCE and MFA, exact issuer/audience/origins,
   access-token profile and signing keys. Inspect a legitimately issued token in
   a private test harness, not Git. Verify header, all required claims, actual
   invalidation and key-rotation behavior using `identity-profile.json.example`.
   If the strict contract cannot be issued, keep blocked and review a separate
   secure adapter change; do not silently weaken the guard. A real browser
   sign-in/callback component is not shipped by the current bearer-test harness.
4. Identity-proof and provision the five people, alias-to-person mapping,
   sessions and four role types privately. Do not place names/IDs/credentials in
   public templates. Runtime roles are read-only; role administrators cannot
   certify clinical work by granting themselves a role.
5. Approve a source authority and independently inspect original sources,
   document/protocol versions/amendments, exact NCT/application, phase/population,
   ownership, dates/cutoff and conflicts. The verifier signs the exact immutable
   manifest only after this work. No AI text or checksum substitutes for it.
6. Review `render.yaml.example` against current Render schema and account
   availability. It is NOT linked to a live Blueprint. `autoDeployTrigger: off`
   does not prevent first creation; no one should sync it before A14.
7. Create the separate approved staging DB only after authorization. Check operator
   capabilities (especially role creation) and DB identity. Manually apply the
   two existing migrations in order, then reviewed restricted-role provisioning.
   Use interactive/approved secret management for passwords; the SQL template
   creates no usable password. Supply only the restricted runtime DSN to the
   preparation service; never wire Render's owner connection string to the app.
8. Run read-only preflight and the operational acceptance/restore checks in
   `docs/level16-staging-operations.md`. Approve controlled private ingress/TLS and
   the later live activation release separately. Until then `/livez` indicates
   process health while `/readyz` remains **503 BLOCKED**.
9. Import actual public originals into the approved immutable store through a
   separately authorized curator process, verify bytes/provenance independently,
   and perform source → clinical → challenge → final review. Keep each level
   unreviewed until its own requirements are met. Never infer the three missing
   application mappings or produce unvalidated FDA probabilities.

## Owner checklist and current blockers

The machine-readable package has fourteen required decisions with null approval
references: workspace/isolation; IdP/MFA/token contract; people/roles; source
attestation authority; database/permissions; storage/data policy; rotation and
revocation; protected ingress/sign-in; backups/restore; cutoff/outcome quarantine;
budget; scientific qualifications; application verification; explicit release.
No decision is approved by generated text or by this commit. Credentials and
private key material must be exchanged through the approved secret service, not
PR comments or JSON templates.

## Public references actually retrieved

- [Render compute plans](https://render.com/docs/compute-plans)
- [Render pricing](https://render.com/pricing)
- [Render Blueprint reference](https://render.com/docs/blueprint-spec)
- [Render schema](https://render.com/schema/render.yaml.json)
- [Render backups/PITR](https://render.com/docs/postgresql-backups)
- [Auth0 pricing](https://auth0.com/pricing)
- [Auth0 access-token profiles](https://auth0.com/docs/secure/tokens/access-tokens/access-token-profiles)
- [Keycloak guides](https://www.keycloak.org/guides)

Pages were read, not merely linked. Prices are a point-in-time public estimate,
not a verified account quote. Workspace selection, real token claims, supported
managed-DB administrator privileges and reviewer qualifications remain external
facts requiring owner confirmation.
