# Isolated research authentication integration

## Implemented boundary

The existing dashboard authenticates a shared-password session. That cookie does not identify an individual evidence submitter/reviewer and cannot supply reviewer roles. Production dashboard/backend authentication and the existing same-origin research route are unchanged. The browser research route continues to return 503 until an authorized identity bridge is configured.

The new isolated FastAPI factory in `research/prediction_v1_1_authenticated_api.py` is not mounted into production. Its default dependencies are absent, so it returns 503 and opens no evidence store. Tests construct the service explicitly with synthetic identities and real RSA signatures.

The supported identity profile is OIDC-style RS256 JWT access tokens with a dedicated research API audience. An approved Auth0 tenant or Keycloak realm using this profile can be integrated; **neither provider is selected, provisioned or configured here**. Other providers require the same pinned-issuer/JWKS profile or a separately reviewed trust policy. This is a resource-server verifier, not a new browser login/PKCE flow.

## Cryptographic and authorization controls

- Fixed RS256 verification checks exact issuer, intended audience, subject, signature, required expiration/issued-at and optional not-before. Unsigned, symmetric-algorithm, expired, forged, future-dated, duplicate-JSON and malformed tokens fail closed.
- Only the operator-pinned HTTPS JWKS URI is fetched with TLS verification. No token-supplied key URLs, redirects or algorithm selection. Key identity, RSA size/exponent, signing use and operations are checked. Responses/keys are bounded; rotation and outage refresh are throttled; failed refresh does not serve stale keys.
- The verifier returns issuer/subject only. Roles and program permissions come from an explicit server-owned `PrincipalDirectory`, keyed by that pair. JWT roles, request headers and body actor fields do not grant access. There is no HTTP account/grant-enrollment endpoint.
- Multiple external subjects can map to one canonical person ID. That ID binds submissions and prevents self-review through identity aliases. Directory replacement/revocation is a trusted server operation and takes effect on subsequent requests; editing a file does not itself reload the running directory.
- Read, submit and review routes enforce distinct roles and exact program grants. Strict request models reject extra identity/review claims. The legacy boolean `verified_by_provider` shortcut always rejects requests to manufacture principals.
- Submission plus immutable submitter binding and provenance reviews run in atomic locked transactions. Audit chains and binding consistency are checked before/after writes. Failures roll back; SQL append-only triggers remain in effect. Authenticated and denied responses are private/no-store.

## Nonproduction construction

```python
from research.prediction_v1_1_oidc_preflight import OIDCConfiguration
from research.prediction_v1_1_oidc_verifier import OIDCVerifier
from research.prediction_v1_1_principal_directory import PrincipalDirectory
from research.prediction_v1_1_authenticated_api import create_research_api

# All values below must come from approved server configuration, never a request.
verifier = OIDCVerifier(OIDCConfiguration(issuer, research_api_audience, jwks_uri))
directory = PrincipalDirectory.from_file(operator_owned_grant_file)
app = create_research_api(
    verifier=verifier, directory=directory, store_path=explicit_research_sqlite_path,
    catalog=server_catalog, program_cutoffs=server_cutoff_map,
)
```

This example does not create a provider, grant a role, start a listener or authorize deployment. JWT public-key verification needs issuer/audience/JWKS metadata, not a provider private signing key. A browser authorization client, redirect configuration and any required login credentials remain separate integration work.

The server-owned grant file uses `schema_version: research-principal-directory-v1` and an `accounts` list. Every account contains exact `issuer`, `subject`, canonical `principal`, explicit `roles` (`evidence_reader`, `evidence_submitter`, `evidence_reviewer`), exact `program_ids`, and boolean `active`. Do not auto-provision these fields from token claims. File ownership/management and canonical-person alias mapping require operator approval.

Routes:

- `GET /research/v1-1/evidence/{program_id}` — authenticated, program-scoped reader.
- `POST /research/v1-1/evidence` — authenticated submitter; server-bound actor, unverified intake only.
- `POST /research/v1-1/reviews/{evidence_event_id}` — distinct, program-scoped reviewer; provenance review only.

No DELETE/PATCH or prediction/trading route is added. Approval of provenance does not certify clinical truth or model validity. Responses remain **NOT_READY / ABSTAIN**.

## Verification

The complete v1.1 evidence/security unittest suite passes **119 tests**, including real RSA-signed HTTP integrations, key rotation/outage handling, server grant revocation, anonymous/expired/forged tokens, cross-program access, identity-alias self-review, audit corruption, immutable records and transaction rollback. The broader FDA/research suite passes **391 tests plus 43 subtests**; one opt-in genuine RFC 3161 timestamp test is skipped because independently obtained TSA fixtures are not configured. No external timestamp or scientific validation is inferred from that skip. The combined research/security run passes **510 tests plus 213 subtests**, with the same one unconfigured genuine-TSA integration skipped and two dependency/marker warnings. Zero tests failed. Final CI results are recorded in PR #522.

Security test dependencies are isolated in `research/requirements-security.txt`. No production requirements, service mounting, credentials or authentication settings are changed.

## Remaining live-integration blockers

No actual issuer, dedicated API audience, pinned JWKS endpoint, server grant file or research SQLite path is configured in this workspace. Select/approve a real provider and canonical identities, configure/review grants and storage, then run a nonproduction integration against the actual provider and its rotation/revocation policy. The current shared dashboard session is insufficient.

Production requires separately authorized hosting, a PostgreSQL storage/migration/backup plan, external audit-head anchoring and a reviewed browser identity bridge. SQLite/local hashes are research infrastructure, not a production audit guarantee. Deployment and changes to production authentication still require explicit approval.

Scientific evidence certification, independently validated predictions and trading remain blocked and are outside this authentication milestone. Existing Pipeline, GEM JR/GEM/WT restrictions, memberships, original FS/FA associations and scanners/schedules remain unchanged.

## Files changed for this security milestone

- `research/prediction_v1_1_oidc_verifier.py` and `prediction_v1_1_oidc_preflight.py`: cryptographic verifier and configuration profile.
- `research/prediction_v1_1_principal_directory.py` and `prediction_v1_1_authenticated_api.py`: server-owned grants and isolated authenticated routes.
- `research/prediction_v1_1_authorization.py`, `prediction_v1_1_identity_boundary.py`, `prediction_v1_1_evidence_projection.py`: strict principals, retired boolean shortcut and accurate projection messaging.
- Five `tests/test_prediction_v1_1_*` files: authorization, identity boundary, preflight, verifier and authenticated API regressions.
- `research/requirements-security.txt` and `.github/workflows/pdufa-v1-1-evidence-safety.yml`: isolated test dependencies and CI.
- `research/evidence/PRODUCTION_INTEGRATION_GATE.md` and this report: verified implementation versus remaining live-integration blockers.
