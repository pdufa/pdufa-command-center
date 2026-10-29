# PDUFA v1.1 research evidence: production integration gate

**State:** BLOCKED / NOT READY / ABSTAIN. This document is an implementation gate, not deployment authorization.

## Verified research components
- Append-only local SQLite evidence and provenance-review ledgers, with locally checked hash chains.
- Program-scoped read authorization contract and research FastAPI router.
- Next.js PREDICTIONS panel and a same-origin route that currently returns 503 rather than proxying unauthorized data.
- Only eight draft fields exist in the 650-slot planning inventory. No independently verified scientific findings or calibrated PASS/CRL/EXTENSION model.

## Blocking requirements before any live evidence endpoint
1. Select a real identity provider with cryptographically verified tokens or server-side sessions, unique reviewer subject IDs, expiration, key rotation, and revocation.
2. Resolve roles and program grants from **server-owned policy**, never client-supplied JSON, cookies, or request headers. The existing shared dashboard password is not a reviewer identity.
3. Bind every evidence submission to a verified submitter principal in the server database. **Current review code compares against a payload reviewer_id, which is not reliable evidence of submitter identity; independent-review approval must remain disabled until this is fixed.**
4. Require a distinct reviewer principal and per-program grant for every review, and enforce authorization on both reads and writes.
5. Implement a durable production PostgreSQL schema with migrations, transaction boundaries, backup/restore and audit controls. Research SQLite must not be treated as the deployed database.
6. Anchor audit-chain head digests outside the mutable database; local hash-chain verification alone cannot establish tamper resistance.
7. Expose a backend endpoint only after a complete authenticated integration test suite covers anonymous, expired, forged, cross-program, self-review, audit-corruption and outage cases.
8. Connect the Next.js same-origin route to that endpoint only after server-side authorization exists; validate response shape and return private no-store data.
9. Require separately verified scientific sources, complete field catalog, external holdout evaluation, calibration and abstention criteria before allowing any FDA decision prediction.

**Deployment gate:** No production router mount, evidence-reader privilege, reviewer approval, or trading decision is authorized by this research work.
