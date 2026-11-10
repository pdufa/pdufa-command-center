# MAIN Revision 32 — separate database migration owner and evidence runtime grants

**Trial:** ACACIA-HCM, exact NCT06081894, CY 6033.  
**Deployment boundary:** Draft PR #965 and Vercel draft PREDICTIONS only. **No** Neon or Render database migrations, new billed resources, service secrets, document uploads or clinical writes.

## Installed implementation

### Separate database migration privilege

`new-platform/backend/app/medical_original_evidence_permissions.py` defines `migrate_by_administrator` as an **explicit-only** migration API. It requires a previously provisioned, unique PostgreSQL LOGIN role `pdufa_vault_runtime` that lacks superuser, CREATEDB, CREATEROLE, replication and BYPASSRLS powers. Only the independent administrator/schema owner can create the vault table, indexes and append-only immutability trigger. It then grants only **SELECT and INSERT** on the original-evidence vault table to the runtime role and revokes the function's public EXECUTE privilege.

The migration function does **not** create any real database user, generate passwords, connect to any hosted database or execute automatically from web routes. A real migration requires separately approved infrastructure access and a nonproduction review.

### Dedicated least-privileged runtime

The vault no longer uses the shared backend `DATABASE_URL` or shared `ENGINE`. Its dedicated `PDUFA_EVIDENCE_RUNTIME_DATABASE_URL` must identify the exact separate PostgreSQL login `pdufa_vault_runtime` and not equal the general service connection; external connections require **TLS verify-full**. For CI only, a strictly named disposable localhost database is accepted under an explicit test switch.

`verify_runtime` checks the actual PostgreSQL `session_user` and `current_user`, prohibits a table-owner or database-owner session, checks schema and database CREATE permissions are absent, rejects membership in the table-owner role, and asserts the runtime has SELECT and INSERT while **UPDATE, DELETE, TRUNCATE, REFERENCES and TRIGGER are denied**. The required exact append-only trigger must be enabled with the right SQL statement-level trigger signature and a separate function owner. This is checked before each HTTP vault access, not only on service startup.

`new-platform/backend/app/medical_original_evidence_vault_http.py` no longer calls `vault.initialize`. A missing or overprivileged evidence runtime connection returns **503** before document storage. `new-platform/backend/app/main.py` passes a dedicated evidence engine into the already-disabled isolated-only vault routes. Browser exposure remains prohibited.

### Actual disposable PostgreSQL security evidence

[**GitHub Actions #42564391773**](https://github.com/pdufa/pdufa-command-center/actions/runs/42564391773) **SUCCESS** after correcting the test for PostgreSQL's legitimate behavior of issuing a warning (not an error) for unauthorized `GRANT`. The test uses a local throwaway PostgreSQL 16 service and a synthetic runtime password known only in the disposable workflow.

The test proves:
- Administrator creates additive vault schema, metadata indexes and trigger; runtime cannot perform migration.
- Actual user `pdufa_vault_runtime` has SELECT and INSERT privileges only; no owner membership and no schema/database creation.
- Runtime cannot UPDATE, DELETE, TRUNCATE, ALTER, DROP, CREATE tables, disable the trigger, SET ROLE administrator or grant itself permissions.
- A nonowner's attempted unauthorized `GRANT` may *warn rather than error*; test checks effective privileges and verifies destructive SQL remains denied.
- Runtime successfully stores only AES-256-GCM encrypted **synthetic** source bytes, verifies its SHA-256 and receipt chain, and never creates a clinical grade.
- Attempts to connect with shared service role, substitute another database, disable verified TLS for remote hosts or access unrelated NCT are rejected.
- Unit tests also prove that HTTP does not run migration DDL and that privilege verification fails closed.

The prior [**#42562929833**](https://github.com/pdufa/pdufa-command-center/actions/runs/42562929833) tested native PostgreSQL immutability and separate **synthetic offline key wrapping/recovery**. Neither run tests real production encryption keys or creates an offsite key backup.

## Activation gates remaining

1. **Approval and architecture:** Confirm separate isolated Render and database environments and available storage capacity. Check that the shared `require_storage` health gate and dedicated runtime connection both reference intentionally authorized resources; perform a migration dry-run with an independent review.
2. **Role provisioning:** Create separate migration-owner and exact runtime roles in the approved isolated database; enforce distinct credentials and TLS chain, narrow network access, audit/expiration and rotation. Do not reuse the service's normal database owner connection.
3. **Encryption-key custody:** Provision a unique 256-bit AES key, an independently held recovery wrapping key, real offsite escrow and audited restore; synthetic recovery tests do not meet this requirement.
4. **Document security and privacy:** Authenticate legal source rights, file provenance and trial/version, malware scan, retention/deletion policy and independent encrypted DB backups; no PHI or confidential patient-level sources.
5. **Manual backend deployment:** Only after approved gates, deploy **exact SHA** to the already isolated Render service with auto-deploy OFF and separately test protected routes. No automatic service or database mutation is authorized by this installation.
6. **Scientific independence:** Document storage does not authenticate original trial statistics or substitute for qualified clinician/method reviewer signoff. The pilot remains 18 research-mapped positions, **0/800 authorized clinical grades**, FDA prediction **ABSTAIN**, accuracy **NOT CALIBRATED**.

**Security limitation:** A database administrator or owner can still alter permissions/triggers and rewrite receipts; immutable SQL triggers and in-database hash chains are **not** tamper-proof against privileged operators. External receipt checkpointing and separately owned encrypted backups are required before active production usage.
