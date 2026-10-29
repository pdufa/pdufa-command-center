# PDUFA v1.1 research evidence: production integration gate

**State:** BLOCKED / NOT READY / ABSTAIN. This document is an implementation gate, not deployment authorization.

## Verified research components
- Append-only local SQLite evidence and provenance-review ledgers, with locally checked hash chains.
- Isolated research API with RS256 issuer/audience/signature/time/key verification and server-controlled account/program grants; no provider configured or production mount.
- Atomic authenticated submission/submitter binding and independent provenance review with self-review/alias/program restrictions.
- Next.js PREDICTIONS panel and a same-origin route that currently returns 503 rather than proxying unauthorized data.
- Only eight draft fields exist in the 650-slot planning inventory. No independently verified scientific findings or calibrated PASS/CRL/EXTENSION model.

## Blocking requirements before any live evidence endpoint
1. Configure an approved real OIDC provider (issuer, dedicated API audience, pinned JWKS URI) and test actual login, rotation and account revocation. The cryptographic adapter is implemented; no tenant/provider is configured.
2. Resolve roles and program grants from **server-owned policy**, never client-supplied JSON, cookies, or request headers. The existing shared dashboard password is not a reviewer identity.
3. Provision canonical person IDs and program grants under operator control. The isolated API now atomically binds authenticated submitters and rejects self-review across aliases; configure and test those mappings against the real provider before any live use.
4. Require a distinct reviewer principal and per-program grant for every review, and enforce authorization on both reads and writes.
5. Implement a durable production PostgreSQL schema with migrations, transaction boundaries, backup/restore and audit controls. Research SQLite must not be treated as the deployed database.
6. Anchor audit-chain head digests outside the mutable database; local hash-chain verification alone cannot establish tamper resistance.
7. Keep the isolated API unmounted until a real-provider nonproduction acceptance test passes. Generated-key security integrations cover anonymous, expired, forged, cross-program, self-review, audit-corruption, outages and rollback; they do not establish a live provider connection.
8. Connect the Next.js same-origin route to that endpoint only after server-side authorization exists; validate response shape and return private no-store data.
9. Require separately verified scientific sources, complete field catalog, external holdout evaluation, calibration and abstention criteria before allowing any FDA decision prediction.

**Deployment gate:** No production router mount, evidence-reader privilege, reviewer approval, or trading decision is authorized by this research work.
