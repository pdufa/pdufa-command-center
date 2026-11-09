# MAIN Revision 30 — encrypted original-document evidence vault staged, disabled

**Exact trial:** ACACIA-HCM / NCT06081894 / CY 6033.  
**Deployment boundary:** Draft PR #965; isolated Render medical service stays unchanged with autodeploy OFF. **No secret was created or uploaded and no original source document has been deposited.**

## Infrastructure finding

The connected current Neon project `pdufa-new-persistent-db` is in **AWS us-west-2**, where Neon branchable object storage currently reports **region unavailable**. We did **not** create a new billable project, change production topology, create a public bucket, alter the existing Neon database, or claim object storage was activated.

The staged alternative for low-volume, **public legally authorized** original documents is **application-level AES-256-GCM encryption** of small source bytes stored in an isolated PostgreSQL `BYTEA` table. Source material **must not** contain patient-level records, protected health information or confidential restricted data. The current project is not HIPAA-enabled.

## New backend components

- `new-platform/backend/app/medical_original_evidence_vault.py`: additive PostgreSQL-only evidence tables (SQLite permitted only with explicit unit-test flag), 2 MiB per-source cap, exact trial/request/document type, original PDF/UTF-8 validation, strict HTTPS original-source allowlist, original-byte SHA-256 comparison, cryptographically fresh AES-GCM nonce and associated-data binding to trial, document hash, versioned metadata and receipt identity. Writes only ciphertext, nonce and source/rights metadata. Append-only PostgreSQL/SQLite mutation rejection triggers, unique source digest and **declared document-version uniqueness**, receipt-version hash chaining, metadata-only list, internal audit of ciphertext/tag and source hash **without returning plaintext**.
- `new-platform/backend/app/medical_original_evidence_vault_http.py`: backend-only, role-separated, opt-in original upload + metadata-only read. Uses a distinct 32+ character write secret and different read secret. Requires the isolated Render service ID, explicit vault/medical feature flags, durable PostgreSQL, actual byte matching and affirmative **document storage-rights attestation**; anonymous browser and browser-origin source upload are explicitly refused. JSON upload capped at 2.85MB, original bytes capped at 2 MiB. No general-public upload/download route, no clinical review event and no automatic medical scoring.
- `new-platform/backend/app/main.py`: mounts these routes **only** when `PDUFA_ORIGINAL_EVIDENCE_VAULT_ENABLED`, `PDUFA_MEDICAL_PREVIEW_ENABLED`, `PDUFA_REQUIRE_POSTGRES` and exact `RENDER_SERVICE_ID=srv-dbntrkpsrm7s73aec3lg` all match. Default settings never create vault tables or expose endpoints.
- `new-platform/backend/requirements.txt`: adds supported Python `cryptography` AES-GCM implementation.
- `new-platform/backend/tests/test_medical_original_evidence_vault.py`: bytes-to-ciphertext verification, correct/incorrect keys, exact NCT and source controls, duplicate version/digest rejection, verified append-only multi-version receipt chain, mutation trigger, metadata-only list, no grade/FDA effect.
- `new-platform/backend/tests/test_medical_original_evidence_vault_http.py`: isolated FastAPI test, distinct read/write role credentials, opt-in route absence, browser Origin rejection, storage-rights attestation, invalid source/receipt/base64/size rejection, encrypted upload with metadata readback, no plaintext or grades.
- `new-platform/frontend/app/predictions/assessment/PilotEncryptedEvidenceVaultStatus.tsx`: intentionally displays **STAGED, NOT ACTIVE** below the browser-local SHA-256 intake precheck, not a false green "uploaded" result; describes the five remaining activation/security gates.
- `new-platform/frontend/tests/acacia-evidence-intake-precheck.test.cjs` and `new-platform/backend/scripts/verify_medical_preview.py`: ensure the signed-in PREDICTIONS screen never suggests activated storage or medical grades.

## What must be completed before active storage

1. **Infrastructure and cost gate:** Confirm isolated Render backend uses its own durable PostgreSQL, review storage quota and document rights, and run a PostgreSQL-specific migration test on an *isolated test database* before enabling the new schema.
2. **Key custody and recovery:** Provision a fresh independent AES-256 encryption key in supported service secrets, never in GitHub; implement secure key backup/restore, versioned key rotation and dual-control emergency recovery.
3. **Separate permissions:** Provision two unique read/write secrets on the **isolated** Render service and test credential isolation, network access, quotas and auditability. The dashboard should not contain or proxy private vault upload credentials.
4. **Source policy and malware:** Limit to legally authorized, genuinely public original documents; confirm external access rules, source authenticity, content security scanning, version/date validity, per-document encryption and retention policies before regular ingestion. **No PHI.**
5. **Independent reviewer workflow:** Constrain the source receipt to its mapped methods, verify original statistical/clinical evidence by qualified review, and only then use the separately gated append-only signed clinical review ledger. The vault **does not** assign clinical scores or FDA probabilities.

## Scientific status unchanged

There are 18 source-mapped research method leads and six unsent original evidence acquisition requests. Neither these leads nor a successful hash/encryption unit test establishes clinical source completeness. No actual original document has been deposited, no reviewer signature is recorded, and **0/800** independent clinical grades exist for the pilot. FDA outcome forecast **ABSTAIN**, accuracy **NOT CALIBRATED**.

**Security caveat:** SQL triggers prevent ordinary updates/deletes but do not make a privileged database administrator unable to change table definitions. SHA-linked receipts allow detection against separately preserved checkpoints but are not by themselves externally anchored, tamper-proof records. Before production use, require independent append-only backups/checkpoints, key custody, audited PostgreSQL integration, disaster recovery and legal review.
